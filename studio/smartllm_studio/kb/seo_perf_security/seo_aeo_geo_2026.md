# SEO, AEO & GEO Canons (Late November 2026)

## 1. Google Search Essentials & AI Overviews (Nov 2026)
- **2025–2026 Core & Spam Timeline:** Core Updates in Mar 27–Apr 8, May 21–Jun 2, and **Nov 10, 2026** (plus Feb 5 Discover Update & Mar/Jun/Aug/Sep Spam Updates).
- **AI Overviews & AI Mode (Google Search Central):** Eligibility = standard indexing + snippet eligibility (no special AI tags). Uses RAG + **Query Fan-Out** (citing pages that answer specific sub-questions clearly). Control snippets via `nosnippet` / `data-nosnippet` / `max-snippet:[N]` (`Google-Extended` controls Gemini training, NOT Search indexing).

## 2. AI Crawler Governance Matrix (`robots.txt`)
| Vendor | Training (Block) | Search Citation Index (Allow) | Live User Fetcher | Executes JS? |
|---|---|---|---|---|
| OpenAI | `GPTBot` | `OAI-SearchBot` | `ChatGPT-User` | **No** (raw HTML) |
| Anthropic | `ClaudeBot` | `Claude-SearchBot` | `Claude-User` | **No** (raw HTML) |
| Perplexity | — | `PerplexityBot` | `Perplexity-User` | **No** (raw HTML) |
| Google | `Google-Extended` | `Googlebot` | `GoogleOther` | **Yes** (WRS) |
| Apple | `Applebot-Extended` | `Applebot` | — | Partial |

- **Operational Rules:** (1) Main copy, tables, and `<script type="application/ld+json">` MUST exist in raw initial SSR/SSG HTML (`OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot` do NOT run JS); (2) Ensure CDN/WAF does not `403` allowed search bots; (3) Include `Claude-SearchBot: Allow /` in `robots.txt`.

## 3. Schema.org JSON-LD `@graph` (2026 Status)
- **Retired from Google Rich Results (Verified):**
  - **`FAQPage`:** Google retired FAQ rich results **globally on May 7, 2026** (removed from GSC/RRT June 2026, API Aug 2026). **Policy:** Keep valid `FAQPage` in `@graph` ONLY for AEO/LLM Q&A extraction, keeping **100% verbatim parity** with visible HTML Q&A text.
  - **`HowTo` / `Sitelinks Searchbox` / June 2025 Cleanup** (`Course Info`, `ClaimReview`, `Estimated Salary`, `Learning Video`, `Special Announcement`, `Vehicle Listing`, `Practice Problem`): Retired — omit as SERP targets.
- **Active Unified `@graph` Nodes (Linked via `@id`, escape `</` -> `<\/`):**
  1. `Organization` (`#org`): real `name`, `url`, `logo`, `telephone`, `email`, `PostalAddress` (dynamic ISO-3166-1 alpha-2 `addressCountry` — NEVER hardcoded), `sameAs` entity URLs.
  2. `LocalBusiness` (`#localbusiness`, physical office sites only): exact NAP parity with footer, `openingHoursSpecification`.
  3. `WebSite` + `WebPage`: `publisher`, `inLanguage`, real ISO `dateModified`.
  4. `BreadcrumbList`: **sub-pages only** (never emit self-referencing breadcrumb on `index`).
  5. `Product` / `Service`: emit `Product` ONLY with real numeric `offers`, `review`, or `aggregateRating` (NEVER fake `"price": "0"` on paid tiers!); otherwise emit `Service` / `OfferCatalog`.
  6. `Article` / `BlogPosting`: `headline`, `author` (`Person` + `jobTitle`), `datePublished`, `dateModified`, `image`.

## 4. `llms.txt` & Princeton GEO Citation Engineering
- **`/llms.txt` (`llmstxt.org`):** Spec-compliant UTF-8 Markdown (`# Title`, `> Summary blockquote`, `## Section` link lists). Adopted by AI coding tools/docs; **explicitly NOT a Google Search ranking signal** (John Mueller confirmed Google ignores it). Generate cleanly without marketing it as an SEO trick.
- **GEO Citation Rules (Princeton KDD '24 + 2026 RAG):**
  - **Answer-First:** Open key `<h2>`/`<h3>` answers with a self-contained **40–60 word** direct statement.
  - **Verifiable Statistics & Citations (+30–40%):** Grounded metrics with units/dates/scope from `foundation.json` (keyword stuffing degrades citations `-10%`).
  - **Semantic `<table>` Matrices:** Use real `<table><thead><tbody><th scope="col">` for specs/pricing.
  - **Visible E-E-A-T:** Real team names/roles, real dates, complete legal/contact footprint.

## 5. Technical SEO Hygiene
- **Canonicals:** Absolute self-referencing `<link rel="canonical">` on every indexable page.
- **`hreflang` (Strict Rule):** Emit bidirectional + `x-default` ONLY when distinct crawlable URLs exist per language (`/en/...`, `/ru/...`). **NEVER emit `hreflang` on single-URL JS-switched bilingual pages.**
- **Headings & Slugs:** Single `<h1>`, monotonic `h1->h2->h3`, ASCII/transliterated slugs.
- **XML Sitemap:** Emit `<loc>` + accurate `<lastmod>` only. Omit ignored `<priority>` and `<changefreq>`.
- **Social Meta & Bans:** Full OpenGraph (incl. `og:image` `1200×630` + `width`/`height`/`alt`) + `twitter:card="summary_large_image"`. **BAN `<meta name="keywords">`.**
