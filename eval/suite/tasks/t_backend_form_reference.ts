import { createHmac, randomUUID, timingSafeEqual } from "node:crypto";

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

export function buildSecurityHeaders(options?: {
  readonly scriptHash?: string;
  readonly styleHash?: string;
}): Record<string, string> {
  const scriptToken = options?.scriptHash ?? "sha256-__CSP_SCRIPT__";
  const styleToken = options?.styleHash ?? "sha256-__CSP_STYLE__";
  return {
    "content-security-policy": `default-src 'none'; script-src 'self' '${scriptToken}'; style-src 'self' '${styleToken}'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'; require-trusted-types-for 'script'`,
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

export function generateCsrfToken(
  sessionId: string,
  timestampMs: number,
  secret: string
): string {
  const mac = createHmac("sha256", secret)
    .update(`${sessionId}:${timestampMs}`)
    .digest("hex");
  return `${timestampMs}.${mac}`;
}

export function verifyCsrfToken(
  token: string,
  sessionId: string,
  secret: string,
  nowMs: number,
  maxAgeMs = 900_000
): boolean {
  if (typeof token !== "string" || !sessionId || !secret) {
    return false;
  }
  const dotIdx = token.indexOf(".");
  if (dotIdx <= 0 || dotIdx === token.length - 1) {
    return false;
  }
  const tsStr = token.slice(0, dotIdx);
  const sigHex = token.slice(dotIdx + 1);
  if (!/^\d+$/.test(tsStr) || !/^[0-9a-f]{64}$/i.test(sigHex)) {
    return false;
  }
  const ts = Number(tsStr);
  if (!Number.isSafeInteger(ts)) {
    return false;
  }
  if (ts > nowMs + 5000 || nowMs - ts > maxAgeMs) {
    return false;
  }
  const expectedHex = createHmac("sha256", secret)
    .update(`${sessionId}:${ts}`)
    .digest("hex");
  const a = Buffer.from(sigHex.toLowerCase(), "utf-8");
  const b = Buffer.from(expectedHex.toLowerCase(), "utf-8");
  if (a.length !== b.length) {
    return false;
  }
  return timingSafeEqual(a, b);
}

export function sanitizeHtmlText(input: string): string {
  const withoutCtrl = input.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, "");
  const normalized = withoutCtrl.replace(/\s+/g, " ").trim();
  return normalized
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

const NAME_RE = /^[\p{L}\s.\-]+$/u;
const EMAIL_RE = /^[^\s<>@]+@[^\s<>@]+\.[^\s<>@.]{2,}$/;
const VALID_TIERS = new Set<ProjectTier>(["prototype", "production", "enterprise"]);

export class FormApiHandler {
  private readonly csrfSecret: string;
  private readonly rateLimitMaxRequests: number;
  private readonly rateLimitWindowMs: number;
  private readonly csrfMaxAgeMs: number;
  private readonly nowFn: () => number;
  private readonly ipHits: Map<string, number[]> = new Map();

  constructor(config: HandlerConfig) {
    if (!config || typeof config.csrfSecret !== "string" || config.csrfSecret.trim().length < 16) {
      throw new Error("csrfSecret must be at least 16 characters");
    }
    if (!Number.isInteger(config.rateLimitMaxRequests) || config.rateLimitMaxRequests <= 0) {
      throw new Error("rateLimitMaxRequests must be a positive integer");
    }
    if (!Number.isInteger(config.rateLimitWindowMs) || config.rateLimitWindowMs <= 0) {
      throw new Error("rateLimitWindowMs must be a positive integer");
    }
    this.csrfSecret = config.csrfSecret;
    this.rateLimitMaxRequests = config.rateLimitMaxRequests;
    this.rateLimitWindowMs = config.rateLimitWindowMs;
    this.csrfMaxAgeMs = config.csrfMaxAgeMs ?? 900_000;
    this.nowFn = config.nowFn ?? (() => Date.now());
  }

  handleRequest(req: {
    readonly method: string;
    readonly clientIp: string;
    readonly sessionId: string;
    readonly contentType?: string;
    readonly body: unknown;
  }): ApiResponse<ValidatedSubmission> {
    const baseHeaders = buildSecurityHeaders();

    if (!req || req.method.toUpperCase() !== "POST") {
      return {
        status: 405,
        headers: { ...baseHeaders, allow: "POST" },
        body: { ok: false, errorCode: "METHOD_NOT_ALLOWED" },
      };
    }

    if (!req.contentType || !req.contentType.toLowerCase().startsWith("application/json")) {
      return {
        status: 415,
        headers: baseHeaders,
        body: { ok: false, errorCode: "UNSUPPORTED_MEDIA_TYPE" },
      };
    }

    const now = this.nowFn();
    const ip = req.clientIp || "0.0.0.0";
    const cutoff = now - this.rateLimitWindowMs;
    const prevHits = (this.ipHits.get(ip) ?? []).filter((t) => t > cutoff);

    if (prevHits.length >= this.rateLimitMaxRequests) {
      const oldestInWindow = prevHits[0] ?? now;
      const retryAfterSec = Math.max(
        1,
        Math.ceil((oldestInWindow + this.rateLimitWindowMs - now) / 1000)
      );
      this.ipHits.set(ip, prevHits);
      return {
        status: 429,
        headers: { ...baseHeaders, "retry-after": String(retryAfterSec) },
        body: { ok: false, errorCode: "RATE_LIMITED" },
      };
    }

    prevHits.push(now);
    this.ipHits.set(ip, prevHits);

    if (typeof req.body !== "object" || req.body === null || Array.isArray(req.body)) {
      return {
        status: 400,
        headers: baseHeaders,
        body: { ok: false, errorCode: "VALIDATION_FAILED", errors: [{ field: "body", code: "INVALID_OBJECT", message: "Body must be a JSON object" }] },
      };
    }

    const payload = req.body as Record<string, unknown>;

    if (typeof payload.honeypot === "string" && payload.honeypot.trim().length > 0) {
      return {
        status: 400,
        headers: baseHeaders,
        body: { ok: false, errorCode: "BOT_DETECTED" },
      };
    }

    const csrfToken = typeof payload.csrfToken === "string" ? payload.csrfToken : "";
    if (!verifyCsrfToken(csrfToken, req.sessionId, this.csrfSecret, now, this.csrfMaxAgeMs)) {
      return {
        status: 403,
        headers: baseHeaders,
        body: { ok: false, errorCode: "CSRF_INVALID" },
      };
    }

    const errors: ValidationIssue[] = [];
    const rawName = typeof payload.fullName === "string" ? payload.fullName.trim() : "";
    if (rawName.length < 2 || rawName.length > 120 || !NAME_RE.test(rawName)) {
      errors.push({ field: "fullName", code: "INVALID_NAME", message: "Full name must be 2..120 letters" });
    }

    const rawEmail = typeof payload.workEmail === "string" ? payload.workEmail.trim() : "";
    if (rawEmail.length < 5 || rawEmail.length > 254 || !EMAIL_RE.test(rawEmail)) {
      errors.push({ field: "workEmail", code: "INVALID_EMAIL", message: "Valid work email required" });
    }

    const rawCompany = typeof payload.company === "string" ? payload.company.trim() : "";
    if (rawCompany.length < 2 || rawCompany.length > 120) {
      errors.push({ field: "company", code: "INVALID_COMPANY", message: "Company must be 2..120 chars" });
    }

    const rawTier = payload.projectTier;
    if (typeof rawTier !== "string" || !VALID_TIERS.has(rawTier as ProjectTier)) {
      errors.push({ field: "projectTier", code: "INVALID_TIER", message: "Invalid project tier" });
    }

    const rawBudget = payload.budgetUsd;
    if (typeof rawBudget !== "number" || !Number.isFinite(rawBudget) || rawBudget < 1000 || rawBudget > 10_000_000) {
      errors.push({ field: "budgetUsd", code: "INVALID_BUDGET", message: "Budget must be 1000..10000000" });
    }

    const rawMessage = typeof payload.message === "string" ? payload.message.trim() : "";
    if (rawMessage.length < 10 || rawMessage.length > 4000) {
      errors.push({ field: "message", code: "INVALID_MESSAGE", message: "Message must be 10..4000 chars" });
    }

    if (errors.length > 0) {
      return {
        status: 400,
        headers: baseHeaders,
        body: {
          ok: false,
          errorCode: "VALIDATION_FAILED",
          errors,
        },
      };
    }

    const data: ValidatedSubmission = {
      submissionId: randomUUID(),
      fullName: rawName,
      workEmail: rawEmail.toLowerCase(),
      company: rawCompany,
      projectTier: rawTier as ProjectTier,
      budgetUsd: rawBudget as number,
      sanitizedMessage: sanitizeHtmlText(rawMessage),
      receivedAtIso: new Date(now).toISOString(),
    };

    return {
      status: 200,
      headers: baseHeaders,
      body: {
        ok: true,
        data,
      },
    };
  }
}
