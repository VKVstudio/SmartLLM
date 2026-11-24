# Engineering baseline (all canons)

- Always loaded with the chosen canon spec and `_ux_baseline.md`. It says how to build; the canon says how it looks. On engineering this file wins.
- Sections start with `<!-- section:NAME -->`; read only what the task needs. `[assumption]` = unverified default.
- Assets: A = code-only motion, B = Z-Image stills, C = video/frame sequences (deferred, never now).

<!-- section:architecture -->
## Architecture
- Build static-first. Every page is plain HTML made at build time. Why: static HTML loads fast, is cheap to host and has no server to attack.
- Add JS only as "islands": small interactive parts; the rest ships no JS.
- Island loading: when visible (`client:visible`, below the fold), when idle (`client:idle`), at once (`client:load`, rarely: it competes with first paint).
- Shared layout partials: one base layout holds `<head>`, SEO tags, JSON-LD, skip link and footer. Pages add only their header and sections. One fix applies everywhere.
- Suggested folders (Astro-like): `pages/[lang]/`, `layouts/`, `components/{layout,sections,blocks,ui}/`, `data/` (typed content), `i18n/`, `styles/`, `functions/` (same-origin edge endpoints), `public/` (`robots.txt`, `llms.txt`, headers, redirects).
- Content as data: keep prices, FAQ and facts in one data file. Build both the HTML and the JSON-LD from it, so they cannot drift apart.
- i18n: every route under a language prefix (`/en/…`); `/` redirects to the default language; strings via `t(lang, key)` with fallback; the language switch keeps the same page.

<!-- section:front_back -->
## Front/back separation
- The site must build and work without any backend. A backend is an extra, never a requirement.
- Graceful fallback:
  - if an API is down, the widget shows a clear static message or demo state, not a blank box;
  - if a JS chunk fails to load, all hidden content becomes visible (see Performance).
- Forms post only to a same-origin endpoint (`functions/api/<name>`). Why: same-origin keeps CSP strict and avoids CORS.
- If a separate API origin is needed, list it explicitly in CSP `connect-src` and pass its URL at build time as a public variable.
- Secrets live only in the hosting provider's environment settings. They never enter the repo, the HTML or client JS.
- The edge endpoint forwards to mail or storage with a signed request (for example HMAC over method, path, timestamp and body hash), so the receiver can reject forged calls [assumption].

<!-- section:security -->
## Security
- Content-Security-Policy (CSP) made at build time, per page:
  - hash every inline `<script>` and `<style>` (SHA-256) and list the hashes in the policy;
  - never use `'unsafe-inline'` or `'unsafe-eval'`. They switch off most of the protection;
  - fail the build if a page needs something the policy does not allow.
- Baseline policy shape: `default-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'` (or `'none'` if forms use fetch), plus `require-trusted-types-for 'script'`.
- Trusted Types: route every HTML sink (`innerHTML` and similar) through one small policy with a sanitizer. The browser then blocks raw string injection.
- No inline event handlers (`onclick=`). They need `unsafe-inline` or extra hashes.
- Subresource Integrity (SRI): add `integrity="sha384-…"` to script and style files. The browser refuses a file whose hash changed.
- Headers on all pages: HSTS `max-age=31536000; includeSubDomains; preload`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `X-Frame-Options: DENY`, COOP and `Cross-Origin-Resource-Policy: same-origin`, a `Permissions-Policy` denying camera, microphone, geolocation, payment, USB unless needed.
- Cache: hashed build assets `immutable` for 1 year; HTML short or `no-cache`.

<!-- section:forms -->
## Form hardening
- The server never trusts the client. Client validation is only for user comfort.
- Checks on the endpoint, in this order:
  - allow only the needed method (POST), else 405;
  - check `Origin` equals the site and `Sec-Fetch-Site: same-origin`, else 403. This blocks cross-site posts;
  - accept only `application/json` (or the one form type you use), else 415;
  - cap the body size (for example 16 KB), else 413;
  - validate with a schema (for example Zod): enums, max lengths, email format. Reject unknown fields;
  - honeypot: a hidden field that humans leave empty. If it is filled, reject quietly;
  - optional bot check (a privacy-friendly captcha) verified on the server;
  - rate limit per IP (for example a few requests per minute), answer 429 with `Retry-After`;
  - fail closed: if a needed config value is missing, reject instead of sending.
- Errors: short JSON, `no-store`, no stack traces.

<!-- section:performance -->
## Performance (PageSpeed)
- Targets: LCP ≤ 2.5s, INP ≤ 200ms, CLS ≤ 0.1 at the 75th percentile.
- CSS: inline small CSS so there is no render-blocking stylesheet. Keep critical HTML+CSS near 14 KB compressed when possible.
- JS: dynamic `import()` for motion libraries, and only after the reduced-motion check. Why: a static import puts the library on every page.
- CSS-first reveals: content is visible by default. JS adds the "hidden before reveal" state only when it runs. If the script fails, a safety timer or `catch` shows everything.
- Start non-critical animation after first paint.
- Canvas and WebGL (class A):
  - cap device pixel ratio at about 1.5–2. Why: a DPR 3 phone draws over 2× the pixels of DPR 2 for little visible gain;
  - pause when off screen (IntersectionObserver) and when the tab is hidden (`visibilitychange`);
  - cap object counts (particles, nodes);
  - `pointer-events: none` on decorative layers.
- No heavy assets on mobile:
  - use one shared media query for the "mobile" gate in CSS, JS and preload tags;
  - do not put a heavy `<img>` in the DOM if it is only hidden by CSS. Hidden images still download. Insert it with JS on the branch that needs it;
  - mobile gets a still image (B) instead of a canvas scene.
- Images: `<picture>` with AVIF, then WebP, then JPEG; explicit `width` and `height`; `loading="lazy"` below the fold; `fetchpriority="high"` on the LCP image only.
- Fonts: WOFF2 subsets per language, preload only the fonts used above the fold, `font-display: swap`.
- Smooth scroll libraries: enable only on fine pointers with hover; keep native scroll on touch.

<!-- section:motion_safety -->
## Motion safety
- Every motion has a reduced-motion version. In CSS wrap motion in `@media (prefers-reduced-motion: no-preference)`. In JS check `matchMedia('(prefers-reduced-motion: reduce)')` before loading any library.
- Reduced motion means "no tweening", not "no interaction". Buttons and menus still work, with instant changes.
- A canvas under reduced motion draws one static frame.
- Animated targets get their own `js-*` classes, separate from styling classes, so a CSS refactor does not break motion.

<!-- section:vendor -->
## Vendor and stack
- All fonts (SIL OFL-1.1 woff2, latin + latin-ext + cyrillic) and JS (MIT) are vendored in `studio/smartllm_studio/templates/vendor/`. The studio copies them to `assets/fonts/<id>/` and `assets/vendor/<lib>/`. Never load from a CDN. Why: fewer CSP origins and fully offline builds.
- Each canon's `vendor` section lists only its font ids and JS libraries.
- Default stack now: `html5_esm` (fully offline). npm stacks (`astro`, `nextjs`, `sveltekit`, `vite_ts`) need `npm install`; their packages are not vendored.
- GSAP is not vendored (license-restricted). Use Motion, anime.js, Lenis, three.js, or native CSS (scroll-driven animations, View Transitions).
- CSS scroll-driven animations (`animation-timeline: scroll()/view()`) are Baseline since October 2026; still wrap them in `@supports` for older browsers.

<!-- section:seo -->
## SEO
- Canonical URL is built from the current route, never hard-coded to the home page.
- `hreflang` for every language plus `x-default`, in the head and in the sitemap. Each page lists all versions, itself included.
- Open Graph and Twitter tags: title, description, URL, locale, image 1200×630 with alt.
- Sitemap: language alternates included; noindex pages excluded; `lastmod` = the last git commit date of the page source, not the build time. Why: Google uses `lastmod` only when it is consistently accurate.

<!-- section:aeo_geo -->
## AEO / GEO (answer engines and AI search)
- JSON-LD as separate nodes linked by `@id`:
  - sitewide `WebSite` (`@id: <site>/#website`) and `Organization` (`@id: <site>/#org`);
  - per page `WebPage` (`@id: <canonical>#webpage`) with `inLanguage` and `isPartOf: {"@id": "<site>/#website"}`;
  - page-specific types (`Service`, `Product`, `Article`, `Event`) point to the same ids.
- Structured data must describe content that is visible on the page.
- `FAQPage` only on a page that visibly shows those questions and answers, built from the same data. Google stopped showing FAQ rich results on 7 May 2026. The markup may still help other answer engines read the page [assumption].
- `robots.txt`: allow normal crawlers, add explicit allow groups for AI crawlers you want (for example GPTBot, OAI-SearchBot, ClaudeBot, PerplexityBot, Google-Extended, Applebot-Extended), then the `Sitemap:` line.
- `llms.txt` at the root: an H1 with the name, a one-paragraph `>` summary, then `##` sections with links (services, pages, contact, notes for AI assistants).
- Write answer-first: each section starts with a one-sentence direct answer, then details.

<!-- section:hard_limits -->
## Hard limits
- No `unsafe-inline` or `unsafe-eval` in CSP. No inline `on*=` handlers.
- No secrets in the repo, HTML or client JS.
- Every form is validated again on the server.
- The site builds and works without a backend.
- Every motion has a reduced-motion version.
- No asset class C (video, frame sequences) now.
- Self-hosted fonts and scripts, no third-party CDNs. Works offline.
- FAQPage JSON-LD only where the FAQ is visible.
