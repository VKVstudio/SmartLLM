# Architecture Router (Late 2026 — Offline 32K Orchestrator)

Inputs: `site_type` (`landing|corporate|docs_editorial|saas_marketing_app|webapp_dashboard`), `dynamic_data` (`none|forms_only|periodic_cms|realtime_per_user`), `auth_required` (`bool`), `seo_priority` (`critical|high|none`), `interactivity_level` (`low|medium|high`), `offline_zero_build_required` (`bool`).

## Deterministic Decision Tree (`IF / ELSE`)
1. `IF offline_zero_build_required`:
   - **Pick:** `html5_esm` (if `forms_only`, add external edge webhook). **Forbid:** `astro`, `sveltekit`, `nextjs`, `vite_ts`.
   - **Reject/Escalate** if `auth_required == true` (static HTML cannot hold authoritative session auth without a BFF).
2. `ELSE IF seo_priority == none AND (site_type == webapp_dashboard OR (auth_required AND interactivity_level == high))`:
   - **Pick:** `vite_ts` `8.3.8` + TS `7.x` (+ same-origin `/api/*` BFF) OR `sveltekit`/`nextjs` if unified repo preferred. **Forbid:** `html5_esm`.
3. `ELSE IF seo_priority IN [critical, high] AND NOT auth_required AND dynamic_data IN [none, forms_only, periodic_cms]`:
   - **Pick:** `html5_esm` or `astro` (`interactivity == low` landing); else **`astro` `7.4.13`** (Content Layer Zod v4 + Islands + Actions/`server:defer`). **Forbid:** `vite_ts`.
4. `ELSE` (`seo_priority IN [critical, high]` + `auth_required` or `realtime_per_user`):
   - **Pick:** **`nextjs` `16.4.6` Active LTS** (React 19.3, PPR/DAL, multi-tenant SaaS) OR **`sveltekit` `3.4.0`** + Svelte `5.59.1` (leaner runtime, progressive forms). **Forbid:** `html5_esm`, `vite_ts`.

## Compact JSON Decision Matrix
```json
[
  {"id":"R1","match":{"offline_zero_build_required":true,"auth_required":false},"recommend":"html5_esm","forbid":["astro","sveltekit","nextjs","vite_ts"],"reason":"Zero-build offline preview; optional edge webhook for forms"},
  {"id":"R2","match":{"offline_zero_build_required":false,"seo_priority":"critical","auth_required":false,"dynamic_data":["none","forms_only"],"interactivity_level":"low","site_type":"landing"},"recommend":"html5_esm","alt":["astro"],"forbid":["vite_ts","nextjs"],"reason":"0 KB framework runtime; peak LCP/INP & raw HTML crawlability"},
  {"id":"R3","match":{"offline_zero_build_required":false,"seo_priority":["critical","high"],"auth_required":false,"dynamic_data":["none","forms_only","periodic_cms"],"site_type":["landing","corporate","docs_editorial"]},"recommend":"astro","alt":["sveltekit"],"forbid":["vite_ts"],"reason":"Static-first HTML + Content Layer Zod v4 + Islands"},
  {"id":"R4","match":{"offline_zero_build_required":false,"seo_priority":["critical","high"],"auth_required":true,"dynamic_data":"realtime_per_user","interactivity_level":["medium","high"]},"recommend":"nextjs","alt":["sveltekit"],"forbid":["html5_esm","vite_ts"],"reason":"RSC/PPR ('use cache' + Suspense) SEO shell + DAL auth"},
  {"id":"R5","match":{"offline_zero_build_required":false,"seo_priority":["critical","high"],"auth_required":true,"dynamic_data":["forms_only","realtime_per_user"],"interactivity_level":["low","medium"]},"recommend":"sveltekit","alt":["nextjs","astro"],"forbid":["html5_esm","vite_ts"],"reason":"Svelte 5 runes + +page.server.ts actions/use:enhance"},
  {"id":"R6","match":{"offline_zero_build_required":false,"seo_priority":"none","site_type":"webapp_dashboard","interactivity_level":"high"},"recommend":"vite_ts","alt":["sveltekit","nextjs"],"forbid":["html5_esm"],"reason":"No SEO; Vite 8.3 Rolldown + TS 7.x + same-origin BFF"}
]
```
- **Hard Guard:** NEVER pick `vite_ts` (pure CSR SPA) when `seo_priority IN [critical, high]`; `OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot` & OG scrapers parse raw initial HTML without executing JS.
