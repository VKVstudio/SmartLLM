# Web Security Hardening & Vulnerability Audit (Late 2026)

## 1. OWASP Top 10:2025 (`owasp.org/Top10/2025/`)
1. **A01:2025 – Broken Access Control** *(now absorbs SSRF + path traversal)*
2. **A02:2025 – Security Misconfiguration** *(CSP, HTTP headers, CORS, verbose errors)*
3. **A03:2025 – Software Supply Chain Failures** *(expanded from 2021 Vulnerable Components)*
4. **A04:2025 – Cryptographic Failures**
5. **A05:2025 – Injection** *(XSS, DOM-XSS, SQLi, SSTI, header injection)*
6. **A06:2025 – Insecure Design**
7. **A07:2025 – Authentication Failures**
8. **A08:2025 – Software or Data Integrity Failures** *(missing SRI, unsigned artifacts)*
9. **A09:2025 – Security Logging & Alerting Failures**
10. **A10:2025 – Mishandling of Exceptional Conditions** *(NEW in 2025 — fail-open errors, leaked stack traces)*

## 2. CRITICAL: W3C CSP Level 3 vs CSSOM (`style-src-attr 'none'`)
Verified across Chromium, Firefox, and WebKit under strict `style-src 'self' 'sha256-...'` + `style-src-attr 'none'` (ZERO `'unsafe-inline'`):
| Operation | Blocked? | Spec / Directive | SmartLLM Canon |
|---|---|---|---|
| `<style>...</style>` | **YES** unless `'sha256-...'`/nonce matches | `style-src-elem` | **ALLOWED** only with build-time SHA-256 hash |
| `<div style="...">` / React `style={{...}}` SSR | **YES (BLOCKED)** | `style-src-attr` | **FORBIDDEN** in HTML/SSR output |
| `el.setAttribute('style', '...')` | **YES (BLOCKED)** | `style-src-attr` | **FORBIDDEN** in JS |
| `el.style.transform = ...` / `.setProperty('--k', v)` | **NO (ALLOWED)** | CSSOM property setter | **APPROVED** (safe for motion/scroll!) |
| `el.animate([...], {...})` (WAAPI) | **NO (ALLOWED)** | Web Animations API | **APPROVED** |
| `el.style.cssText = '...'` | **BLOCKED/INCONSISTENT** (Firefox blocks!) | CSSOM string sink | **BANNED** |

## 3. Trusted Types (`require-trusted-types-for 'script'`)
- **Baseline Newly Available (Feb 2026):** Chrome 83+, Safari 26 (Sep 2025), **Firefox 148** (Feb 2026).
- Blocks raw string sinks (`innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `eval`, `new Function`, `setTimeout(str)`).
- Static/vanilla islands use `.textContent` + `createElement` + safe `setAttribute` (requires zero policy). React 19.3 / DOMPurify SSR apps define `trusted-types default dompurify;`.

## 4. Security Headers & Edge Platform Pitfalls
- **`<meta>` CSP Limitation:** Browsers silently ignore `frame-ancestors`, `sandbox`, `report-uri`, and `report-to` inside `<meta http-equiv="Content-Security-Policy">`. Clickjacking (`frame-ancestors 'none'`) **MUST** ship in HTTP headers:
  ```http
  Content-Security-Policy: default-src 'none'; script-src 'self' 'sha256-<HASH>'; style-src 'self' 'sha256-<HASH>'; style-src-attr 'none'; img-src 'self' data:; font-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'; object-src 'none'; require-trusted-types-for 'script'
  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()
  Cross-Origin-Opener-Policy: same-origin
  Cross-Origin-Embedder-Policy: credentialless
  Cross-Origin-Resource-Policy: same-origin
  ```
  *(Use `credentialless` for offline/marketing sites; upgrade to `require-corp` only when zero third-party embeds exist and cross-origin `SharedArrayBuffer` isolation is required.)*
- **Cloudflare Pages (`_headers`):** Max **100** URL rules; max **2,000 chars per header line** (huge hash lists silently fail — keep inline code externalized `'self'`); comments MUST start with `#` at col 0 (never `/*`); **does NOT apply to Pages Functions** (emit headers in `functions/_middleware.ts`).
- **Nginx:** Child `location` `add_header` wipes ALL parent `server` headers! Use shared `include` or **Nginx `1.29.3+` `add_header_inherit merge;`** + **`always`** on every directive.
- **Vercel / Netlify:** Netlify `_headers` skips Edge/Serverless Functions (set programmatically). Vercel `vercel.json` separates `/(.*)` security headers from `/assets/(.*)` cache headers.

## 5. CSRF, Forms, SVG XSS & Links
- **CSRF (`Sec-Fetch-Site` + `Origin`):** Server endpoints reject `Sec-Fetch-Site: cross-site` (`403`) + check `Origin` + `SameSite=Lax|Strict` `__Host-` cookies. Forms include server Zod v4 validation + `.hp-trap` honeypot.
- **OWASP SVG XSS Defense:** Enforce strict geometry allowlist (or DOMPurify) AND strip `<script>`, `<foreignObject>`, SMIL (`<animate>`, `<set>`, `<animatetransform>`, `<animatemotion>`), `<style>`, `<use>`, `<iframe>`, `on*` attrs, XML `<!DOCTYPE`/`<!ENTITY` (XXE/Billion Laughs), and `javascript:`/`vbscript:`/`data:text/html`/`data:image/svg+xml`/`data:application/xhtml+xml` URIs.
- **External Links & SRI:** All `target="_blank"` carry `rel="noopener noreferrer"`; zero external CDN assets in offline default (SRI mandatory if online).
