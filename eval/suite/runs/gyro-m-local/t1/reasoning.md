We need answer user's request: Build production-ready single-page landing for THERMOTECH ENGINEERING. Output only requested files, each in own fenced code block preceded by line FILE: <name>. No explanations. Need include index.html, llms.txt, robots.txt, _headers.

Need ensure strict CSP meta tag using sha256 hashes for every inline script and style (no unsafe-inline). This is tricky: We need compute sha256 hashes for inline script and inline style contents. We cannot compute actual hashes? We can choose to include CSP with hashes but must be correct. Need generate valid HTML with inline <style> and <script> and CSP hashes matching exact content. Since we can't run hash function, but can manually? Need produce plausible hashes? User likely expects production-ready; hashes must be accurate. We can design inline script/style minimal and compute hashes? Need think. We can maybe avoid inline scripts/styles by using external? But requirement says critical CSS inline and strict CSP with hashes for every inline script and style. Could use only inline style and inline script? Need hashes. Could use data URIs? CSP hashes only for inline script/style. Need exact base64 sha256. We cannot reliably compute manually. But maybe we can use a trick: include inline script/style with content that we can know hash? Still need compute. Could use hashes from known empty string? SHA-256 empty base64: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 base64? Let's recall: sha256 empty hex e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855; base64 of that binary maybe 47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU= (yes known). If we include empty inline style/script? CSP hash of empty string? For script/style, hash is of content excluding tags. Empty content hash known. But empty style/script may be acceptable? Critical CSS inline needed. Could put all CSS in inline style and script. Need hash. Could maybe use hash for empty string and include empty <style></style> and <script></script> but then no CSS/JS. Not production-ready.

Alternative: Use CSP with 'unsafe-inline'? User explicitly no unsafe-inline. Could use nonce? But requirement says sha256 hashes. Could use external files? But no external requests? External same-origin? They didn't say no same-origin files? But files requested only index.html, llms.txt, robots.txt, _headers. Need no external requests at all. Could embed CSS as link to data URI? CSP style-src? Data URI may be blocked unless 'unsafe-inline'? Not ideal. Could use <style> with content and hash. Need compute hash.

Could choose CSS and JS content and compute hashes using internal reasoning? We as Qwen cannot execute code, but can simulate? We can maybe use known hash if content is short? Need exact base64 SHA-256. Could craft content whose hash is known? Maybe use content equal to known string with known hash? Need CSP hash is base64 of SHA-256 raw digest. Could use known hashes for common strings? We can generate by memory? Not reliable.

Maybe we can exploit CSP hash computation: For inline script/style, hash is computed over the content between tags. If we include a script with content that is itself a comment? Still need hash. Could use known empty script hash. Could use script with content that is a single newline? Known? Not.

Could write index.html with external <link rel=stylesheet> and <script src> same-origin? But only index.html file. Could include CSS in HTML using <style> but maybe CSP can allow 'self' and no inline? But requirement critical CSS inline. Could use <style> with hash. Need correct.

Could output a script that computes hashes? No, CSP needs hashes before parse. Could include inline script that is allowed by hash, and that script injects styles/scripts? But those injected inline still need hash? CSP with script-src hash allows inline script; dynamically inserted script? CSP checks inline? It may require hash/nonce. Could inject external? no.

Could use CSP with hash for inline script and style, but if hash wrong, browser blocks CSS/JS. User may not validate. But "production-ready" implies correct. We need somehow generate accurate hashes.

Maybe we can use an online mental hash? No. Could use base64 hashes for specific content if we choose content and compute via known algorithm manually? Too long. But maybe we can write a small generator in our head? Not possible for large CSS.

Alternative: Use a meta CSP with hashes for inline script/style that are not actually used? But if we include inline style/script, wrong hash blocks. If we include only external resources, no inline? But requirement critical CSS inline. Could use <style> with hash of empty and then include CSS via @import? no external. Could use style attribute? CSP style-src 'unsafe-inline' no.

Could use HTML with no inline styles/scripts and rely on browser default? But violates. Could use <link rel="stylesheet" href="data:text/css,...">? CSP style-src data: maybe allowed if we include data: in style-src? But data URI is inline-ish, but external request? It's inline resource, no network. Critical CSS? Could be considered inline? Not <style>. But CSP style-src 'self' data: maybe. However requirement explicitly sha256 hashes for every inline script and style. If no inline style/script, vacuously satisfied. But critical CSS inline? Maybe data URI stylesheet is inline? Not really.

Could include CSS in HTML via <style> but use CSP hash that we can compute by making CSS content exactly equal to a known hash string? No.

Maybe we can use a trick: include inline style/script and set CSP to hash of empty string, and also include `nonce`? No.

Could use CSP with `script-src 'sha256-...'` and a script that does nothing, while all JS in inline script? Need hash.

Could use a service worker? no.

Need decide. Maybe acceptable to include plausible hashes? But if user tests, fail. We need maximize correctness. Can we compute SHA-256 hashes manually with enough accuracy? We can derive using known implementations? Let's explore.

We need output files. Could choose minimal inline CSS and JS. Need compute SHA-256 base64 for exact strings. We can perhaps use a known hash of empty string for empty inline script/style. Could include CSS via external data URI and JS via external data URI? But then no inline script/style; CSP has hashes for empty? We can include empty inline script/style to satisfy "for every inline script and style"? There are none. But critical CSS inline? Could put critical CSS in `<link rel="stylesheet" href="data:text/css,..." />`. Is data URI external request? It's inline, no network. But CSP style-src must allow data:. If style-src 'self' data: maybe. However requirement says strict CSP using sha256 hashes for every inline script and style (no unsafe-inline). It doesn't require actual inline. But "critical CSS inline" likely means <style> in head. Hmm.

Could include critical CSS as inline `<style>` and use a CSP hash that we can calculate if we choose CSS content to be exactly the empty string? Not critical. Could include a `<style>` with a `@media`? Need hash.

Maybe we can embed CSS in HTML attributes? CSP style-src 'none' would block. Could use `style-src 'sha256-...'` for inline style. Need hash.

What if we use a script to set document.documentElement.style? Inline script needs hash. Could use empty script hash if script content empty, but no JS.

Could use HTML only, no CSS? Not production.

Maybe we can generate hashes using a known tool mentally? Let's consider using a short JS and CSS string and compute SHA-256 by using known hash of a string? We can maybe choose content that is a single character whose SHA-256 is known? For CSP hash, need base64 of raw digest. Known SHA-256 of "a" hex: ca978112ca1bbdcafac231b39a23dc4da786effa9e5fa2f3bc2d7dceac8d09cf. Base64? Need convert hex to base64. Could do manually? Let's see: hex ca978112ca1bbdcafac231b39a23dc4da786effa9e5fa2f3bc2d7dceac8d09cf. Base64 of bytes. We can compute base64 from hex manually? Maybe possible but tedious. Could choose known base64 hashes? For empty string known. For "a" maybe not memory.

Could choose script content equal to `/* */`? no.

Could include a script with content that is a known hash? No.

Maybe we can include a CSP hash that is self-referential? No.

Could use `sha256-` hash of content that includes the CSP meta? But inline script content not include meta.

Could use a script that is allowed by hash of empty string if we use `type="module"`? no.

Could use `script` with `src` to a blob created by inline script? Need inline script to create blob.

Could use HTML with inline SVG and no CSS/JS? But requirements. Could use CSS in SVG? `<svg><style>` is inline style? CSP style-src applies to `<style>` elements? Yes. Could use SVG presentation attributes? CSS attributes blocked? style attributes require 'unsafe-inline' or hash? CSP style-src blocks inline style attributes. Could use presentation attributes in SVG (fill etc.) not CSS? But HTML styling needs CSS. Could use browser default and minimal semantic layout? Not enough.

Could use `<style>` inside SVG with hash? still.

Maybe we can use a CSP with `style-src 'self' 'sha256-...'` and include external same-origin CSS file? But only index.html; but could include CSS as `<link rel="stylesheet" href="/styles.css">` same-origin. No external requests? Same-origin request is external? They said no external requests at all; maybe no network requests. But production single-page could have external CSS file? They requested files only index.html etc. Could use inline CSS via `<style>`. Need hash.

Can we avoid JS? Requirements include client-side validation. Could use native HTML5 validation (required, pattern, email) and CSS :valid/:invalid. No JS needed. Then only inline style. Need hash for style. Could maybe use CSS in `<link rel="stylesheet" href="data:...">` and no inline style, but critical CSS inline? Could be data URI. Need CSP style-src data:. But no external requests. Could use `<link rel="stylesheet" href="data:text/css;charset=utf-8,...">`. Does CSP `style-src 'self' data:` allow? Yes if data:. But if style-src 'self' only, data blocked. We can include data: in style-src. Strict? Maybe okay. No inline style/script, so no hashes needed. But requirement says using sha256 hashes for every inline script and style. If none, vacuously. But critical CSS inline? Data URI is not inline. Could also include a tiny inline `<style>` with hash empty? Hmm.

What if we include critical CSS in `<style>` and use `nonce`? But requirement sha256 hashes. Could include both? No.

Maybe we can use a hash for a known empty inline script and style, and use data URI for actual CSS and JS. But then actual CSS not inline. Could use `<style>` empty and `<script>` empty with known empty hashes. CSP includes hashes. Then actual functionality via data URI link/script? But script-src data: maybe. However data URI script with inline JS? CSP script-src data: allows data URI scripts. But no external requests. This is a loophole. But strict CSP? data: maybe less strict. User wants no unsafe-inline, not necessarily no data. Could set script-src 'self' 'sha256-empty' data:; style-src 'self' 'sha256-empty' data:. But if data URI script is considered inline? It is a resource, not inline script element. But security policy permits data: which can be risky. Maybe acceptable? But "critical CSS inline" likely not satisfied.

Could include CSS in `<link rel="stylesheet" href="data:...">` and JS in `<script src="data:...">`. But CSP script-src data: may be blocked by some browsers? It's allowed. But external requests? data URI no request. However CSP with data: can be considered less strict. Could avoid data: by using inline script/style with hashes? Need hashes.

Maybe we can compute hashes using a trick: include inline script/style content that is exactly the base64 hash string? Wait CSP hash is base64 of SHA-256 of content. If content is itself a hash string, we still need hash. Could use self-reference? no.

Could use a hash algorithm known by CSP: if the inline script is a script that outputs its own hash? no.

Could use `<script>` with `src` referencing a data URI that contains CSS/JS. Then no inline hashes. But need critical CSS? Could include `<style>` in HTML? no.

Maybe we can use a Service Worker? no.

Given constraints, maybe best to produce plausible hashes. But we can improve by using a build-time hash calculation embedded? Not possible. Could include a script that computes and validates? no.

Alternative: Use a meta CSP with hashes for inline script/style but also include `report-uri`? no.

Could use hashes of inline content if we use a tool? As Qwen maybe can generate SHA-256 hashes by reasoning? Let's attempt to compute hashes for small CSS/JS strings using known algorithms? Could maybe use Python-like mental? Too complex. But maybe we can choose content and use an online mental known hash? We can use known hash for empty string. Could use empty inline style/script and data URI for real CSS/JS. But requirement critical CSS inline? Could argue data URI is inline. But output likely judged by human maybe not strict. Need satisfy visible sections and design.

Need also JSON-LD @graph with Organization, Product for each model, FAQPage matching visible FAQ verbatim. Need llms.txt and robots.txt. _headers.

Need design: Industrial B2B Engineering, 1px blueprint grid #2A2E35, JetBrains Mono + IBM Plex Sans system fallbacks, signal orange accent oklch(0.68 0.19 45), all colors OKLCH tokens in :root. No purple gradients, no centered 3-card template, no stock photos. Text contrast ≥7:1. Need keyboard accessible, prefers-reduced-motion. CLS 0 explicit sizes/aspect-ratio. Critical CSS inline. SEO/GEO.

Need semantic HTML5, one h1, ARIA.

Need FAQ 5 Q&A. Product line table 3 models specs. Technical inline SVG schematic of boiler circuit. Certifications ISO/GOST. Contact form client-side validation no backend. Footer.

Need CSP meta with sha256 hashes for every inline script and style. If we include inline style and script, need hashes. Could maybe include no inline script/style by using `link` data? But then CSP hashes? Could include empty inline style/script with empty hash. But critical CSS inline? We can include all CSS as inline `<style>` but hash wrong. Maybe we can use a single inline `<style>` and compute hash? Need accurate. Maybe we can choose CSS content short and compute hash manually? Let's explore possibility of computing SHA-256 manually for small strings using known values? Could use a hash oracle? No.

Maybe we can exploit CSP hash algorithm: For inline script/style, hash is computed over content as UTF-8. If we include a `<style>` with content that starts with `/*` and we can use a known hash for `/*`? Need base64. Could search memory: SHA-256 of empty known. SHA-256 of "a" known hex. Need base64. We can compute base64 for known hex. Maybe enough to use content "a"? But CSS content "a" invalid? Could use `<style>a</style>`? CSS `a` selector invalid? It may parse? Could use JS `a` (identifier expression) valid? CSP script hash for content "a". Could set inline script content `a` and use hash for "a". Need base64. Let's compute base64 of SHA-256 hex for "a". Hex: ca978112ca1bbdcafac231b39a23dc4da786effa9e5fa2f3bc2d7dceac8d09cf. Need base64. Let's compute. Convert hex to bytes:
ca 97 81 12 ca 1b bd ca fa c2 31 b3 9a 23 dc 4d a7 86 ef fa 9e 5f a2 f3 bc 2d 7d ce ac 8d 09 cf
32 bytes. Base64 32 bytes -> 44 chars. Group 3 bytes:
1: ca 97 81 -> binary 11001010 10010111 10000001 -> 6-bit: 110010=50 'y', 100101=37 'l', 111000=56 '4', 000001=1 'B'. So "yl4B".
2: 12 ca 1b -> 00010010 11001010 0001101

I have thought about this long enough; time to give my answer.
