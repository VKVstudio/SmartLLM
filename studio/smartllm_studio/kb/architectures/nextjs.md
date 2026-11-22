# Stack 4: `nextjs` — Next.js 16.4.x Active LTS App Router + React 19.3.x

## 1. Verified Late-2026 Versions & Primitives
- **Versions (Nov 2026):** **Next.js `16.4.6` Active LTS** (Nov 9, 2026; `16.4.0` Oct 6, 2026; **`16.4.5` Nov 3, 2026 mandatory security floor**; Maintenance LTS is `15.5.29`; Next.js 17 not yet released) + **React `19.3.1`** (Oct 14, 2026; `19.3.0` stabilized `<ViewTransition>`, Fragment Refs, Trusted Types in React DOM, and `<Context>` in RSC).
- **RSC vs Leaf `'use client'`:** Server Components are default (`0 KB` client JS for server tree). Push `'use client'` strictly to smallest interactive leaf widgets; pass serializable DTOs only.
- **Cache Components & PPR (`'use cache'`):** `cacheComponents: true` (default in new 16.4 apps; replaces legacy `export const dynamic`/`revalidate`). Annotate cacheable async functions/components with `'use cache'`, set TTL via `cacheLife()`, tag via `cacheTag()`, invalidate synchronously after mutations via `updateTag()` or background `revalidateTag()`. Pair cached shells with `<Suspense>` streaming.
- **`proxy.ts` (Replaces Deprecated `middleware.ts`):**
  - `middleware.ts` is deprecated in Next.js 16 in favor of `proxy.ts`.
  - **Hard Constraints:** `proxy.ts` runs on the **Node.js runtime ONLY** (`runtime = 'edge'` is unsupported); `'use cache'`, `'use server'`, and `fetch` cache options do NOT work inside `proxy.ts`; NEVER treat `proxy.ts` as the sole auth/authz boundary.
- **Server Actions (`'use server'`):** Compile to public HTTP `POST` endpoints with non-deterministic action IDs + automatic `Origin` vs `Host`/`X-Forwarded-Host` CSRF checks (`experimental.serverActions.allowedOrigins` behind multi-hop proxies).
- **Data Access Layer (DAL):** Centralized server modules with `import 'server-only'`, mandatory authz check per function, Zod v4 validation, explicit DTO projection, and optional React 19 `experimental_taintObjectReference` / `experimental_taintUniqueValue`.
- **Primary Docs:** `https://nextjs.org/blog`, `https://nextjs.org/docs/app/api-reference/file-conventions/proxy`, `https://nextjs.org/docs/app/api-reference/directives/use-cache`, `https://nextjs.org/docs/app/guides/data-security`, `https://endoflife.date/nextjs`.

## 2. Mandatory Cache & Action Security Rules (Nov 2026 CVEs)
1. **Pin `next >= 16.4.5` (prefer `16.4.6+`) & Purge Legacy Caches:**
   - `16.4.5` patched 3 cache-isolation CVEs: `CVE-2026-119790` (High: `unstable_cache`/`use cache` cross-tenant leak), `CVE-2026-119351` (nested `use cache` root-params race), `CVE-2026-119349` (binary args collision). Any deployment upgraded from `<=16.4.4` must purge persisted caches.
2. **Tenant Isolation in `'use cache'`:**
   - NEVER call `cookies()` or `headers()` inside a `'use cache'` scope. Read session/tenant outside the cache boundary and pass `tenantId` / `userId` explicitly as cache function arguments so cache keys segregate tenants cleanly.
3. **Server Actions Are Public POST Endpoints:**
   - Every `'use server'` action MUST independently verify session + ownership via DAL, parse inputs with Zod v4 (`safeParse`), execute atomic writes, and call `updateTag(...)`. Never trust hidden fields, client prices, or closure-bound roles.
4. **CSP & Inline Styles Warning:** Avoid React `style={{...}}` on SSR markup if deploying strict `style-src-attr 'none'`; use CSS classes/modules and nonce-based CSP for Next.js SSR.

## 3. Build, Deployment & Offline Preview
- **Build:** Requires Node (`next build`).
- **Runtime vs Static Export (`output: 'export'`):** Full App Router requires Node runtime (`next start`, Docker standalone, OpenNext, Vercel). `output: 'export'` produces static files for offline preview, BUT **Server Actions fail the build** and **`proxy.ts` does NOT run** — if you only need static output, choose `astro` or `html5_esm`.
