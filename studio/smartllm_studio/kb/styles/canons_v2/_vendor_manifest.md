# _vendor_manifest — offline assets for canons_v2

Not loaded by the model. Owner/agent reference. Source of truth for files: `studio/smartllm_studio/templates/vendor/MANIFEST.json` (schema 2026.11.2, verified 2026-11-22). Re-verified 2026-11-23: all 236 files on disk match MANIFEST sha256 and size; every font folder has the SIL OFL 1.1 text; JS LICENSE files are MIT.
Total: 30 font families + 4 JS libs, 7.12 MB. Policy (`LICENSES.json`): offline self-hosted only; JS MIT/Apache-2.0; fonts OFL-1.1; subsets latin + cyrillic mandatory.
In a generated site the studio (`templates_engine.bundle_vendor_assets_for_canon`) copies fonts to `assets/fonts/<id>/` and JS to `assets/vendor/<lib>/`. Lenis is bundled together with motion/animejs/three.

## Status of new downloads
- Nothing new needed for canons 01–20: every font named in `canon_cards`/`kb/styles/canons/*.json` is already vendored (checked all 20), and all catalog motion ids (motion, animejs, lenis, three) are vendored. Added 2026-11-23 for 14_spatial_3d_showcase: three.js addons GLTFLoader, BufferGeometryUtils, SkeletonUtils, OrbitControls (same 0.187.0 npm tarball, MIT, 211 KB) in `js/three/addons/`; import map `three` → `three.module.js`, `three/addons/` → `addons/`. ⚠ Engine gap (code, not changed): `bundle_vendor_assets_for_canon` copies only `three.module.js`, but it imports `./three.core.js`, and addons are not copied — needs a studio fix to copy the whole `js/three/` folder. `css_scroll_driven`, `reduced_motion_instant`, View Transitions are native.
- GSAP: NOT vendored (see verdict below).
- Stack npm packages: NOT vendored, needs owner decision. Measured `node_modules` for current versions (linux-x64, 2026-11-23): astro 7.4.13 ≈ 190 MB (192 pkgs); vite 8.3.8 + typescript 7.0.2 + zod 4.6.7 ≈ 74 MB; @sveltejs/kit 3.4.0 + svelte 5.59.1 + vite + adapter-static ≈ 47 MB; next 16.4.6 + react 19.3.1 ≈ 341 MB. Each is over or near the 50 MB limit, and native binaries are per-OS. Non-MIT/Apache licenses inside: `@img/sharp-libvips-*` LGPL-3.0-or-later (astro, next), `lightningcss` MPL-2.0 (astro, vite, sveltekit), `caniuse-lite` CC-BY-4.0 (next), `lru-cache`/`sax`/`common-ancestor-path` BlueOak-1.0.0, `mdn-data` CC0. Options: (a) keep `html5_esm` as the fully offline default; (b) an offline npm tarball cache per OS outside git; (c) accept the extra licenses. Not done until owner says.

## GSAP licence verdict (read 2026-11-23 from the GSAP Standard "No Charge" License page on gsap.com, effective 30 Apr 2025, last modified 30 May 2025; npm gsap 3.15.1 declares "Standard 'no charge' license")
Quoted clauses:
- Grant (II): "Webflow grants you a non-exclusive, worldwide license to use, reproduce, display, and implement GSAP Products solely for Permitted Uses."
- Permitted Uses (I): "the implementation and/or use of GSAP Products on any website, web application, or digital interface by any person or entity (which may include, for clarity, those of companies that compete with Webflow in other areas of business)."
- Prohibited Uses (I): "any implementation and/or use of GSAP Products in tools that allow users to build visual animations without code that encourages, induces, or materially assists in creating a solution that competes with Webflow's visual animation building capabilities."
- Competitive Products (I): "any software, tool, or service that enables users to create, edit, or manage animations through a visual interface or builder similar to Webflow."
- Restrictions (III): "You may not: Use any GSAP Products for any Prohibited Uses without prior written consent; Reverse engineer any GSAP Products for the purpose of creating Competitive Products; Remove or alter any proprietary notices or branding from GSAP Products."
- Ownership (IV): "All intellectual property rights in GSAP Products ... remain the exclusive property of Webflow." Termination (V): "Webflow may terminate this GSAP License and revoke your access in its discretion if you fail to comply..." Amendments (VI): "Webflow reserves the right to update or modify this GSAP License at any time..."
- Governing: "This GSAP License is incorporated into and subject to Webflow's Terms of Service ... In the event of any conflict ... the terms of this GSAP License shall govern" (Webflow ToS effective 15 Nov 2023; nothing GSAP-specific found in it).
- FAQ: "Is it acceptable for AI tools like ChatGPT, Cursor, Lovable, Webstudio, etc. to generate GSAP code? Absolutely! AI-generated code is not a 'Prohibited Use'." and "If you are not sure if your product might be considered a 'Prohibited Use', feel free to contact us".
- Note: the page's "Plain English Summary" still says use is free "as long as end users are not charged a fee of any kind" and points to a paid "Business" Club membership. The legal clauses above do not contain that fee condition. The two texts on the same page conflict.
Answers:
1. Redistribution in the public SmartLLM repo (FSL-1.1-ALv2 / Apache): NOT CLEARLY ALLOWED. The grant says "reproduce" but only "solely for Permitted Uses" (use on a website/app/interface); it does not grant distribution or sublicensing, it is not an OSI licence, it cannot be relicensed under Apache/FSL, and Webflow can amend or terminate. Repo users would get GSAP under Webflow's terms, not ours. → Do not vendor. Matches studio `LICENSES.json` (`builder_bundling_safe: false`).
2. Is SmartLLM Studio a Prohibited Use? AI generation of GSAP code is explicitly NOT prohibited (FAQ). The risk appears only if Studio ships GSAP inside its own runtime AND gives users a visual, no-code way to build or edit animations (motion presets/pickers could be read as "build visual animations without code"). Grey area → keep GSAP out of the Studio runtime; ask Webflow in writing if GSAP-based visual motion controls are ever wanted.
3. May generated sites include GSAP? YES: use "on any website, web application, or digital interface" is a Permitted Use, commercial included. Safe form: the user's own project installs it (`npm i gsap`) when the user chooses it; SmartLLM does not ship the file. Watch the fee wording in the summary if the generated site charges end users.
Rule for specs: GSAP = "optional, license-restricted, not vendored". Defaults: Motion (MIT), anime.js v4 (MIT, has `splitText`, `onScroll`, timelines, stagger), Lenis (MIT), CSS scroll-driven animations, View Transitions.

## Files
| asset | version | license | size B | local path (under `studio/smartllm_studio/templates/vendor/`) | sha256 | used by canons |
|---|---|---|---|---|---|---|
| manrope | 5.3.0 | SIL OFL-1.1 | 4383 | `fonts/manrope/LICENSE` | `d826ab6583b12c26807d8716a545bdbbb672df04f48608a364ba9efdbe501c30` | 01 |
| manrope | 5.3.0 | SIL OFL-1.1 | 14500 | `fonts/manrope/manrope-cyrillic-wght-normal.woff2` | `c268b459a9329e59fecf39a17618efd44c71735532048d60b12aab76a8c14914` | 01 |
| manrope | 5.3.0 | SIL OFL-1.1 | 15120 | `fonts/manrope/manrope-latin-ext-wght-normal.woff2` | `3911b66d9f2e005a4b989223405d0e5032619c668597ba467cc76a23c8fffcfb` | 01 |
| manrope | 5.3.0 | SIL OFL-1.1 | 24836 | `fonts/manrope/manrope-latin-wght-normal.woff2` | `a30ddcd349703aff7464c34bef3fffdff405ee50c113440d7c8693c02d210972` | 01 |
| manrope | 5.3.0 | SIL OFL-1.1 | 1160 | `fonts/manrope/font.css` | `1cedd99d713c4146b9a5d3303030a75319b00b28401bb5c74479b75fda998380` | 01 |
| inter | 5.3.0 | SIL OFL-1.1 | 4477 | `fonts/inter/LICENSE` | `3b0a5fca3d17942cde889069889dedbbbd075e9b599968c82a95f4d944e9b345` | 01 |
| inter | 5.3.0 | SIL OFL-1.1 | 18748 | `fonts/inter/inter-cyrillic-wght-normal.woff2` | `71d5ee93cc1e9f1d520a3a8b66456de18c7879d8df09d57fcd2eaff75fef0075` | 01 |
| inter | 5.3.0 | SIL OFL-1.1 | 85068 | `fonts/inter/inter-latin-ext-wght-normal.woff2` | `34b9c504cab7a73e37b746343a449132e56cf7b5481af2cb81dc74dcff25c956` | 01 |
| inter | 5.3.0 | SIL OFL-1.1 | 48256 | `fonts/inter/inter-latin-wght-normal.woff2` | `3100e775e8616cd2611beecfa23a4263d7037586789b43f035236a2e6fbd4c62` | 01 |
| inter | 5.3.0 | SIL OFL-1.1 | 19980 | `fonts/inter/inter-cyrillic-wght-italic.woff2` | `47d42151dff6d13f1c2b9a1f278290f625593c1f01c89612ee4ae7f063167f7a` | 01 |
| inter | 5.3.0 | SIL OFL-1.1 | 91900 | `fonts/inter/inter-latin-ext-wght-italic.woff2` | `71254244ccb1ec21e14db3480fef6f6826d1136dc4aca1c7d3ca7ce31294fcce` | 01 |
| inter | 5.3.0 | SIL OFL-1.1 | 51832 | `fonts/inter/inter-latin-wght-italic.woff2` | `7291b5970da2237441273c03b424a504b70b18f09791473fab99687dcc314720` | 01 |
| inter | 5.3.0 | SIL OFL-1.1 | 2273 | `fonts/inter/font.css` | `7ced209b80d10ba0e3d5ad22308618fc931e4e951fc08a35e58d9e2a4cb9c9f6` | 01 |
| golos_text | 5.3.0 | SIL OFL-1.1 | 4392 | `fonts/golos_text/LICENSE` | `54dcae300688bccf111e43c818a6ee2261d10fc8d7eb5b9c9aa2a1e9b03189c9` | 02,06,19 |
| golos_text | 5.3.0 | SIL OFL-1.1 | 22032 | `fonts/golos_text/golos-text-cyrillic-wght-normal.woff2` | `17d048ca05cb1218af3c0d6dcdf882989e6d1cc5dcb598ea50eaf54850ff7229` | 02,06,19 |
| golos_text | 5.3.0 | SIL OFL-1.1 | 19180 | `fonts/golos_text/golos-text-latin-ext-wght-normal.woff2` | `05befabe4813f41238ce6ea4f5ecd6b758591e9ef2f303a9932bff68ba66dc66` | 02,06,19 |
| golos_text | 5.3.0 | SIL OFL-1.1 | 37916 | `fonts/golos_text/golos-text-latin-wght-normal.woff2` | `9a69d0aa4734c4022224c002a3d944a702e0204972a49d892789f5668b922c2a` | 02,06,19 |
| golos_text | 5.3.0 | SIL OFL-1.1 | 1196 | `fonts/golos_text/font.css` | `4b06e40259b4ff5bd98dbb7aa0049de524ba3d59a1b375d150c8441999bb3b2b` | 02,06,19 |
| ibm_plex_sans | 5.3.0 | SIL OFL-1.1 | 4429 | `fonts/ibm_plex_sans/LICENSE` | `d0283623ef57e722fd0eb688a8041589670c608ab780cd3612d06ba6f153d3fd` | 02,07,17 |
| ibm_plex_sans | 5.3.0 | SIL OFL-1.1 | 29512 | `fonts/ibm_plex_sans/ibm-plex-sans-cyrillic-wght-normal.woff2` | `9409ee21811f0f5272b7e1d828fe8838005b0573481ef906e7e55b63f6610ab0` | 02,07,17 |
| ibm_plex_sans | 5.3.0 | SIL OFL-1.1 | 30964 | `fonts/ibm_plex_sans/ibm-plex-sans-latin-ext-wght-normal.woff2` | `d160e20920ae4d6556518d352d3af27a74e9b0de3d8fe17b1c1044fc75aa2f81` | 02,07,17 |
| ibm_plex_sans | 5.3.0 | SIL OFL-1.1 | 45712 | `fonts/ibm_plex_sans/ibm-plex-sans-latin-wght-normal.woff2` | `e2291e842cf5af167122a22881a740c7f2dda7716f1e8cd76680264f4a859470` | 02,07,17 |
| ibm_plex_sans | 5.3.0 | SIL OFL-1.1 | 32632 | `fonts/ibm_plex_sans/ibm-plex-sans-cyrillic-wght-italic.woff2` | `e71db60f3419842ad61305fcb22100fc0ea34f6aaa98d1f028de948751f08d88` | 02,07,17 |
| ibm_plex_sans | 5.3.0 | SIL OFL-1.1 | 33900 | `fonts/ibm_plex_sans/ibm-plex-sans-latin-ext-wght-italic.woff2` | `bf44b77cc751203b2f0ce95c048a9d8f984313f84b58106c7c4410ca50314016` | 02,07,17 |
| ibm_plex_sans | 5.3.0 | SIL OFL-1.1 | 50184 | `fonts/ibm_plex_sans/ibm-plex-sans-latin-wght-italic.woff2` | `4363757d2695c7633f98472855849f7c30528eba869d7968ee35b58c87cf14c1` | 02,07,17 |
| ibm_plex_sans | 5.3.0 | SIL OFL-1.1 | 46012 | `fonts/ibm_plex_sans/ibm-plex-sans-cyrillic-wdth-normal.woff2` | `d0c0257292881fee5bffd2671c380772c22e94f78e1e4bd9ad840aa0fcdef5f0` | 02,07,17 |
| ibm_plex_sans | 5.3.0 | SIL OFL-1.1 | 46744 | `fonts/ibm_plex_sans/ibm-plex-sans-latin-ext-wdth-normal.woff2` | `d43e5954a3549d82ea11577d0aa403fe00cb334aaefae6b58bc6ba0542c146d2` | 02,07,17 |
| ibm_plex_sans | 5.3.0 | SIL OFL-1.1 | 65488 | `fonts/ibm_plex_sans/ibm-plex-sans-latin-wdth-normal.woff2` | `1e875856600a34cb44a406a7deef0e3f9ae70e6f636e0f37fbca2248dec2dca4` | 02,07,17 |
| ibm_plex_sans | 5.3.0 | SIL OFL-1.1 | 3776 | `fonts/ibm_plex_sans/font.css` | `0675033dbf42ed61ae7c13f2a7e8e80cd4891193af45b082ddae7e75b61be002` | 02,07,17 |
| ibm_plex_mono | 5.3.0 | SIL OFL-1.1 | 5299 | `fonts/ibm_plex_mono/LICENSE` | `23b0a9d0c6d3f140a0b77e483c5cfa6bba574325ef5cb189ed9f2fec4884533f` | 02,17 |
| ibm_plex_mono | 5.3.0 | SIL OFL-1.1 | 8356 | `fonts/ibm_plex_mono/ibm-plex-mono-cyrillic-400-normal.woff2` | `7635422bd10ddbbcb0e0caa1154b928298f5c8319b8c00b30978d4395f4783ce` | 02,17 |
| ibm_plex_mono | 5.3.0 | SIL OFL-1.1 | 13348 | `fonts/ibm_plex_mono/ibm-plex-mono-latin-ext-400-normal.woff2` | `6bc0f226a5b7884a8170e3f62c63d7675609d4631bdc5931b5cdab81821f00eb` | 02,17 |
| ibm_plex_mono | 5.3.0 | SIL OFL-1.1 | 14708 | `fonts/ibm_plex_mono/ibm-plex-mono-latin-400-normal.woff2` | `08949f728dc52d528e69b1667d15c89a5686a4ee9a296ff90983985f99c380f7` | 02,17 |
| ibm_plex_mono | 5.3.0 | SIL OFL-1.1 | 10404 | `fonts/ibm_plex_mono/ibm-plex-mono-cyrillic-400-italic.woff2` | `4aded3f2f2a7d27d9430ca6f6ef9dc7d7efa861a61891a5f67758d467da9ed14` | 02,17 |
| ibm_plex_mono | 5.3.0 | SIL OFL-1.1 | 14524 | `fonts/ibm_plex_mono/ibm-plex-mono-latin-ext-400-italic.woff2` | `1b07eee6df7d26b31864581c2365131d384077605e0b63ae67c4a0a64363a6de` | 02,17 |
| ibm_plex_mono | 5.3.0 | SIL OFL-1.1 | 16448 | `fonts/ibm_plex_mono/ibm-plex-mono-latin-400-italic.woff2` | `0840095faae86403735a8c04014b72cb29e7923646b222b360b7e8252932e4e3` | 02,17 |
| ibm_plex_mono | 5.3.0 | SIL OFL-1.1 | 8460 | `fonts/ibm_plex_mono/ibm-plex-mono-cyrillic-500-normal.woff2` | `1d89462e86cb8e87e7e9d6f6635605bd7c3081baca6caaecee84916bf7b60edc` | 02,17 |
| ibm_plex_mono | 5.3.0 | SIL OFL-1.1 | 13432 | `fonts/ibm_plex_mono/ibm-plex-mono-latin-ext-500-normal.woff2` | `6bb06407c97584b0867a959e05e8874693bfeb8c317de190811c51598f2d99ea` | 02,17 |
| ibm_plex_mono | 5.3.0 | SIL OFL-1.1 | 14888 | `fonts/ibm_plex_mono/ibm-plex-mono-latin-500-normal.woff2` | `01d285447409c8a588692162439a038b8cbd7871309ee20267b0d2d91c6e8e22` | 02,17 |
| ibm_plex_mono | 5.3.0 | SIL OFL-1.1 | 10668 | `fonts/ibm_plex_mono/ibm-plex-mono-cyrillic-500-italic.woff2` | `52243493496143dd07224d8a6cda80107d91e57b2abb83924f31052f834948d2` | 02,17 |
| ibm_plex_mono | 5.3.0 | SIL OFL-1.1 | 14676 | `fonts/ibm_plex_mono/ibm-plex-mono-latin-ext-500-italic.woff2` | `57216564e5a42dde14048f03e32caa40c97d9b2b440be1aa2ea87ff324fbc95e` | 02,17 |
| ibm_plex_mono | 5.3.0 | SIL OFL-1.1 | 16484 | `fonts/ibm_plex_mono/ibm-plex-mono-latin-500-italic.woff2` | `528cc360f6e6f5210526a33b6ed8f2c37084bd0c73b918f25a55f48b40c4ac52` | 02,17 |
| ibm_plex_mono | 5.3.0 | SIL OFL-1.1 | 9352 | `fonts/ibm_plex_mono/ibm-plex-mono-cyrillic-600-normal.woff2` | `2b05a8695c7f9f4abd7178b279646a3b005a8ce57546bef6fd145f25d131e0aa` | 02,17 |
| ibm_plex_mono | 5.3.0 | SIL OFL-1.1 | 14328 | `fonts/ibm_plex_mono/ibm-plex-mono-latin-ext-600-normal.woff2` | `32057cf50dd14bdb21a2c93766c4a2c43e4abe688ea3922df3203cac7751a98b` | 02,17 |
| ibm_plex_mono | 5.3.0 | SIL OFL-1.1 | 15620 | `fonts/ibm_plex_mono/ibm-plex-mono-latin-600-normal.woff2` | `0d1f0b8d0722224e32e9f28261bdc86c79115be73444ae5eceb73976a1bcdf83` | 02,17 |
| ibm_plex_mono | 5.3.0 | SIL OFL-1.1 | 11472 | `fonts/ibm_plex_mono/ibm-plex-mono-cyrillic-600-italic.woff2` | `20811c3ee42d0e1d4cb1f6e4554a38720c9bd5fda2a85acb03636560d6e63a70` | 02,17 |
| ibm_plex_mono | 5.3.0 | SIL OFL-1.1 | 15460 | `fonts/ibm_plex_mono/ibm-plex-mono-latin-ext-600-italic.woff2` | `979f73fb848c600282d2c2e48e6dc67eeb02d47b520c9fa48b0af65fbef09da4` | 02,17 |
| ibm_plex_mono | 5.3.0 | SIL OFL-1.1 | 17356 | `fonts/ibm_plex_mono/ibm-plex-mono-latin-600-italic.woff2` | `42a8ca72a19c5ee1612ac3e35f52d08f34a09856c9466dc87a21101ad230ed6b` | 02,17 |
| ibm_plex_mono | 5.3.0 | SIL OFL-1.1 | 7127 | `fonts/ibm_plex_mono/font.css` | `91643b268fbe167e056c21c45b8b95c0aa06daf490901f017a04cf2ee626b08b` | 02,17 |
| source_serif_4 | 5.3.1 | SIL OFL-1.1 | 4314 | `fonts/source_serif_4/LICENSE` | `18aabf190848725e2576eefb5c29ba06aac1029d02132252a7f312eac2e50cf3` | 03 |
| source_serif_4 | 5.3.1 | SIL OFL-1.1 | 36508 | `fonts/source_serif_4/source-serif-4-cyrillic-wght-normal.woff2` | `a81082707b85203d7f2ae33833f7ae0bf832db167c8710f92f805a9808fb051a` | 03 |
| source_serif_4 | 5.3.1 | SIL OFL-1.1 | 42212 | `fonts/source_serif_4/source-serif-4-latin-ext-wght-normal.woff2` | `d10ccbbd0dc4ebae2938958dc1f622a53460fe297e9c958564742dd684309c3f` | 03 |
| source_serif_4 | 5.3.1 | SIL OFL-1.1 | 50936 | `fonts/source_serif_4/source-serif-4-latin-wght-normal.woff2` | `382475f38242c52d42a3e5ff8dc69b5d73f10d0d21e4550b5fe232984688779a` | 03 |
| source_serif_4 | 5.3.1 | SIL OFL-1.1 | 34972 | `fonts/source_serif_4/source-serif-4-cyrillic-wght-italic.woff2` | `62faaf044db101ae07f9be3f23424892fa9c792d8d4eadcde3b7a8cd6d27909d` | 03 |
| source_serif_4 | 5.3.1 | SIL OFL-1.1 | 44420 | `fonts/source_serif_4/source-serif-4-latin-ext-wght-italic.woff2` | `14e38c2d6a4ea6effcddde38f0262c03af252cbf82dbc68037f2d6c9112f2097` | 03 |
| source_serif_4 | 5.3.1 | SIL OFL-1.1 | 51576 | `fonts/source_serif_4/source-serif-4-latin-wght-italic.woff2` | `b4f56ddc9873487f1c9a3ad5bbce31982fe89b951f57e4604f62b4c8a540fb19` | 03 |
| source_serif_4 | 5.3.1 | SIL OFL-1.1 | 2489 | `fonts/source_serif_4/font.css` | `4d843e780be73405dfb0305cbe9a84cb45e1498f9b79447f4dd1577a497f1831` | 03 |
| source_sans_3 | 5.3.1 | SIL OFL-1.1 | 4314 | `fonts/source_sans_3/LICENSE` | `18aabf190848725e2576eefb5c29ba06aac1029d02132252a7f312eac2e50cf3` | 03,10,16,19 |
| source_sans_3 | 5.3.1 | SIL OFL-1.1 | 18496 | `fonts/source_sans_3/source-sans-3-cyrillic-wght-normal.woff2` | `b6b721e08d0324b9e743858e8260463085d4c5e1e684f036f9d4a8ca6c62996f` | 03,10,16,19 |
| source_sans_3 | 5.3.1 | SIL OFL-1.1 | 60088 | `fonts/source_sans_3/source-sans-3-latin-ext-wght-normal.woff2` | `a85a7459bdb3cdc1136751e151a506bae653fc29ada3ca86237477df6f1b59e6` | 03,10,16,19 |
| source_sans_3 | 5.3.1 | SIL OFL-1.1 | 28872 | `fonts/source_sans_3/source-sans-3-latin-wght-normal.woff2` | `19143dca075972bc84e3fd9eab7416dd40cc565dccb2435a044bdfabe060c7d5` | 03,10,16,19 |
| source_sans_3 | 5.3.1 | SIL OFL-1.1 | 18724 | `fonts/source_sans_3/source-sans-3-cyrillic-wght-italic.woff2` | `747ba5266ef049efc6d67eaa99058a81efa134ec00483c246ed388ef288186d2` | 03,10,16,19 |
| source_sans_3 | 5.3.1 | SIL OFL-1.1 | 59496 | `fonts/source_sans_3/source-sans-3-latin-ext-wght-italic.woff2` | `6fe10a66ec416f77a26309b645471d032ad8175063bb605b886e9b7e57efaaa8` | 03,10,16,19 |
| source_sans_3 | 5.3.1 | SIL OFL-1.1 | 28460 | `fonts/source_sans_3/source-sans-3-latin-wght-italic.woff2` | `5fbc14d56cea35e60596c72ca969b349443c6a536f74e11748eed8b3a396e61d` | 03,10,16,19 |
| source_sans_3 | 5.3.1 | SIL OFL-1.1 | 2465 | `fonts/source_sans_3/font.css` | `6aadeacf2fa8da4a555190019f2dbd65abf86bf003414506ed7f3cfbccf1ee0d` | 03,10,16,19 |
| source_code_pro | 5.3.1 | SIL OFL-1.1 | 4314 | `fonts/source_code_pro/LICENSE` | `18aabf190848725e2576eefb5c29ba06aac1029d02132252a7f312eac2e50cf3` | 03,13,15 |
| source_code_pro | 5.3.1 | SIL OFL-1.1 | 14180 | `fonts/source_code_pro/source-code-pro-cyrillic-wght-normal.woff2` | `fd7699ecbd3ce9ae5db900abc491150d176e8b1530aee9a9268cb3023658a5b3` | 03,13,15 |
| source_code_pro | 5.3.1 | SIL OFL-1.1 | 33568 | `fonts/source_code_pro/source-code-pro-latin-ext-wght-normal.woff2` | `ab316ee7e4a28a149fe9f74a3e9173c3d14a11bb7d4df898dd2fe10da7b7fe24` | 03,13,15 |
| source_code_pro | 5.3.1 | SIL OFL-1.1 | 22044 | `fonts/source_code_pro/source-code-pro-latin-wght-normal.woff2` | `8b774aaa5137a38ef40f4ac9d36db9a5eee152b2f66589dfdc82ff007fc87135` | 03,13,15 |
| source_code_pro | 5.3.1 | SIL OFL-1.1 | 2384 | `fonts/source_code_pro/source-code-pro-cyrillic-wght-italic.woff2` | `9d5a510257df6c4b14f63b979c89af8be75c828edf1311a69eb945c63f986344` | 03,13,15 |
| source_code_pro | 5.3.1 | SIL OFL-1.1 | 34012 | `fonts/source_code_pro/source-code-pro-latin-ext-wght-italic.woff2` | `da6214a7b9f9eca88a7ae3b7b6fec00db41741774d8a38e6a899bd8e85968411` | 03,13,15 |
| source_code_pro | 5.3.1 | SIL OFL-1.1 | 22448 | `fonts/source_code_pro/source-code-pro-latin-wght-italic.woff2` | `97f01332aeda642a2f298030203dd4dd72802c0288ab2705d33daf691278e563` | 03,13,15 |
| source_code_pro | 5.3.1 | SIL OFL-1.1 | 2513 | `fonts/source_code_pro/font.css` | `8679d05a01dff2d99994bcc8ad6d19329310ff7de70f6131ae0a3c7717445d49` | 03,13,15 |
| geist | 5.3.0 | SIL OFL-1.1 | 4486 | `fonts/geist/LICENSE` | `71609cbb5c78b5870d712eab73a31d76622635c6ed034ab5cee3b9ecbda8685f` | 04,18 |
| geist | 5.3.0 | SIL OFL-1.1 | 15084 | `fonts/geist/geist-cyrillic-wght-normal.woff2` | `6894439694946a589d157ece003086960a6a4013d74a813dab7602efdb3d8c09` | 04,18 |
| geist | 5.3.0 | SIL OFL-1.1 | 16512 | `fonts/geist/geist-latin-ext-wght-normal.woff2` | `824f485b5d26e2f2da3c2b236132ece1bc8e4e43373452950bb0e40548b4313f` | 04,18 |
| geist | 5.3.0 | SIL OFL-1.1 | 29400 | `fonts/geist/geist-latin-wght-normal.woff2` | `19f9c92546aa300c312235e3125af1b81394d8db9a4bc4a425cd5b641d2d54e1` | 04,18 |
| geist | 5.3.0 | SIL OFL-1.1 | 15960 | `fonts/geist/geist-cyrillic-wght-italic.woff2` | `a7684bfc9a77331f2a59560c61b2a6ecf11482570b3a6d61bf869dca1c91c530` | 04,18 |
| geist | 5.3.0 | SIL OFL-1.1 | 17892 | `fonts/geist/geist-latin-ext-wght-italic.woff2` | `56dc9ac98e3fc45e7ee487d03ee205b35858c672f2e15053eabbb119c0bc1e74` | 04,18 |
| geist | 5.3.0 | SIL OFL-1.1 | 31008 | `fonts/geist/geist-latin-wght-italic.woff2` | `9b10496762af92659f3b05d2b084b0c8f962c3ecdf637aa764e3b7fd17f5acaf` | 04,18 |
| geist | 5.3.0 | SIL OFL-1.1 | 2273 | `fonts/geist/font.css` | `72940d937db5ec1086e94244452753ccf4b8c88718ced6cadcfafa4f4a37a81b` | 04,18 |
| geist_mono | 5.3.0 | SIL OFL-1.1 | 4498 | `fonts/geist_mono/LICENSE` | `cc815ed4fc045f0e991abb10395b7932bd028c6a067deb13316d6002105074e6` | 04,18 |
| geist_mono | 5.3.0 | SIL OFL-1.1 | 12940 | `fonts/geist_mono/geist-mono-cyrillic-wght-normal.woff2` | `4866787fc952dbdbd591d6923d67bc21c2d894b93f34ab69d0cdf25d47bfb2df` | 04,18 |
| geist_mono | 5.3.0 | SIL OFL-1.1 | 14696 | `fonts/geist_mono/geist-mono-latin-ext-wght-normal.woff2` | `1a189eb997c3e2ece68373e387afaec9e8617424186c4b1ab3cff7c54ba6223b` | 04,18 |
| geist_mono | 5.3.0 | SIL OFL-1.1 | 23128 | `fonts/geist_mono/geist-mono-latin-wght-normal.woff2` | `684ad5b531f81d43c1e8c7038262d5db7cdc1f68006e04d6c7769efa8d33c8cc` | 04,18 |
| geist_mono | 5.3.0 | SIL OFL-1.1 | 14116 | `fonts/geist_mono/geist-mono-cyrillic-wght-italic.woff2` | `0bed200c47f591ab28726d1a9c1d3b53a4423713c13f5b37b108258ef22eafb1` | 04,18 |
| geist_mono | 5.3.0 | SIL OFL-1.1 | 16440 | `fonts/geist_mono/geist-mono-latin-ext-wght-italic.woff2` | `cde10355ce14bb325e89af19c7609fac1fe90ea741f03a278cb3a11b02fe7f1a` | 04,18 |
| geist_mono | 5.3.0 | SIL OFL-1.1 | 25516 | `fonts/geist_mono/geist-mono-latin-wght-italic.woff2` | `7842d88c32207514dd03ddb9abc6c84b032d6fef58af1177e0b23f6554c80c75` | 04,18 |
| geist_mono | 5.3.0 | SIL OFL-1.1 | 2393 | `fonts/geist_mono/font.css` | `aef786aa57fd2dec2766810ce160b78241da3cf3b55052e62d5cad340ea35ecc` | 04,18 |
| tektur | 5.3.0 | SIL OFL-1.1 | 4383 | `fonts/tektur/LICENSE` | `865c2067daf0c957ed41ee040168088a5253be10df167549defcb775d0bbd0c3` | 05,14 |
| tektur | 5.3.0 | SIL OFL-1.1 | 8664 | `fonts/tektur/tektur-cyrillic-wght-normal.woff2` | `717684b09fd7c875416b30e168f51256ebc7cf811c908218fae6182069e41f01` | 05,14 |
| tektur | 5.3.0 | SIL OFL-1.1 | 14704 | `fonts/tektur/tektur-latin-ext-wght-normal.woff2` | `a6d4d0a825ef9ea09774cf487ca0a6181c6d4b33aeb4d3708d52d6c98526fbd8` | 05,14 |
| tektur | 5.3.0 | SIL OFL-1.1 | 12148 | `fonts/tektur/tektur-latin-wght-normal.woff2` | `2c4e3f0723427b12e30b10fd233c362244963124ecbdd3a3cba40dcf78c3f22e` | 05,14 |
| tektur | 5.3.0 | SIL OFL-1.1 | 14056 | `fonts/tektur/tektur-cyrillic-wdth-normal.woff2` | `231c3c1b2e5e03234fa859f6172974227dfca2aec82320446995b6e37409ca84` | 05,14 |
| tektur | 5.3.0 | SIL OFL-1.1 | 22320 | `fonts/tektur/tektur-latin-ext-wdth-normal.woff2` | `1c99d1742b06ac8d25753af21e775df5ff5b1af936b64a86a58f4ad8c75ac34a` | 05,14 |
| tektur | 5.3.0 | SIL OFL-1.1 | 19196 | `fonts/tektur/tektur-latin-wdth-normal.woff2` | `19d3beb395906c32f206c82d01580e993d257a8872277e254b97c6ca96a64dc1` | 05,14 |
| tektur | 5.3.0 | SIL OFL-1.1 | 2375 | `fonts/tektur/font.css` | `2bae73dc585bf67896ac6abee950fe67932b257b6858699b38c26bfeb6ed0fba` | 05,14 |
| commissioner | 5.3.0 | SIL OFL-1.1 | 4385 | `fonts/commissioner/LICENSE` | `f4bab37ac72f638eeaec7a38cf8f5cc4e91299d763e6befc38e224044730ed8a` | 05,13 |
| commissioner | 5.3.0 | SIL OFL-1.1 | 26188 | `fonts/commissioner/commissioner-cyrillic-wght-normal.woff2` | `1cb81390574ac797658ecabb9d6c50648b01506909c9b0c0c315fbe89f83a689` | 05,13 |
| commissioner | 5.3.0 | SIL OFL-1.1 | 30988 | `fonts/commissioner/commissioner-latin-ext-wght-normal.woff2` | `bd6c9bcd8fddfa16facc4398d075d0dfdf1286fc08334b94e8ea0c94beb1e0ff` | 05,13 |
| commissioner | 5.3.0 | SIL OFL-1.1 | 36700 | `fonts/commissioner/commissioner-latin-wght-normal.woff2` | `e3d539b926881fbb3592788297eee24d6d179c1c06dbad36805fc722775247ce` | 05,13 |
| commissioner | 5.3.0 | SIL OFL-1.1 | 1220 | `fonts/commissioner/font.css` | `8d920a4aa72c9894c5694c7c4fc581b363fac9345cc25f097e6d0abff8bda764` | 05,13 |
| jetbrains_mono | 5.3.0 | SIL OFL-1.1 | 4524 | `fonts/jetbrains_mono/LICENSE` | `403581b69dac5cff4079205e01c6b467e56af449ecbd7247693ddb1baafa005b` | 01,05,08,11,20 |
| jetbrains_mono | 5.3.0 | SIL OFL-1.1 | 12108 | `fonts/jetbrains_mono/jetbrains-mono-cyrillic-wght-normal.woff2` | `d274604c40757f98f07df623a8b8fb5194508a6fa4f5413a7a107f09e3b7452a` | 01,05,08,11,20 |
| jetbrains_mono | 5.3.0 | SIL OFL-1.1 | 15196 | `fonts/jetbrains_mono/jetbrains-mono-latin-ext-wght-normal.woff2` | `79bfdab9ba467e26eea4122e6f2567e188dd8a09a8c730d501fc487c4ab99c6e` | 01,05,08,11,20 |
| jetbrains_mono | 5.3.0 | SIL OFL-1.1 | 40404 | `fonts/jetbrains_mono/jetbrains-mono-latin-wght-normal.woff2` | `18be452724bfdc236c074ca94a249a7f41a86752c7d04ab258ce9ed5651f6a7e` | 01,05,08,11,20 |
| jetbrains_mono | 5.3.0 | SIL OFL-1.1 | 13352 | `fonts/jetbrains_mono/jetbrains-mono-cyrillic-wght-italic.woff2` | `8df3ca627bd8e1cb0e5414f7429fe7a2cf82732b0fc43f2d05bc2c471b64fcfc` | 01,05,08,11,20 |
| jetbrains_mono | 5.3.0 | SIL OFL-1.1 | 16520 | `fonts/jetbrains_mono/jetbrains-mono-latin-ext-wght-italic.woff2` | `60652c78382d7e5021ce4c3ed8985fc41d8f3d1b1a3bedcec2a44ed8979fe5eb` | 01,05,08,11,20 |
| jetbrains_mono | 5.3.0 | SIL OFL-1.1 | 42964 | `fonts/jetbrains_mono/jetbrains-mono-latin-wght-italic.woff2` | `a8afa085e9ca5e53434e2ee918ba6b65c7dd4dda56509976b36591478c99d62e` | 01,05,08,11,20 |
| jetbrains_mono | 5.3.0 | SIL OFL-1.1 | 2489 | `fonts/jetbrains_mono/font.css` | `7c953f1ca96e27fbfa04313e4257490c06f9c56bf88b9a932242aabc9c15915b` | 01,05,08,11,20 |
| unbounded | 5.3.0 | SIL OFL-1.1 | 4390 | `fonts/unbounded/LICENSE` | `48a780bc857729859e54d1e691b05792894a26634edc1c4b5dbeabffe6941758` | 06,09 |
| unbounded | 5.3.0 | SIL OFL-1.1 | 31424 | `fonts/unbounded/unbounded-cyrillic-wght-normal.woff2` | `e30bf6a6063b6a47232bbd657e24c7cf4fdaf76fc2c50d92d9ee63e2ad2087cf` | 06,09 |
| unbounded | 5.3.0 | SIL OFL-1.1 | 118348 | `fonts/unbounded/unbounded-latin-ext-wght-normal.woff2` | `845e1c9fe2e9a7bfbedfeb447fbeba4bc1b5ecd6246277910ccdaad35a7a532c` | 06,09 |
| unbounded | 5.3.0 | SIL OFL-1.1 | 50904 | `fonts/unbounded/unbounded-latin-wght-normal.woff2` | `22f9b928aa3928a896340422b54d690fbb5875c30eae4c106f029c61f2289fd6` | 06,09 |
| unbounded | 5.3.0 | SIL OFL-1.1 | 1184 | `fonts/unbounded/font.css` | `ecb1ffeee3ad54a975b01db82b84f85472a412c446c2d27a2c9b9d150230e452` | 06,09 |
| martian_mono | 5.3.0 | SIL OFL-1.1 | 4389 | `fonts/martian_mono/LICENSE` | `bd7d799f6a67b704f9546422ee83d69b4dc5e4ae289d5eabc22581251dd7150a` | 06,14 |
| martian_mono | 5.3.0 | SIL OFL-1.1 | 10560 | `fonts/martian_mono/martian-mono-cyrillic-wght-normal.woff2` | `2d30189f145a92ec118dc73194c7d813f218db9ec084444f6c071d419ce6b529` | 06,14 |
| martian_mono | 5.3.0 | SIL OFL-1.1 | 15908 | `fonts/martian_mono/martian-mono-latin-ext-wght-normal.woff2` | `c26a87eedc388afebc0c6331d99b248196ea64a883322fc519831278ffd169d5` | 06,14 |
| martian_mono | 5.3.0 | SIL OFL-1.1 | 23556 | `fonts/martian_mono/martian-mono-latin-wght-normal.woff2` | `d0be3a78a854bcea53a9dc26b6620ba322eaa515ccbd92bb4b6ec20a3c91b291` | 06,14 |
| martian_mono | 5.3.0 | SIL OFL-1.1 | 17200 | `fonts/martian_mono/martian-mono-cyrillic-wdth-normal.woff2` | `827d9868a49cc5c27acf71f9467a3c5b060bdc1120ff2194452d3966a077103b` | 06,14 |
| martian_mono | 5.3.0 | SIL OFL-1.1 | 24660 | `fonts/martian_mono/martian-mono-latin-ext-wdth-normal.woff2` | `21fce7e290a2395b70fb1569e1b2ef65b3a2c0a121f28203e23dd9b17d120ed4` | 06,14 |
| martian_mono | 5.3.0 | SIL OFL-1.1 | 38492 | `fonts/martian_mono/martian-mono-latin-wdth-normal.woff2` | `f9c1655c2c9d1ed5bb8b301a57d1169a1123ffef1a588dc50a7a487810f7d732` | 06,14 |
| martian_mono | 5.3.0 | SIL OFL-1.1 | 2525 | `fonts/martian_mono/font.css` | `0ab3b7d1d82c6601f5b626be47ce55066d94ae744ccbfa6425fd7b5ae30f7c2c` | 06,14 |
| alumni_sans | 5.3.0 | SIL OFL-1.1 | 4505 | `fonts/alumni_sans/LICENSE` | `0091179f4d5e0a5b41eaf840a57d3ef5a76240e62871deed754192db13860469` | 07 |
| alumni_sans | 5.3.0 | SIL OFL-1.1 | 11792 | `fonts/alumni_sans/alumni-sans-cyrillic-wght-normal.woff2` | `79758662da8f8d52bca682e7b4834f6f16bf47d8e339cd821d55a350bd851f9a` | 07 |
| alumni_sans | 5.3.0 | SIL OFL-1.1 | 18892 | `fonts/alumni_sans/alumni-sans-latin-ext-wght-normal.woff2` | `1d84fd8caed56f7acd48ea7af48b06c608421fcb15f18e64977b5ec3fba414ba` | 07 |
| alumni_sans | 5.3.0 | SIL OFL-1.1 | 22236 | `fonts/alumni_sans/alumni-sans-latin-wght-normal.woff2` | `49015c322cbd9ee7fbfbdb25295a57a5ba4b35e6f9c92c6d42fd570267e45c36` | 07 |
| alumni_sans | 5.3.0 | SIL OFL-1.1 | 12916 | `fonts/alumni_sans/alumni-sans-cyrillic-wght-italic.woff2` | `fa69c9760050453a8c839939424f90c25d9d54be8914058498a2234931f20fea` | 07 |
| alumni_sans | 5.3.0 | SIL OFL-1.1 | 19956 | `fonts/alumni_sans/alumni-sans-latin-ext-wght-italic.woff2` | `6dc212778d048f3083f79ca21420a1004a7f6dd27d5ae22484755cd08fcdb8c3` | 07 |
| alumni_sans | 5.3.0 | SIL OFL-1.1 | 23880 | `fonts/alumni_sans/alumni-sans-latin-wght-italic.woff2` | `5164f7384b20e45a949fc71a8540e58c176d509c3412589a44cf7285d6653ffc` | 07 |
| alumni_sans | 5.3.0 | SIL OFL-1.1 | 2417 | `fonts/alumni_sans/font.css` | `a57ed6d232786f838ebeb3fb29270870947bbb0b1e541a4a16a05bdf21944a87` | 07 |
| pt_mono | 5.3.0 | SIL OFL-1.1 | 4370 | `fonts/pt_mono/LICENSE` | `df14159157b0f6d728e2186a19ed31bec4fd30d1e8be87647b6e1e0a30cb265f` | 07,16 |
| pt_mono | 5.3.0 | SIL OFL-1.1 | 15356 | `fonts/pt_mono/pt-mono-cyrillic-400-normal.woff2` | `798d60261c091fa0735d73a9c10c819d27b27cbbcfdcdf6b8ba94e0d41a7d99f` | 07,16 |
| pt_mono | 5.3.0 | SIL OFL-1.1 | 16072 | `fonts/pt_mono/pt-mono-latin-ext-400-normal.woff2` | `b5e539036e0fedbb1bc408355993f36d264132b96008a5152f05b1f858d9120e` | 07,16 |
| pt_mono | 5.3.0 | SIL OFL-1.1 | 27436 | `fonts/pt_mono/pt-mono-latin-400-normal.woff2` | `b4e2aee32a6162b66a40f6fc7ac09962b0385e467ca8b143d92a091b16eaff6d` | 07,16 |
| pt_mono | 5.3.0 | SIL OFL-1.1 | 1115 | `fonts/pt_mono/font.css` | `f83906da52b3a335185e511a5445b8668c78a86c3b588ee7afb6e0f41bea0028` | 07,16 |
| wix_madefor_display | 5.3.0 | SIL OFL-1.1 | 4386 | `fonts/wix_madefor_display/LICENSE` | `d36354965f1cd37fecd85338773287a4969a6f065478d9a92244400d606c2bad` | 08,17 |
| wix_madefor_display | 5.3.0 | SIL OFL-1.1 | 13816 | `fonts/wix_madefor_display/wix-madefor-display-cyrillic-wght-normal.woff2` | `34c9d48261f9e10a150d240bc0c81c3dfb4838795e59d6b66e34eb78471605ed` | 08,17 |
| wix_madefor_display | 5.3.0 | SIL OFL-1.1 | 12464 | `fonts/wix_madefor_display/wix-madefor-display-latin-ext-wght-normal.woff2` | `910481ea54d71c83e72ccb179e116ee47063ce6a92022444e9dd1cd2d66dca03` | 08,17 |
| wix_madefor_display | 5.3.0 | SIL OFL-1.1 | 20168 | `fonts/wix_madefor_display/wix-madefor-display-latin-wght-normal.woff2` | `19bf2f2f1eaa10b2a047a8a1e624a1e12008ab5e3c50ad199ac968f8324f5f4d` | 08,17 |
| wix_madefor_display | 5.3.0 | SIL OFL-1.1 | 1304 | `fonts/wix_madefor_display/font.css` | `f18c01e7c6abffe5cbb718faa0474c471c814e88a1cd3b29e7c283582a04b499` | 08,17 |
| wix_madefor_text | 5.3.0 | SIL OFL-1.1 | 5644 | `fonts/wix_madefor_text/LICENSE` | `ed8d911198369bc4da998f5c12d6c5b6b5a6ceceb89d9c5064b18624622896ff` | 12 |
| wix_madefor_text | 5.3.0 | SIL OFL-1.1 | 14096 | `fonts/wix_madefor_text/wix-madefor-text-cyrillic-wght-normal.woff2` | `db1a17ef71f7ab174e889c18dd0afe070eb95731ded5d447a15063c9c2a60932` | 12 |
| wix_madefor_text | 5.3.0 | SIL OFL-1.1 | 12728 | `fonts/wix_madefor_text/wix-madefor-text-latin-ext-wght-normal.woff2` | `3b75cd0aa0856655b4623ab658a9725de2b774e5c98ae89ffa10f8fb2cc0aec9` | 12 |
| wix_madefor_text | 5.3.0 | SIL OFL-1.1 | 20244 | `fonts/wix_madefor_text/wix-madefor-text-latin-wght-normal.woff2` | `cbd90a79e04d153fd521d90b08e9962628e3139313af330bd898001fe5b36e1a` | 12 |
| wix_madefor_text | 5.3.0 | SIL OFL-1.1 | 916 | `fonts/wix_madefor_text/wix-madefor-text-cyrillic-wght-italic.woff2` | `587c8fe1dea05f1dccffdab5d3f40d41a34760c1ce2757c6c4003f53e190545a` | 12 |
| wix_madefor_text | 5.3.0 | SIL OFL-1.1 | 12016 | `fonts/wix_madefor_text/wix-madefor-text-latin-ext-wght-italic.woff2` | `0f18cc275b98ed88dc15aea792ffc5d5a29566e75a3ecebac50d1a6c2b3a107b` | 12 |
| wix_madefor_text | 5.3.0 | SIL OFL-1.1 | 21364 | `fonts/wix_madefor_text/wix-madefor-text-latin-wght-italic.woff2` | `9e24955c2990af1fdf1a4d0b0f828beafe6128ce408a70fc5cce3e78456be331` | 12 |
| wix_madefor_text | 5.3.0 | SIL OFL-1.1 | 2537 | `fonts/wix_madefor_text/font.css` | `1c6d6374a591df8e1e0aa71e03521b71cb260013e389aedd2a6007c50eae4ead` | 12 |
| onest | 5.3.1 | SIL OFL-1.1 | 4378 | `fonts/onest/LICENSE` | `a2a09da98a3d0d1ec79fc2d6deeac748b20a8153e26699552e7b59b5a40b63a3` | 08 |
| onest | 5.3.1 | SIL OFL-1.1 | 15860 | `fonts/onest/onest-cyrillic-wght-normal.woff2` | `68e5e01d6265bd68967746d4f5a9d18d0e6cbb5d15583c7082d6384ab1229b27` | 08 |
| onest | 5.3.1 | SIL OFL-1.1 | 28452 | `fonts/onest/onest-latin-ext-wght-normal.woff2` | `14e7d3079b75860e2ab50efc6c318c398fdb46ede9b56e625f12ae70a3c5d9a4` | 08 |
| onest | 5.3.1 | SIL OFL-1.1 | 33760 | `fonts/onest/onest-latin-wght-normal.woff2` | `052df74533250c2e0ca0c4bdd32de594e107d99c1648e63820ef9c6142067828` | 08 |
| onest | 5.3.1 | SIL OFL-1.1 | 1136 | `fonts/onest/font.css` | `63812ba0a0dacb40593f466f8176de83d91465f140084df6601b5abdd7a8520b` | 08 |
| geologica | 5.3.0 | SIL OFL-1.1 | 4390 | `fonts/geologica/LICENSE` | `1ed2ffe9ee7048846f4bc5b28bf655113fd7d53e7717bf251dd68130af73016c` | 09,14,15 |
| geologica | 5.3.0 | SIL OFL-1.1 | 16428 | `fonts/geologica/geologica-cyrillic-wght-normal.woff2` | `a7dc739efa0c2d4066164b40b15276440978d8efb6003b5f10a6b9c3e5c1cd30` | 09,14,15 |
| geologica | 5.3.0 | SIL OFL-1.1 | 22404 | `fonts/geologica/geologica-latin-ext-wght-normal.woff2` | `85ea5e8563c66d7fc38c97e7fabf398643c719e76ce058704b3690317d6d0993` | 09,14,15 |
| geologica | 5.3.0 | SIL OFL-1.1 | 24944 | `fonts/geologica/geologica-latin-wght-normal.woff2` | `b14f1edee95a57f8782d505232e54584c80c673acbd25a0e7c6366332977b47d` | 09,14,15 |
| geologica | 5.3.0 | SIL OFL-1.1 | 1184 | `fonts/geologica/font.css` | `a84a975ec940d3c3fe04d94c94245d3e5705278c27e3ef5c669a5febfdae6266` | 09,14,15 |
| fira_code | 5.3.0 | SIL OFL-1.1 | 4389 | `fonts/fira_code/LICENSE` | `126cd7bf732b86f42885f1fbf682e6aeea456672c7fdb99f2d557ec44e468a28` | 09,10,19 |
| fira_code | 5.3.0 | SIL OFL-1.1 | 11980 | `fonts/fira_code/fira-code-cyrillic-wght-normal.woff2` | `b0ea81e7827ccb1e8258b911e632b694e898fe15665fab3ed0d12bc565288a34` | 09,10,19 |
| fira_code | 5.3.0 | SIL OFL-1.1 | 13272 | `fonts/fira_code/fira-code-latin-ext-wght-normal.woff2` | `801677342d1191c5e964719bbcb5834f5da3c39a00e1e1501f450b1379fcc116` | 09,10,19 |
| fira_code | 5.3.0 | SIL OFL-1.1 | 36276 | `fonts/fira_code/fira-code-latin-wght-normal.woff2` | `771bf4b79a97fc005d12866168bd39d868a9dd3d5903008fe8b796723c8a56f4` | 09,10,19 |
| fira_code | 5.3.0 | SIL OFL-1.1 | 1184 | `fonts/fira_code/font.css` | `6393b88ae0e003ff30d3051a828bef8015594e174ce39fbe6477933dd8ceed26` | 09,10,19 |
| jura | 5.3.0 | SIL OFL-1.1 | 4378 | `fonts/jura/LICENSE` | `0d5db8c052b693936cbc18c1411060c34cc4d8209b98fb13baca93e267778651` | 10 |
| jura | 5.3.0 | SIL OFL-1.1 | 13212 | `fonts/jura/jura-cyrillic-wght-normal.woff2` | `288dbc9f897b39e56a62d1d4b4c0a24919659cb92fbe410f4032901a887c9f9f` | 10 |
| jura | 5.3.0 | SIL OFL-1.1 | 24472 | `fonts/jura/jura-latin-ext-wght-normal.woff2` | `8364bcb0173c1f3f4981c1a40766112ed8ee59c1ebd2c3d62638557f59b63527` | 10 |
| jura | 5.3.0 | SIL OFL-1.1 | 24276 | `fonts/jura/jura-latin-wght-normal.woff2` | `99a4b2d414e1d6ee78a883c7513d5dd9da4254f2a094c76170b81f07b1620d79` | 10 |
| jura | 5.3.0 | SIL OFL-1.1 | 1124 | `fonts/jura/font.css` | `505e054928536fa5574bb66957b101d7da3f1b11f00fa32b19bf295b3565f755` | 10 |
| rubik | 5.3.0 | SIL OFL-1.1 | 4486 | `fonts/rubik/LICENSE` | `46a250495a963b0b84f2736c0185d0e3af8df9d23427bd425b92a8ece020283c` | 11,20 |
| rubik | 5.3.0 | SIL OFL-1.1 | 15112 | `fonts/rubik/rubik-cyrillic-wght-normal.woff2` | `bdb2b33ab916e9e7b42edb61f8aea5f5dd83ad773d6ee4e9b55665daf8954ce8` | 11,20 |
| rubik | 5.3.0 | SIL OFL-1.1 | 19400 | `fonts/rubik/rubik-latin-ext-wght-normal.woff2` | `09472f217ad1ebb61a7669cf532f9f2f80685e07652ee862fde9a79665aef479` | 11,20 |
| rubik | 5.3.0 | SIL OFL-1.1 | 35348 | `fonts/rubik/rubik-latin-wght-normal.woff2` | `691cd1d9b4c0cdf31a1dcf04259c86f92c85e69f6622abab7964d81e36890691` | 11,20 |
| rubik | 5.3.0 | SIL OFL-1.1 | 16488 | `fonts/rubik/rubik-cyrillic-wght-italic.woff2` | `e9f7ede725761fea79102f5256a581eb4693dbaff21e61db15974eec2dfb226a` | 11,20 |
| rubik | 5.3.0 | SIL OFL-1.1 | 21152 | `fonts/rubik/rubik-latin-ext-wght-italic.woff2` | `51999fc7e45d93d8d34d3c0f1c32e58f85ae6e69d8dfb700771062e5c3945e49` | 11,20 |
| rubik | 5.3.0 | SIL OFL-1.1 | 36616 | `fonts/rubik/rubik-latin-wght-italic.woff2` | `4d9f552c4b0a7f02f231e56198d80aed8550bdfb7e7541260b2b20455b14fb88` | 11,20 |
| rubik | 5.3.0 | SIL OFL-1.1 | 2273 | `fonts/rubik/font.css` | `abdf726cc2fc54b67a2ad744dbf14df8fc97f276f3e8c7d00faa9ba5b2aaf3ef` | 11,20 |
| nunito | 5.3.0 | SIL OFL-1.1 | 4491 | `fonts/nunito/LICENSE` | `40991bfa02ac620aae16dc527f3c47765a25e43f270d4c301ee6ab663a8d9015` | 11,20 |
| nunito | 5.3.0 | SIL OFL-1.1 | 20776 | `fonts/nunito/nunito-cyrillic-wght-normal.woff2` | `63b14e3ef0966785438b8947380dfbcad178cbd3c6a5ed2172672ca0d8b839ac` | 11,20 |
| nunito | 5.3.0 | SIL OFL-1.1 | 35588 | `fonts/nunito/nunito-latin-ext-wght-normal.woff2` | `2c8d792869818ecb253a46bc3c63c7013df7aac2f69291c3c85e5cdc94160960` | 11,20 |
| nunito | 5.3.0 | SIL OFL-1.1 | 39128 | `fonts/nunito/nunito-latin-wght-normal.woff2` | `ba344451eab25b217a165363b1982048a5e5830a0daf36577973955a04cac793` | 11,20 |
| nunito | 5.3.0 | SIL OFL-1.1 | 22896 | `fonts/nunito/nunito-cyrillic-wght-italic.woff2` | `2c394b5d3bc6aa00dd6917458909e85191dcd675026459fdddde520bf5ee3bf7` | 11,20 |
| nunito | 5.3.0 | SIL OFL-1.1 | 39072 | `fonts/nunito/nunito-latin-ext-wght-italic.woff2` | `1bb48a49c837d76a727223515b78eb2a14eaab783563be84b0718f338c56c846` | 11,20 |
| nunito | 5.3.0 | SIL OFL-1.1 | 41760 | `fonts/nunito/nunito-latin-wght-italic.woff2` | `6cfcc3786d5ba3b5c3a41797f95272e57f4290ccbd283a4bfd0033a3d857e64c` | 11,20 |
| nunito | 5.3.0 | SIL OFL-1.1 | 2303 | `fonts/nunito/font.css` | `d4594700cc0d64ea2f1fef90e5aa2fd230a0ed7a64520628e998c22587087cd9` | 11,20 |
| cormorant_garamond | 5.3.0 | SIL OFL-1.1 | 4504 | `fonts/cormorant_garamond/LICENSE` | `732f37009943e7f4378cf37113c9bcc4716af002a8583511aa91ed5d37683e73` | 12 |
| cormorant_garamond | 5.3.0 | SIL OFL-1.1 | 21168 | `fonts/cormorant_garamond/cormorant-garamond-cyrillic-wght-normal.woff2` | `017fab69b4be8ffc08ca312823327989ade6dc3d948f0afa125e12ec2e5e7ca1` | 12 |
| cormorant_garamond | 5.3.0 | SIL OFL-1.1 | 33736 | `fonts/cormorant_garamond/cormorant-garamond-latin-ext-wght-normal.woff2` | `cfa9a397d86f66c5c51775a2500a712d5f632a04f0c5eca6930dfaf612d4566d` | 12 |
| cormorant_garamond | 5.3.0 | SIL OFL-1.1 | 37640 | `fonts/cormorant_garamond/cormorant-garamond-latin-wght-normal.woff2` | `d80df8ff5aecd299a61549f9e29ab1ed0b9b05f4ea71d50fe978e07d5240b235` | 12 |
| cormorant_garamond | 5.3.0 | SIL OFL-1.1 | 21300 | `fonts/cormorant_garamond/cormorant-garamond-cyrillic-wght-italic.woff2` | `cb13c04533ee98c94e49a053b9f4d39bf616fd7ba6360d71aead92a78dc571f7` | 12 |
| cormorant_garamond | 5.3.0 | SIL OFL-1.1 | 34392 | `fonts/cormorant_garamond/cormorant-garamond-latin-ext-wght-italic.woff2` | `cd5bf126b2c84ab41b254a6a9a1ffb5c326a0f9f82c22fb4704daa31c9aaa415` | 12 |
| cormorant_garamond | 5.3.0 | SIL OFL-1.1 | 39260 | `fonts/cormorant_garamond/cormorant-garamond-latin-wght-italic.woff2` | `6f2f5c3b1abc3d0bb035a927f66a90ca873f94fc31c4966c8d024142c2036e55` | 12 |
| cormorant_garamond | 5.3.0 | SIL OFL-1.1 | 2585 | `fonts/cormorant_garamond/font.css` | `fef81c2737c0d2296ffe52c732b21cdeb10d223cea7c5de02912615ccb3459aa` | 12 |
| literata | 5.3.0 | SIL OFL-1.1 | 4506 | `fonts/literata/LICENSE` | `9895ebc015226accf416b758ac1ca02a2fb4f83a89d316791ef697c3dc0852aa` | 13 |
| literata | 5.3.0 | SIL OFL-1.1 | 28068 | `fonts/literata/literata-cyrillic-wght-normal.woff2` | `df20f1a8ca3c15497861c6dbf36c0c59507ee351301527ec89543747067ad4d7` | 13 |
| literata | 5.3.0 | SIL OFL-1.1 | 42656 | `fonts/literata/literata-latin-ext-wght-normal.woff2` | `46792f7cd10b28fb512161caeaaa11b049feb2221ccaa72bb4d4ccc286199155` | 13 |
| literata | 5.3.0 | SIL OFL-1.1 | 52496 | `fonts/literata/literata-latin-wght-normal.woff2` | `9adbeac5b167fe5ad6c49d9e29aa0c76e2f1bb3b46bf4ebf12a9eca7d3525384` | 13 |
| literata | 5.3.0 | SIL OFL-1.1 | 29264 | `fonts/literata/literata-cyrillic-wght-italic.woff2` | `62e8c9a48487878d0027e5946773f029f28ec6be99f1f20eb26b6aa401395c29` | 13 |
| literata | 5.3.0 | SIL OFL-1.1 | 43256 | `fonts/literata/literata-latin-ext-wght-italic.woff2` | `ba0e6a12e2f0a1f5d455c23c47068b71f9898c571dcb92dab385294ebdae3e74` | 13 |
| literata | 5.3.0 | SIL OFL-1.1 | 53728 | `fonts/literata/literata-latin-wght-italic.woff2` | `ab198d6616c7cc966f26a4a5b28a3977dc47439640f09d9b3361226bd465c404` | 13 |
| literata | 5.3.0 | SIL OFL-1.1 | 2345 | `fonts/literata/font.css` | `bed9232fcbb8eb334461a411c61ea2a74e3122b5be91355e91b2dd80a025aece` | 13 |
| mulish | 5.3.0 | SIL OFL-1.1 | 4491 | `fonts/mulish/LICENSE` | `e8c2c25954b4ff44e44ad6b2d900d0b3936a593a4579e8d65b2788aac7ebf8ca` | 15 |
| mulish | 5.3.0 | SIL OFL-1.1 | 15948 | `fonts/mulish/mulish-cyrillic-wght-normal.woff2` | `270a9552cb39c2aa23054f70bf8c770bc1a9c2d6e0df2841bad89f6597bcd483` | 15 |
| mulish | 5.3.0 | SIL OFL-1.1 | 26820 | `fonts/mulish/mulish-latin-ext-wght-normal.woff2` | `e1ccc8579a0437969464ba8bb1bb5e423306fa16746521d1f05040243b9a7a58` | 15 |
| mulish | 5.3.0 | SIL OFL-1.1 | 29968 | `fonts/mulish/mulish-latin-wght-normal.woff2` | `8d1d33d6beea5a722b8f336d79c61c07405949457e37b5e65454c72dc10aba1a` | 15 |
| mulish | 5.3.0 | SIL OFL-1.1 | 16896 | `fonts/mulish/mulish-cyrillic-wght-italic.woff2` | `c960e23b0bacf5debcde95e42e1774105d2dafc05dd3ac8ca5f8d7e7ce69a99f` | 15 |
| mulish | 5.3.0 | SIL OFL-1.1 | 29612 | `fonts/mulish/mulish-latin-ext-wght-italic.woff2` | `081c49fccb3da90bee5f39c9b97cc40c8d52e13291c0c78d573a6def6a8f5402` | 15 |
| mulish | 5.3.0 | SIL OFL-1.1 | 32264 | `fonts/mulish/mulish-latin-wght-italic.woff2` | `7380fb751bd9cbd89824588ddeb25a83395eb850e16eb24936c24c7de2ff4d2e` | 15 |
| mulish | 5.3.0 | SIL OFL-1.1 | 2303 | `fonts/mulish/font.css` | `22737905158b9c39510b2b5d3cb63b79b7db75c386fa51a00a5c87154a528795` | 15 |
| vollkorn | 5.3.0 | SIL OFL-1.1 | 4517 | `fonts/vollkorn/LICENSE` | `811216cf167432058346171e124416e3d4aa6ab8b2b87d5a0b949ee8dfa40731` | 16 |
| vollkorn | 5.3.0 | SIL OFL-1.1 | 28016 | `fonts/vollkorn/vollkorn-cyrillic-wght-normal.woff2` | `0a30dfec06879aabe5edaa29e9feb425557f108eb234eb8937da48f23067643d` | 16 |
| vollkorn | 5.3.0 | SIL OFL-1.1 | 37620 | `fonts/vollkorn/vollkorn-latin-ext-wght-normal.woff2` | `fd562f72811cac53a5bf14f86732e952a3f5cfd3c61896b7b809e164978fd7dd` | 16 |
| vollkorn | 5.3.0 | SIL OFL-1.1 | 46356 | `fonts/vollkorn/vollkorn-latin-wght-normal.woff2` | `3d9ff812bd542e52bb7f0c204f3a21152e22aead4572ff09722c1b38f30d7567` | 16 |
| vollkorn | 5.3.0 | SIL OFL-1.1 | 27204 | `fonts/vollkorn/vollkorn-cyrillic-wght-italic.woff2` | `7a764339aeea7b10f8def07604771923722ee2d7a70be08ecdce3b52780c8add` | 16 |
| vollkorn | 5.3.0 | SIL OFL-1.1 | 41256 | `fonts/vollkorn/vollkorn-latin-ext-wght-italic.woff2` | `5aff1d5511c936c03f1dbd2db0400e0d075b99a4417dcc2c5b11ca6fe8009325` | 16 |
| vollkorn | 5.3.0 | SIL OFL-1.1 | 47528 | `fonts/vollkorn/vollkorn-latin-wght-italic.woff2` | `2b21f0fe01d929e246f513850bb1e2658eb77d9ab80c68a53a460725d66a5059` | 16 |
| vollkorn | 5.3.0 | SIL OFL-1.1 | 2345 | `fonts/vollkorn/font.css` | `9d2e3a5a7d225809ed6b0f232706cd81fc801a1527d5ade84aa46ef938c46560` | 16 |
| shantell_sans | 5.3.0 | SIL OFL-1.1 | 4536 | `fonts/shantell_sans/LICENSE` | `cde8ad5bfbaa0f4b916daff2b107d45dd7a84706c627fd3f669f6cc2af563843` | 16,20 |
| shantell_sans | 5.3.0 | SIL OFL-1.1 | 58676 | `fonts/shantell_sans/shantell-sans-cyrillic-wght-normal.woff2` | `8d4fcae6f8af2fc468dc359089387d4e1096a398217f7b91aa6127e8a2f40794` | 16,20 |
| shantell_sans | 5.3.0 | SIL OFL-1.1 | 37192 | `fonts/shantell_sans/shantell-sans-latin-ext-wght-normal.woff2` | `3b0ecff7fe287e170571e7cdce06da4099bed00e3fba7209a3840a280ffa79e4` | 16,20 |
| shantell_sans | 5.3.0 | SIL OFL-1.1 | 79292 | `fonts/shantell_sans/shantell-sans-latin-wght-normal.woff2` | `f15631aba9746668ad895821c72db5825759fe0bddaa4da1e7ea33d0dc2d5477` | 16,20 |
| shantell_sans | 5.3.0 | SIL OFL-1.1 | 60160 | `fonts/shantell_sans/shantell-sans-cyrillic-wght-italic.woff2` | `21b7bfe26f0a881b84b242da03d084e1bd49876087a43a2e94a2906e8c57cd41` | 16,20 |
| shantell_sans | 5.3.0 | SIL OFL-1.1 | 39904 | `fonts/shantell_sans/shantell-sans-latin-ext-wght-italic.woff2` | `f9337ece6e7944c7c9fb7b7ef03b7f655e651739a70175937b0c2e995b4ef2cb` | 16,20 |
| shantell_sans | 5.3.0 | SIL OFL-1.1 | 82000 | `fonts/shantell_sans/shantell-sans-latin-wght-italic.woff2` | `0fcdc355c37aff725b1cd969ae83691e02927a371cc94a28f2f16b62d1f722c9` | 16,20 |
| shantell_sans | 5.3.0 | SIL OFL-1.1 | 2465 | `fonts/shantell_sans/font.css` | `bee5c971f4ec788deb14647f6d6796e3bdb09e0f70bed222e52c132b7a974f6b` | 16,20 |
| motion | 14.14.0 | MIT | 1100 | `js/motion/LICENSE.md` | `1bf0dc3f7727723e5a032ed12164a47cf92c05204cb1a3485f123c24e2833ed1` | 01,05,06,07,08,09,10,11,13,14,20 |
| motion | 14.14.0 | MIT | 191561 | `js/motion/motion.js` | `521cfef8910fdd997463ea9881d4b790e017331e3d2f79c02adfc4d5fe1f2cae` | 01,05,06,07,08,09,10,11,13,14,20 |
| animejs | 4.5.0 | MIT | 1075 | `js/animejs/LICENSE.md` | `3f3e835a9952cfc2a6ca836fb95b3257c981f24fa3ef51249055acb09931897b` | 05,06,07,11,20 |
| animejs | 4.5.0 | MIT | 118678 | `js/animejs/anime.esm.min.js` | `a19015a1a92d52025a2fb6703b6d67eadd1cc2aeaf880770e96e04cf6aa07be1` | 05,06,07,11,20 |
| animejs | 4.5.0 | MIT | 118043 | `js/animejs/anime.umd.min.js` | `8d5b3a58a1f64023a04a4cedeef135a2263b18da04b35177ac13438a0bad033b` | 05,06,07,11,20 |
| lenis | 1.3.27 | MIT | 1088 | `js/lenis/LICENSE` | `7d1896b31f2eed9f286b05faca067c4e35b2f109ae7c4ed5105220e2d2820228` | 01,05,06,07,08,09,10,11,12,13,14,16,20 |
| lenis | 1.3.27 | MIT | 33274 | `js/lenis/lenis.mjs` | `4cdb25138c7233e7419f630d9536adb41d71fa51906c059f0a27a1268ddedacc` | 01,05,06,07,08,09,10,11,12,13,14,16,20 |
| lenis | 1.3.27 | MIT | 18815 | `js/lenis/lenis.min.js` | `80f53e77f1c13e379fc246d2b5e299188e20bcb2b2fe7ebb13e8e8c7563a6da7` | 01,05,06,07,08,09,10,11,12,13,14,16,20 |
| three | 0.187.0 | MIT | 1081 | `js/three/LICENSE` | `8b378ebe60e2fe500158cb0ac71cb5e8b7d92953c2abcc63a0eb90499653b5bc` | 14 |
| three | 0.187.0 | MIT | 658900 | `js/three/three.module.js` | `104f56145899722094556490d787aae0617cc2fc3382f31df02d724ea1aee341` | 14 |
| three | 0.187.0 | MIT | 1474799 | `js/three/three.core.js` | `613e370f76638fdef83926642bf256dc9615684922de1ce1f63a8583e5d78578` | 14 |
| three addons | 0.187.0 | MIT | 119861 | `js/three/addons/loaders/GLTFLoader.js` | `532ac726e120039acbcd6cf54328c57acbf7b438176afaa6951257126d11bff1` | 14 |
| three addons | 0.187.0 | MIT | 39153 | `js/three/addons/utils/BufferGeometryUtils.js` | `7bda2a8ba836b2bcf67cb938d4b9e1bb5d1b1bc616817103ed858c0b58296ce7` | 14 |
| three addons | 0.187.0 | MIT | 11535 | `js/three/addons/utils/SkeletonUtils.js` | `b1632a703206c3d830de9fcbe515696770d04b71a15ee6b50afa6d2c3298c86f` | 14 |
| three addons | 0.187.0 | MIT | 40918 | `js/three/addons/controls/OrbitControls.js` | `e7fca2fe9e7670a828af9b28084669a5909445b7f36f1f26cee9bf8f2961c32c` | 14 |

## npm offline cache (vendor/npm_offline/) — added 2026-11-23

Offline install for the non-HTML stacks the Studio scaffolds. Platform-specific optional binaries were fetched for **win32-x64 only** (other OS need one online install). Usage: copy `vendor/npm_offline/<stack>/package*.json` into the project, then `npm ci --offline --cache <repo>/vendor/npm_offline/_cacache --ignore-scripts`. Verified offline on 2026-11-23 for all 4 stacks.

| stack | top-level packages | installed pkgs | package-lock.json sha256 |
|---|---|---|---|
| astro | astro 7.4.13, zod ^4.6.7 | 194 | 02fc92c90e3018ce9152e1687f08d7ecc4eaf6c2d05d62d246d008c7eb7cea22 |
| sveltekit | @sveltejs/kit ^3.4.0, svelte ^5.59.1, zod, @sveltejs/adapter-node ^6.0.5, vite ^8.3.8 | 49 | d83ed90d1ab46c79500759c5052eebb409562585e127db8ecf1ecf145db1114a |
| nextjs | next ^16.4.6, react/react-dom ^19.3.1, server-only, zod | 25 | bbf6aa83ab2f92ca7a2c394670d44ce8be3ae2f933ba6c4c33c40243ab2eeec2 |
| vite_ts | vite ^8.3.8, typescript ^7.0.2 | 17 | 76b46cd091634fcc02571ac29985fbc67c1b5bfafaa2d88ebde6bb7cc8ac55a0 |

- Cache size ~504 MB (content-addressed, no duplicate versions; every tarball verified by the sha512 `integrity` in the lock files). Per-package licenses: `vendor/npm_offline/licenses_inventory.json` (350 package@version rows).
- Licence mix: MIT 258, Apache-2.0 40, LGPL-3.0-or-later 14 (sharp/libvips binaries), MPL-2.0 12 (lightningcss), ISC 8, BSD 11, BlueOak 3, CC0 2, 0BSD 1, CC-BY-4.0 1 (caniuse-lite). All allow redistribution.
- Full LICENSE/NOTICE files for Apache/LGPL/MPL/CC-BY packages present on this platform: `vendor/npm_offline/licenses/<pkg>_<ver>/`. Obligations: `vendor/npm_offline/NOTICE.md`.
- Scaffold fix found while vendoring: `@sveltejs/adapter-node ^5` has peer `@sveltejs/kit ^2` → scaffold now pins `^6.0.5` (templates_engine.py).
- GSAP: not vendored (licence forbids redistribution in a site builder).
