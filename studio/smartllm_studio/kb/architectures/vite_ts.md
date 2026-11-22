# Stack 5: `vite_ts` — Vite 8.3.x (Rolldown) + TypeScript 7.x + Same-Origin BFF

## 1. Verified Late-2026 Versions & Tooling Caveats
- **Vite `8.3.8` (Nov 11, 2026):** `8.0.0` (March 12, 2026) replaced `esbuild` + `Rollup` with unified **Rolldown + Oxc** Rust toolchain. Config migrations: `build.rollupOptions` -> `build.rolldownOptions`, `worker.rollupOptions` -> `worker.rolldownOptions`, `optimizeDeps.esbuildOptions` -> `optimizeDeps.rolldownOptions`, `esbuild` -> `oxc`.
- **TypeScript `7.0` GA (July 8, 2026, Project Corsa `tsgo` Go Compiler) / `7.1 Beta` (Oct 20, 2026):**
  - 8–12x faster CLI builds & type-checking; drops `target: es5`, `baseUrl`, `node10` resolution (TS 6.0 was the final JS bridge).
  - **CRITICAL TOOLING CAVEAT:** `typescript@7.0` shipped with **NO programmatic JS API** (`ts.createProgram`), breaking ESLint (`typescript-eslint`), Volar, and custom AST plugins unless paired with `@typescript/typescript6` compatibility shim or **TypeScript `7.1+`** (`typescript/sync` & `typescript/async` API groundwork).
- **Validation:** **Zod `4.6.7`** (Oct 2026; fast `.validate()`, subpath `zod/mini` or `@zod/mini` for tiny client bundles + full `zod` on BFF).
- **Primary Docs:** `https://vite.dev/blog/`, `https://devblogs.microsoft.com/typescript/`, `https://zod.dev`.

## 2. When SPA Is Justified vs Hard Anti-Pattern
### Justified Use Cases
- Auth-gated SaaS workspaces & admin panels (`X-Robots-Tag: noindex`).
- Interactive local-first apps, WebGPU/Canvas/CAD/media editors, local tool HUDs (like SmartLLM Studio UI).
- Authenticated offline-first PWAs where SEO crawlability is irrelevant.

### Hard Anti-Pattern for SEO / Marketing / Corporate Landings
1. **AI/LLM & Social Crawler Blindness:** `GPTBot`, `OAI-SearchBot`, `ClaudeBot`, `Claude-SearchBot`, `PerplexityBot`, and OpenGraph scrapers fetch raw initial HTTP HTML and **do NOT execute client JS**. A CSR `<div id="root"></div>` shell yields zero GEO citations and broken previews.
2. **Two-Wave Indexing Delay:** Googlebot defers CSR rendering to a secondary headless Chromium queue with render-budget limits.
3. **CWV Penalty:** Client bundle + API waterfall degrades **LCP** (`<= 2.5s`) and hydration hurts **INP** (`<= 200ms`).

## 3. Frontend <-> Backend (Same-Origin BFF) & Trust Boundary
- **Channel:** Browser SPA -> same-origin Reverse Proxy -> **BFF** (`/api/*`, `server.proxy` in dev) -> downstream DB/services.
- **Why Same-Origin BFF Is Mandatory:** Terminates OAuth/OIDC server-side and issues `__Host-sid` (`HttpOnly; Secure; SameSite=Lax; Path=/`), eliminating `localStorage`/`sessionStorage` token theft via XSS and eliminating CORS preflight sprawl.
- **Trust Rules:** Treat every `/api/*` call as untrusted; enforce `Sec-Fetch-Site` + `Origin` CSRF checks on mutations, Zod v4 allowlist schemas, server-side RBAC/tenant isolation, rate limiting, and explicit DTOs. All `VITE_*` env vars compile into public client JS — NEVER place secrets in `VITE_*`.

## 4. Build, Deployment & Offline Preview
- **Build:** Requires Node + Vite 8 (`vite build` via Rolldown).
- **Offline Preview:** Static `dist/` runs offline over local HTTP ONLY for purely client-local/mocked state; any auth or live data requires running the BFF alongside it.
