# Frontend <-> Backend Trust Boundary Matrix (Late 2026)

Baseline: **OWASP ASVS 5.0** + **OWASP Top 10:2025** (`owasp.org/Top10/2025/`) + OWASP CSRF/SSRF/CSP/Session Cheat Sheets.

## 1. Architecture Comparison Matrix
| Stack | Primary Channel | Authoritative Boundary | Built-in CSRF Guard | Secret Isolation | Offline Preview |
|---|---|---|---|---|---|
| `html5_esm` | `<form POST>` / `fetch` -> Edge webhook | Serverless/Edge handler | Manual (`Sec-Fetch-Site` + `Origin` in webhook) | Edge env only (never in HTML/ESM) | **YES** (static HTTP; webhook external) |
| `astro` (`7.4.13`) | Actions (`/_actions/*`), Server Islands, API routes | `src/actions/`, `prerender=false` endpoints | `security.checkOrigin: true` (SSR only) | `astro:env` (`server/secret`) | Static `dist/` YES; Actions/SSR NO |
| `sveltekit` (`3.4.0`) | `+page.server.ts` load/actions (`use:enhance`), `+server.ts` | `hooks.server.ts` + `*.server.ts` | `csrf.trustedOrigins` (`Sec-Fetch-Site` + `Origin`) | `$env/{static,dynamic}/private` | `adapter-static` YES (no actions); SSR NO |
| `nextjs` (`16.4.6`) | RSC Flight, Server Actions (`POST`), Route Handlers | DAL (`server-only`) + Actions/Routes (NOT `proxy.ts` alone) | `Origin` vs `Host`/`X-Forwarded-Host` + `allowedOrigins` | `server-only`, non-`NEXT_PUBLIC_*`, taint API | `output:'export'` YES (no Actions/`proxy.ts`); Full NO |
| `vite_ts` (`8.3.8`) | `fetch` REST/JSON -> same-origin BFF (`/api/*`) | Dedicated BFF server | Manual in BFF (`Sec-Fetch-Site` + `Origin`) | BFF env only (all `VITE_*` are PUBLIC!) | Static UI YES; BFF auth/data NO |

## 2. Non-Negotiable Zero-Trust Invariants (Apply to ALL 5 Stacks)
1. **Frontend Is NEVER Trusted With:**
   - Prices, totals, discounts, currency, quota, or subscription tier (compute server-side from catalog IDs).
   - AuthN/AuthZ claims, `userId`, `tenantId`, `role`, or ownership (derive from verified server session).
   - Rate limits, Turnstile/CAPTCHA verification, or honeypot outcomes (enforce server/edge-side).
   - Hidden `<input type="hidden">`, disabled controls, URL query params, client clocks, or optimistic UI state.
   - HTML/SVG sanitization or API bearer tokens.
2. **Validation Split & DTO Allowlisting:**
   - **Client:** UX hints only (HTML5 constraints or `zod/mini`).
   - **Server (Authoritative):** Parse every request with **Zod v4** strict schemas (strip unknown keys -> blocks mass assignment). Project DB rows into explicit public DTOs on output (blocks PII/secret leakage into SSR HTML / RSC Flight).
3. **Cookies & Sessions (ASVS 5.0 / RFC 6265bis):**
   - Prefix sensitive cookies with **`__Host-`** (enforces `Secure`, `Path=/`, NO `Domain` -> prevents subdomain cookie fixation/injection).
   - Flags: `HttpOnly; Secure; SameSite=Lax; Path=/` (`SameSite=Strict` for admin/payment sessions).
   - NEVER store session/refresh tokens in `localStorage` or `sessionStorage`.
4. **CSRF & CORS Defense:**
   - Verify Fetch Metadata **`Sec-Fetch-Site`** (`same-origin` or `none`; reject `cross-site` on `POST/PUT/PATCH/DELETE` with `403`) + fallback **`Origin`** exact allowlist + `SameSite` cookies. Keep framework CSRF guards ON; never configure `['*']`.
   - Prefer same-origin BFF/routes to eliminate CORS. Where CORS is mandatory, allowlist exact origins; NEVER pair `Access-Control-Allow-Origin: *` with `Access-Control-Allow-Credentials: true`.
5. **SSRF & Host-Header Hardening (A01:2025 Broken Access Control):**
   - Never pass user-supplied URLs straight to server `fetch()`. If outbound fetch is required: allowlist `https:` + hostnames, resolve DNS first and block loopback (`127.0.0.0/8`, `::1`), RFC1918 (`10/8`, `172.16/12`, `192.168/16`), cloud metadata/link-local (`169.254.169.254`, `fe80::/10`), and ULA (`fc00::/7`); disable auto-redirects or re-validate each hop.
   - Guard `X-Forwarded-Host` with explicit allowlists (`allowedDomains` / trusted proxy settings).
6. **XSS, Sanitization & CSP Level 3:**
   - Default to text-only rendering (`.textContent`). If rich HTML is required, sanitize **server-side** AND with **DOMPurify** on client (`Element.setHTML()` lacks Safari support in Nov 2026).
   - Ship strict CSP3 (`sha256` hashes for static or nonces for SSR, `object-src 'none'`, `base-uri 'none'`, `frame-ancestors 'none'` via HTTP headers). Never put HTML `style="..."` attrs in SSR/static markup under `style-src-attr 'none'`.
