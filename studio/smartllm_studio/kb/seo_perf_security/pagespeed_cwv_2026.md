# PageSpeed & Core Web Vitals Canon (Late 2026)

## 1. Official 2026 Thresholds (CrUX 75th Percentile — web.dev)
| Metric | Good Threshold | SmartLLM Target | Focus Area |
|---|---|---|---|
| **LCP** (Loading) | `<= 2.5 s` | `<= 1.5 s` | Hero image & critical CSS |
| **INP** (Responsiveness) | `<= 200 ms` | `<= 80 ms` | Main-thread yields & passive scroll |
| **CLS** (Visual Stability) | `<= 0.10` | **`0.00`** | Reserved media & font metrics |
| **TTFB** *(diagnostic)* | `<= 800 ms` | `<= 200 ms` static | Edge caching & compression |
| **LoAF** *(diagnostic)* | `<= 50 ms` frame | `0` long frames | Break up JS tasks `> 50 ms` |

## 2. LCP (`<= 2.5s`) — Eliminating Render Blockers & Traps
- **CRITICAL LCP `opacity: 0` TRAP:** Per W3C LCP spec, browsers exclude `opacity: 0` elements from LCP timing until painted visibly. **NEVER attach scroll-reveal `opacity: 0` (`[data-reveal]`) to `#hero`, hero `<h1>`, or hero `<img>`!** Above-the-fold hero content MUST paint immediately at `opacity: 1`.
- **Hero Image Delivery:** Serve AVIF/WebP (`<picture>` fallback), set `fetchpriority="high" loading="eager" decoding="sync"`, and **NEVER put `loading="lazy"`** on LCP images. Preload hero image via `<link rel="preload" as="image" fetchpriority="high">` if hidden inside CSS or `<picture>`.
- **Critical CSS & Fonts:** Inline critical CSS (hashed in CSP) or bundle lean single stylesheet; self-host subsetted `.woff2`; never issue external Google Fonts / unpkg requests.

## 3. CLS (`0.00`) — Zero Layout Shift
- **Explicit Geometry:** Every `<img>` and `<svg>` MUST carry integer `width` and `height` HTML attrs (read from real PNG IHDR) + matching CSS `aspect-ratio`.
- **Font Fallback Metrics:** `@font-face` uses `font-display: swap` + tuned `size-adjust`, `ascent-override`, `descent-override`, and `unicode-range` splitting (`cyrillic` `U+0400-04FF` + `latin` `U+0000-00FF`).
- **Dynamic Viewport (`svh`/`dvh`):** Size hero folds with `min-height: min(86svh, 840px)` and modals with `100dvh`. **BAN raw `100vh`.**

## 4. INP (`<= 200ms`) & Late-2026 Platform APIs
- **`scheduler.yield()` (NOT in Safari!):** Supported in Chrome 129+ and Firefox 142+, unsupported in Safari as of Nov 2026. Always feature-detect before breaking >50ms tasks:
  ```js
  const yieldMain = () => globalThis.scheduler?.yield ? scheduler.yield() : new Promise((r) => setTimeout(r, 0));
  ```
- **CSS Scroll-Driven Animations (`scroll()` / `view()`):** **Baseline Newly Available (Oct 2026)** — Chrome 115+, Safari 26+, Firefox 159+. Prefer compositor-thread CSS scroll timelines inside `@supports (animation-timeline: view())` and `@media (prefers-reduced-motion: no-preference)`.
- **Compositor-Only Transforms:** Animate `transform`, `opacity`, `clip-path` ONLY (never `top`, `left`, `width`, `height`, `margin`, `backdrop-filter` radius). Attach `{ passive: true }` to all scroll/wheel/touch listeners.
- **Below-Fold Rendering Skip:** Apply `content-visibility: auto; contain-intrinsic-size: auto 600px;` (Baseline: Chrome 85+, FF 125+, Safari 18+) to lower sections (`#features`, `#gallery`, `#faq`, `#footer`), NEVER on `#hero`.

## 5. Compression, Caching & Speculation Rules
- **`Content-Encoding: zstd`:** Baseline Feb 2026 (Chrome 123+, Firefox 126+, Safari 26.3+); **caveat:** Safari 26.3 only supports `zstd` on **macOS 26.3 Tahoe / iOS 26.3+**. Always negotiate via `Accept-Encoding` with Brotli (`br`) and `gzip` fallback.
- **Immutable Static Assets:** `Cache-Control: public, max-age=31536000, immutable` on fingerprinted `/assets/*`; `max-age=0, must-revalidate` on HTML.
- **Speculation Rules API (Limited Availability — Chromium):** Use progressive enhancement (`eagerness: "moderate"` `prefetch`, excluding `/logout`, `#`, external URLs). Prefer external **`Speculation-Rules: "/speculation.json"` HTTP header** so strict hash-only CSP stays clean without inline speculation hashes.
