# Stack 1: `html5_esm` — Zero-Build Semantic HTML5 + OKLCH CSS + Native ESM

## 1. Verified Late-2026 Platform Primitives
- **Color & Design Tokens:** `oklch()` + CSS Relative Color Syntax (Baseline Widely Available); cascade locked via `@layer reset, tokens, base, layout, components, utilities;`.
- **Native Top-Layer UI (Zero JS libs):** `<dialog>`, Popover API (`popover`), CSS Anchor Positioning (`position-anchor`, `position-area`), `@starting-style` + `transition-behavior: allow-discrete`, HTML Invoker Commands (`commandfor`, `command="show-modal" | "toggle-popover"`).
- **Navigation Transitions:** Same-document `document.startViewTransition()` is **Baseline Newly Available** (Chrome 111+, Safari 18.2+, Firefox 144+). Cross-document MPA `@view-transition { navigation: auto; }` is **Limited Availability** (Chrome 126+, Safari 18.2+; Firefox Nightly ~161 behind experimental flag, NOT in Firefox 159/160 stable) — emit strictly as zero-cost progressive enhancement.
- **Native Modules:** `<script type="module">` + `<script type="importmap">` (no bundler).
- **Sanitization Caveat (Nov 2026):** HTML Sanitizer API (`Element.setHTML()`) shipped unflagged in **Chrome 146+** and **Firefox 148+** (refined in FF 159), but is **NOT in Safari** (NOT Baseline). Never rely solely on `setHTML()` without DOMPurify + server-side sanitization fallback.
- **Primary Docs:** `https://web.dev/baseline`, `https://developer.mozilla.org/en-US/docs/Web/CSS/@view-transition`, `https://developer.mozilla.org/en-US/docs/Web/API/HTML_Sanitizer_API`.

## 2. Folder Topology
```text
site/
├── index.html, about.html, contact.html   # Pure semantic MPA pages
├── assets/
│   ├── css/{reset.css,tokens.css,layout.css,components.css}
│   ├── js/{main.js,islands/form.js}       # Native ESM, deferred by default
│   ├── img/*.{avif,webp,png}              # Explicit width/height
│   └── fonts/*.woff2                      # Self-hosted SIL OFL, font-display: swap
├── _headers, robots.txt, sitemap.xml, llms.txt
└── functions/api/contact.ts               # Optional Edge/serverless webhook
```

## 3. Frontend <-> Backend Channel & Trust Boundary
- **Channel:** Native `<form method="POST" action="/api/contact">` (progressively enhanced with `fetch()` + `FormData`) or static-only (`0` backend).
- **Serverless Webhook Contract (Authoritative Boundary):**
  - HTML5 `required`/`pattern`/`type="email"` is UX-only; Edge handler MUST re-validate with Zod v4 (`safeParse`), strip unknown fields, enforce body-size caps, check anti-abuse (Turnstile/rate-limit/honeypot), and validate **`Sec-Fetch-Site`** (`same-origin`/`none`, reject `cross-site`) + **`Origin`** allowlist.
  - Never embed CRM/SMTP/API keys in `<script type="module">` or hidden inputs.
  - Never reflect unsanitized user HTML into confirmation views or emails.
  - Prefer reverse-proxied same-origin `/api/*` route; if cross-origin, allowlist exact origins (never `*` with credentials).

## 4. Build, Deployment & Offline Preview
- **Build:** Zero Node build step.
- **Offline Preview:** Serve via local HTTP (`http://127.0.0.1:PORT`) — ES modules enforce CORS and fail under raw `file://` if importing sub-modules.
- **Deploy:** Cloudflare Pages (remember `_headers` does NOT apply to Pages Functions — attach headers in `functions/_middleware.ts`), Netlify, Nginx, S3+CloudFront.

## 5. Best Fit / Anti-Patterns
- **Best Fit:** SmartLLM Studio zero-build output, marketing landings, corporate brochure MPAs, portfolios, offline deliverables.
- **Anti-Patterns:** Authenticated user portals, multi-step server state, large blogs (`>30` pages without templating).
