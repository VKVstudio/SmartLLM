# Stack 3: `sveltekit` — SvelteKit 3.4.x + Svelte 5.59.x Runes

## 1. Verified Late-2026 Versions & Breaking Changes
- **Versions (Nov 2026):** **SvelteKit `3.4.0`** (Nov 18–19, 2026; `3.0.0` went stable Oct 1, 2026) + **Svelte `5.59.1`**. Minimum runtime prerequisites: **Node `22.17+`**, **TypeScript `6+`**, **Svelte `5.57.1+`**, **Vite `8.0.12+`**.
- **Svelte 5 Runes:** `$state()`, `$state.raw()` (avoids deep-proxy overhead on large arrays/objects), `$state.snapshot()`, `$derived()`, `$effect()`, `$props()`, `$bindable()` across `.svelte` and `.svelte.ts`.
- **SvelteKit 3 Breaking Changes (CRITICAL FOR CODEGEN):**
  1. **`svelte.config.js` REMOVED:** All Svelte & Kit config (`adapter`, `csrf`, `csp`, `paths`, `compilerOptions`, `preprocess`) now passes directly to `sveltekit({...})` inside `vite.config.ts`.
  2. **`$lib` Alias REMOVED:** Deprecated in late 2.x and **completely removed in SvelteKit 3**. Use Node native `package.json` `"imports": { "#lib/*": "./src/lib/*" }` with **explicit file extensions** (`import { x } from '#lib/utils/format.ts'`; extensionless `#lib/utils/format` or directory imports FAIL).
  3. **`csrf.checkOrigin` REMOVED -> `csrf.trustedOrigins`:** Legacy `csrf.checkOrigin` is gone; configure `csrf: { trustedOrigins: [...] }` (never set `['*']` blindly).
- **Data Loading & Progressive Forms:**
  - `+page.server.ts`: Authoritative server `load` (returns serialized DTOs) and `actions` returning `fail(400, ...)` or `redirect()`.
  - `use:enhance` (`$app/forms`): Progressively enhances `<form method="POST">` while staying 100% functional without JS; cross-page `<form action="/other" use:enhance>` navigates cleanly in SvelteKit 3.
- **Experimental Remote Functions (Opt-In):** Type-safe `query`/`form`/`command` RPC enabled via `compilerOptions: { experimental: { async: true } }` + `experimental: { remoteFunctions: true }`.
- **Secrets Isolation:** `$env/static/private` and `$env/dynamic/private` are build-time blocked from entering client chunks.
- **Primary Docs:** `https://svelte.dev/docs/kit`, `https://svelte.dev/docs/svelte/what-are-runes`, `https://github.com/sveltejs/kit`.

## 2. Frontend <-> Backend Channel & Trust Boundary
- **Channels:** SSR HTML + `+page.server.ts` load serialization, HTML `<form method="POST">` / `use:enhance` Form Actions, `+server.ts` endpoints, optional Remote Functions.
- **Built-in CSRF & Reverse Proxy Rules:**
  - `csrf.trustedOrigins` enforces `Sec-Fetch-Site` + `Origin` checks on unsafe state-changing requests (`403` on cross-origin mismatch).
  - Behind reverse proxies on `@sveltejs/adapter-node`, configure `ORIGIN` env or `protocol_header: 'X-Forwarded-Proto'` + `host_header: 'X-Forwarded-Host'` ONLY when the proxy strips untrusted client headers.
- **Trust Rules:**
  - Authenticate in `hooks.server.ts` (`event.locals.user` from `__Host-` `HttpOnly; Secure; SameSite=Lax` cookie); authorize inside every `+page.server.ts` `load`/`action` and `+server.ts` route.
  - Validate `await request.formData()` / JSON with Zod v4; project explicit DTOs from `load` because SvelteKit embeds returned `load` data into SSR HTML.
  - Enable `csp: { mode: 'auto' | 'nonce' }` in `sveltekit({...})`.

## 3. Build, Deployment & Offline Preview
- **Build:** Requires Node 22.17+ and Vite 8 (`vite build`).
- **Adapters:**
  - `@sveltejs/adapter-static` + `export const prerender = true`: builds static offline-previewable files, but disables runtime `actions`, `+server.ts` mutations, and `$env/dynamic/private`.
  - `@sveltejs/adapter-node` / `@sveltejs/adapter-cloudflare`: full SSR + progressive Form Actions.

## 4. Minimal SvelteKit 3 Config (`vite.config.ts`)
```ts
import adapter from '@sveltejs/adapter-node';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
export default defineConfig({
  plugins: [sveltekit({ adapter: adapter(), csrf: { trustedOrigins: [] }, csp: { mode: 'auto' } })],
});
```
