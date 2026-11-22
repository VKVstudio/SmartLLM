# Stack 2: `astro` — Astro 7.4.x Content-First MPA + Islands

## 1. Verified Late-2026 Versions & Primitives
- **Version (Nov 2026):** **Astro `7.4.13`** (Nov 18, 2026). `7.0.0` (June 22, 2026) migrated to **Vite 8 / Rolldown** + Rust `.astro` compiler (Oxc + Lightning CSS) + *Sätteri* Rust Markdown pipeline; `7.1` added `script-src-elem`/`style-src-elem` CSP granularity; `7.4` added `astro build --timings`.
- **Bundled Validation:** `import { z } from 'astro/zod'` re-exports **Zod v4** natively (graduated in Astro 6.0).
- **Content Layer API:** `src/content.config.ts` with `defineCollection({ loader: glob(...) | file(...) | customLoader, schema: z.object(...) })`.
- **Zero-JS Default + Client Islands:** `.astro` templates ship `0 KB` JS. Hydrate islands explicitly: `client:visible` (below-fold), `client:idle` (non-critical), `client:load` (critical above-fold only), `client:media`, `client:only`.
- **Static + On-Demand Hybrid:** `output: 'static'` is default (merged legacy `hybrid`). Add an adapter (`@astrojs/node`, `@astrojs/cloudflare`, `@astrojs/vercel`) and set `export const prerender = false` per dynamic route.
- **Server Islands (`server:defer`):** Cache page shell on CDN while streaming dynamic fragments with `<div slot="fallback">`. Guarded by `security.serverIslandBodySizeLimit`.
- **Astro Actions (`astro:actions`):** `defineAction({ accept: 'form' | 'json', input: z.object(...), handler })` in `src/actions/index.ts`. Supports native `<form action={actions.lead}>` + type-safe client RPC (`security.actionBodySizeLimit` default 1 MB).
- **Typed Secrets (`astro:env`):** Schema in `astro.config.mjs` enforces `client/public` vs `server/secret`.
- **Primary Docs:** `https://astro.build/blog/`, `https://docs.astro.build/en/guides/actions/`, `https://docs.astro.build/en/guides/server-islands/`, `https://docs.astro.build/en/reference/configuration-reference/`.

## 2. Critical Late-2026 Astro Caveats (Skeptic-Verified)
1. **Astro 7 Rust Compiler Strict HTML:** The Rust compiler no longer auto-closes malformed tags — any LLM-generated `.astro` file MUST pass strict HTML tag balance validation before `astro build`.
2. **`security.csp: true` Is INCOMPATIBLE with `<ClientRouter />`:** Official Astro docs explicitly mark `<ClientRouter />` (and unhashed inline Shiki blocks) incompatible with `security.csp`. When enabling strict `security.csp: true` (graduated in 6.0), omit `<ClientRouter />` and use CSS `@view-transition { navigation: auto; }` progressive enhancement instead.
3. **Static CSP `<meta>` Drops `frame-ancestors`:** Static Astro builds emit `<meta http-equiv="content-security-policy">`, where browsers silently ignore `frame-ancestors`, `sandbox`, and `report-to`. Static deploys STILL require HTTP headers (`_headers` / Nginx) for clickjacking protection.
4. **CSP Disabled in `astro dev`:** `security.csp` emits NOTHING in `astro dev` — always verify CSP headers/hashes in `astro build` + `astro preview`.

## 3. Frontend <-> Backend Channel & Trust Boundary
- **Channels:** Build-time Content Layer, Astro Actions (`POST /_actions/*`), Server Islands (`/_server-islands/*`), SSR API endpoints (`prerender = false`).
- **Built-in Guards:** `security.checkOrigin: true` (default, **SSR only**) validates `Sec-Fetch-Site` + `Origin` on unsafe form requests (`403` on mismatch). `security.allowedDomains` (**SSR only**) allowlists trusted `X-Forwarded-Host` patterns.
- **Trust Rules:** Every Action is a public endpoint — enforce authz (`context.locals.user`), Zod v4 `input` allowlisting, rate limits, and DTO projection inside `handler`. Never pass secrets as props to `client:*` or `server:defer` islands (encrypted Server Island props traverse the client).

## 4. Build & Config Pattern (`astro.config.mjs`)
```js
import { defineConfig, envField } from 'astro/config';
import node from '@astrojs/node';
export default defineConfig({
  output: 'static',
  adapter: node({ mode: 'standalone' }),
  security: { checkOrigin: true, csp: true, allowedDomains: [{ hostname: 'example.com' }] },
  env: { schema: { CRM_TOKEN: envField.string({ context: 'server', access: 'secret' }) } },
});
```
*(Offline preview: `output: 'static'` without adapter builds `dist/` servable by static HTTP; SSR/Actions/`server:defer` require `astro preview` or adapter runtime.)*
