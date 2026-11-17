FILE: form_handler.ts
```typescript
import { createHmac, timingSafeEqual } from "node:crypto";

// ─── Types & Interfaces ──────────────────────────────────────────────────────────

export type ProjectTier = "prototype" | "production" | "enterprise";

export interface FormSubmissionInput {
  fullName: string;
  workEmail: string;
  company: string;
  projectTier: ProjectTier;
  budgetUsd: number;
  message: string;
  csrfToken: string;
  honeypot?: string;
  timestampMs: number;
}

export interface ValidationIssue {
  field: string;
  code: string;
  message: string;
}

export interface ValidatedSubmission {
  submissionId: string;
  fullName: string;
  workEmail: string;
  company: string;
  projectTier: ProjectTier;
  budgetUsd: number;
  sanitizedMessage: string;
  receivedAtIso: string;
}

export interface ApiResponse<T = unknown> {
  status: number;
  headers: Readonly<Record<string, string>>;
  body: {
    readonly ok: boolean;
    readonly data?: T;
    readonly errors?: readonly ValidationIssue[];
    readonly errorCode?: string;
  };
}

export interface HandlerConfig {
  csrfSecret: string;
  rateLimitMaxRequests: number;
  rateLimitWindowMs: number;
  csrfMaxAgeMs?: number;
  nowFn?: () => number;
}

// ─── Security Headers ──────────────────────────────────────────────────────────

export function buildSecurityHeaders(
  options?: { readonly scriptHash?: string; readonly styleHash?: string }
): Record<string, string> {
  const scriptSrc = options?.scriptHash
    ? `'self' '${options.scriptHash}'`
    : "'self' 'sha256-__CSP_SCRIPT__'";
  const styleSrc = options?.styleHash
    ? `'self' '${options.styleHash}'`
    : "'self' 'sha256-__CSP_STYLE__'";

  return {
    "content-security-policy":
      `default-src 'none'; script-src ${scriptSrc}; style-src ${styleSrc}; ` +
      `img-src 'self' data:; connect-src 'self'; object-src 'none'; ` +
      `base-uri 'none'; frame-ancestors 'none'; form-action 'self'; ` +
      `require-trusted-types-for 'script'`,
    "cross-origin-opener-policy": "same-origin",
    "cross-origin-embedder-policy": "require-corp",
    "cross-origin-resource-policy": "same-origin",
    "strict-transport-security": "max-age=63072000; includeSubDomains; preload",
    "x-content-type-options": "nosniff",
    "referrer-policy": "strict-origin-when-cross-origin",
    "permissions-policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "cache-control": "no-store, max-age=0",
    "content-type": "application/json; charset=utf-8",
  };
}

// ─── CSRF Token Generation & Verification ───────────────────────────────────────

export function generateCsrfToken(
  sessionId: string,
  timestampMs: number,
  secret: string
): string {
  const payload = `${sessionId}:${timestampMs}`;
  const hmacHex = createHmac("sha256", secret).update(payload).digest("hex");
  return `${timestampMs}.${hmacHex}`;
}

export function verifyCsrfToken(
  token: string,
  sessionId: string,
  secret: string,
  nowMs: number,
  maxAgeMs?: number
): boolean {
  const maxAge = maxAgeMs ?? 900_000;
  const separatorIndex = token.indexOf(".");
  if (separatorIndex === -1) return false;

  const timestampStr = token.slice(0, separatorIndex);
  const hmacHex = token.slice(separatorIndex + 1);

  const timestampMs = Number(timestampStr);
  if (!Number.isFinite(timestampMs) || timestampMs <= 0) return false;

  // Timestamp must not be in the future (allow 5s clock skew)
  if (timestampMs > nowMs + 5000) return false;
  // Token must not be too old
  if (nowMs - timestampMs > maxAge) return false;

  const payload = `${sessionId}:${timestampMs}`;
  const expectedHex = createHmac("sha256", secret).update(payload).digest("hex");

  if (hmacHex.length !== expectedHex.length) return false;

  const expectedBuf = Buffer.from(expectedHex, "utf8");
  const actualBuf = Buffer.from(hmacHex, "utf8");

  return timingSafeEqual(expectedBuf, actualBuf);
}

// ─── HTML / XSS Sanitization ────────────────────────────────────────────────────

const CONTROL_CHARS_RE = /[\x00-\x08\x0B\x0C\x0E\x0F\x7F]/g;
const MULTIPLE_WS_RE = /[ \t]{2,}/g;

export function sanitizeHtmlText(input: string): string {
  let result = input.replace(CONTROL_CHARS_RE, "");
  result = result.replace(MULTIPLE_WS_RE, " ");
  result = result.replace(/&/g, "&amp;");
  result = result.replace(/</g, "&lt;");
  result = result.replace(/>/g, "&gt;");
  result = result.replace(/"/g, "&quot;");
  result = result.replace(/'/g, "&#39;");
  return result.trim();
}

// ─── Rate Limiter (Sliding Window) ──────────────────────────────────────────────

interface RateLimitEntry {
  timestamps: number[];
}

function createRateLimiter(
  maxRequests: number,
  windowMs: number,
  nowFn: () => number
): { check: (ip: string) => { allowed: boolean; retryAfterSeconds: number } } {
  const buckets = new Map<string, RateLimitEntry>();

  return {
    check(ip: string): { allowed: boolean; retryAfterSeconds: number } {
      const now = nowFn();
      const entry = buckets.get(ip);

      if (entry === undefined) {
        buckets.set(ip, { timestamps: [now] });
        return { allowed: true, retryAfterSeconds: 0 };
      }

      // Prune timestamps older than the window
      const cutoff = now - windowMs;
      entry.timestamps = entry.timestamps.filter((ts) => ts > cutoff);

      if (entry.timestamps.length >= maxRequests) {
        // Oldest entries are at the boundary of the window; compute retry-after
        const oldest = entry.timestamps[0];
        const remainingMs = oldest + windowMs - now;
        const retryAfterSeconds = Math.max(1, Math.ceil(remainingMs / 1000));
        return { allowed: false, retryAfterSeconds };
      }

      entry.timestamps.push(now);
      return { allowed: true, retryAfterSeconds: 0 };
    },
  };
}

// ─── Validation Helpers ────────────────────────────────────────────────────────

const FULLNAME_RE = /^[A-Za-z\u0400-\u04FF\u0410-\u044F\u0450-\u045F\u0460-\u047F\u0480-\u049F\u04A0-\u04FF\u04A0-\u04FF\s\-\.]+$|^[A-Za-z\u0400-\u04FF\s\-\.]+$/;

function isProjectTier(value: unknown): value is ProjectTier {
  return (
    value === "prototype" ||
    value === "production" ||
    value === "enterprise"
  );
}

function isValidEmail(value: string): boolean {
  const trimmed = value.trim();
  if (trimmed.length < 5 || trimmed.length > 254) return false;
  if (/\s/.test(trimmed)) return false;
  if (/[<>]/.test(trimmed)) return false;
  const parts = trimmed.split("@");
  if (parts.length !== 2) return false;
  const [local, domain] = parts;
  if (local.length === 0 || local.length > 64) return false;
  if (domain.length === 0 || domain.length > 253) return false;
  if (!/^[a-zA-Z0-9._%+\-]+$/u.test(local)) return false;
  if (!/^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(domain)) return false;
  return true;
}

// ─── FormApiHandler ────────────────────────────────────────────────────────────

export class FormApiHandler {
  readonly #config: HandlerConfig;
  readonly #rateLimiter: { check: (ip: string) => { allowed: boolean; retryAfterSeconds: number } };
  readonly #nowFn: () => number;
  readonly #csrfMaxAgeMs: number;
  readonly #csrfSecret: string;
  readonly #rateLimitMaxRequests: number;
  readonly #rateLimitWindowMs: number;

  constructor(config: HandlerConfig) {
    if (!config.csrfSecret || config.csrfSecret.length < 16) {
      throw new Error("csrfSecret must be at least 16 characters");
    }
    if (!Number.isInteger(config.rateLimitMaxRequests) || config.rateLimitMaxRequests <= 0) {
      throw new Error("rateLimitMaxRequests must be a positive integer");
    }
    if (!Number.isInteger(config.rateLimitWindowMs) || config.rateLimitWindowMs <= 0) {
      throw new Error("rateLimitWindowMs must be a positive integer in ms");
    }

    this.#csrfSecret = config.csrfSecret;
    this.#rateLimitMaxRequests = config.rateLimitMaxRequests;
    this.#rateLimitWindowMs = config.rateLimitWindowMs;
    this.#nowFn = config.nowFn ?? (() => Date.now());
    this.#csrfMaxAgeMs = config.csrfMaxAgeMs ?? 900_000;
    this.#rateLimiter = createRateLimiter(
      this.#rateLimitMaxRequests,
      this.#rateLimitWindowMs,
      this.#nowFn
    );
    this.#config = config;
  }

  handleRequest(req: {
    readonly method: string;
    readonly clientIp: string;
    readonly sessionId: string;
    readonly contentType?: string;
    readonly body: unknown;
  }): ApiResponse<ValidatedSubmission> {
    const securityHeaders = buildSecurityHeaders();

    // 1. Method check
    if (req.method.toUpperCase() !== "POST") {
      return {
        status: 405,
        headers: { ...securityHeaders, allow: "POST" },
        body: { ok: false, errorCode: "METHOD_NOT_ALLOWED" },
      };
    }

    // 2. Content-Type check
    if (
      !req.contentType ||
      !req.contentType.toLowerCase().startsWith("application/json")
    ) {
      return {
        status: 415,
        headers: securityHeaders,
        body: { ok: false, errorCode: "UNSUPPORTED_MEDIA_TYPE" },
      };
    }

    // 3. Rate limiting
    const rateResult = this.#rateLimiter.check(req.clientIp);
    if (!rateResult.allowed) {
      return {
        status: 429,
        headers: { ...securityHeaders, "retry-after": String(rateResult.retryAfterSeconds) },
        body: { ok: false, errorCode: "RATE_LIMITED" },
      };
    }

    // 4. Body must be a plain object
    const body: unknown = req.body;
    if (body === null || typeof body !== "object" || Array.isArray(body)) {
      return {
        status: 400,
        headers: securityHeaders,
        body: { ok: false, errorCode: "BOT_DETECTED" },
      };
    }

    const record = body as Record<string, unknown>;

    // 5. Honeypot check
    if (typeof record["honeypot"] === "string" && record["honeypot"].trim().length > 0) {
      return {
        status: 400,
        headers: securityHeaders,
        body: { ok: false, errorCode: "BOT_DETECTED" },
      };
    }

    // 6. CSRF verification
    const csrfToken = record["csrfToken"];
    if (typeof csrfToken !== "string" || csrfToken.length === 0) {
      return {
        status: 403,
        headers: securityHeaders,
        body: { ok: false, errorCode: "CSRF_INVALID" },
      };
    }
    const nowMs = this.#nowFn();
    if (
      !verifyCsrfToken(
        csrfToken,
        req.sessionId,
        this.#csrfSecret,
        nowMs,
        this.#csrfMaxAgeMs
      )
    ) {
      return {
        status: 403,
        headers: securityHeaders,
        body: { ok: false, errorCode: "CSRF_INVALID" },
      };
    }

    // 7. Field validation
    const issues: ValidationIssue[] = [];

    const fullName = record["fullName"];
    if (typeof fullName !== "string" || fullName.trim().length < 2 || fullName.trim().length > 120) {
      issues.push({
        field: "fullName",
        code: "INVALID_LENGTH",
        message: "fullName must be between 2 and 120 characters",
      });
    } else if (!this.#isValidFullName(fullName.trim())) {
      issues.push({
        field: "fullName",
        code: "INVALID_CHARS",
        message: "fullName must contain only letters, spaces, hyphens, or periods",
      });
    }

    const workEmail = record["workEmail"];
    if (typeof workEmail !== "string" || !isValidEmail(workEmail)) {
      issues.push({
        field: "workEmail",
        code: "INVALID_EMAIL",
        message: "workEmail must be a valid email address (5-254 chars)",
      });
    }

    const company = record["company"];
    if (typeof company !== "string" || company.trim().length < 2 || company.trim().length > 120) {
      issues.push({
        field: "company",
        code: "INVALID_LENGTH",
        message: "company must be between 2 and 120 characters",
      });
    }

    const projectTier = record["projectTier"];
    if (!isProjectTier(projectTier)) {
      issues.push({
        field: "projectTier",
        code: "INVALID_TIER",
        message: "projectTier must be prototype, production, or enterprise",
      });
    }

    const budgetUsd = record["budgetUsd"];
    if (
      typeof budgetUsd !== "number" ||
      !Number.isFinite(budgetUsd) ||
      budgetUsd < 1000 ||
      budgetUsd > 10_000_000
    ) {
      issues.push({
        field: "budgetUsd",
        code: "INVALID_BUDGET",
        message: "budgetUsd must be a finite number between 1000 and 10000000",
      });
    }

    const message = record["message"];
    if (typeof message !== "string" || message.trim().length < 10 || message.trim().length > 4000) {
      issues.push({
        field: "message",
        code: "INVALID_LENGTH",
        message: "message must be between 10 and 4000 characters",
      });
    }

    if (issues.length > 0) {
      return {
        status: 400,
        headers: securityHeaders,
        body: { ok: false, errorCode: "VALIDATION_FAILED", errors: issues },
      };
    }

    // 8. Success — return validated submission
    const sanitizedMessage = sanitizeHtmlText(message as string);
    const submissionId = this.#generateSubmissionId(nowMs);

    const data: ValidatedSubmission = {
      submissionId,
      fullName: (fullName as string).trim(),
      workEmail: (workEmail as string).trim().toLowerCase(),
      company: (company as string).trim(),
      projectTier: projectTier as ProjectTier,
      budgetUsd: budgetUsd as number,
      sanitizedMessage,
      receivedAtIso: new Date(this.#nowFn()).toISOString(),
    };

    return {
      status: 200,
      headers: securityHeaders,
      body: { ok: true, data },
    };
  }

  #isValidFullName(value: string): boolean {
    // Allow Latin letters, Cyrillic letters, spaces, hyphens, periods
    return /^[A-Za-z\u0400-\u04FF\s\-\.]+$/u.test(value);
  }

  #generateSubmissionId(nowMs: number): string {
    const hex = createHmac("sha256", this.#csrfSecret)
      .update(`${nowMs}:${Math.random()}`)
      .digest("hex")
      .slice(0, 16);
    return `sub_${hex}`;
  }
}
```