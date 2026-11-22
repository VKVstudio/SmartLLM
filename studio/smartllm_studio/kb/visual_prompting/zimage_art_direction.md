# Z-Image-Turbo Visual Art Direction & 7-Slot Prompting Canon

## 1. Verified `Tongyi-MAI/Z-Image-Turbo` Architecture & `sd-cli` Traps
- **Model (`arXiv:2511.22699`):** 6.15B **S3-DiT** (~10.26B total w/ frozen **Qwen3-4B** + FLUX 16-ch 8× VAE): **30 joint single-stream blocks + 2 image `noise_refiner` + 2 text `context_refiner` (34 transformer blocks total)**.
- **Verified `sd-cli` Flags:** `--type q8_0 --clip-on-cpu --vae-tiling --sampling-method euler --flow-shift 3.0 --steps 8 --cfg-scale 1.0`.
- **CRITICAL CFG TRAP (`request.cpp:319-334`):** At `--cfg-scale 1.0`, `sd-cli` skips the negative branch (`-n` is a no-op). **NEVER use `sd-cli --cfg-scale 0.0`** (Diffusers uses `guidance_scale=0.0`, whereas in `sd-cli`, `0.0` disables prompt conditioning too!).
- **Strict Positive-Only Framing:** Qwen3-4B tokens attend directly inside S3-DiT. Negative clauses (*"no text"*, *"zero text"*, *"zero beige"*, *"no outline"*) draw attention to *text / beige / outline* and spawn them! State blank surfaces positively (`"blank matte aluminum bezel"`, `"unmarked travertine"`, `"crisp neutral platinum tones"`).
- **English-Only, Text-Free Output:** Z-Image typography covers EN+ZH only; Cyrillic renders garbled glyphs. Keep visuals 100% text-free and render all EN/RU typography in HTML/CSS/SVG.
- **Length & Grid:** Write 2–3 cohesive prose sentences (**45–95 words**, hard cap `110` words; 0 CLIP tag-soup). Dimensions are `64`-multiples (`1024×576` `16:9`, `896×672` `4:3`, `768×768` `1:1`, `640×800` `4:5`, `576×768` `3:4` team, `512×512` logo).

## 2. Full-Context 7-Slot Assembly Formula
`POST_SANITIZE([1: COPY_SEMANTICS] + [4: LAYOUT_&_NEGATIVE_SPACE] + [2: CANON_DIRECTION] + [3: POLARITY_LIGHTING] + [5: OPTICS] + [6: PALETTE_HARMONY])`

### Slot 1 — Upstream Copy Extraction & Physical Scene Translation
Read finalized slot copy (NEVER just `brief[:240]`): `hero_{slug}` (`hero.headline`, `hero.subhead`, `copy.features`, `architecture.angle`), `gallery_1` (`24–35mm` wide establishing) vs `gallery_2` (`85–100mm` macro material detail), `team_{i}` (`gender` + `role` + unique persona, NEVER name). Ban glowing brains, handshakes, floating holograms, and matrix code:
| Domain | Hero / Wide Establishing (`24–35mm`) | Macro Craft Detail (`gallery_2`, `85–100mm`) |
|---|---|---|
| **Cybersecurity** | Air-gapped server corridor, matte black racks, braided fiber, steel vault door | CNC anodized titanium security key beside shielded fiber connectors |
| **Logistics** | Cross-dock fulfillment hub at dusk, matte containers, steel rollers, bay lamps | Knurled steel cargo ratchet tensioner, nylon strapping, waxed kraft seams |
| **Legal Advisory** | Quiet architectural library, smoked oak shelves, travertine table, blank volumes | Deckle-edge archival cotton paper, solid brass weight, pen nib on walnut |
| **B2B SaaS** | Minimalist glass-concrete desk, blank matte aluminum laptop, machined dial | Optical glass prisms refracting clean light bands across brushed aluminum |
| **Dental / Med** | Daylight treatment suite, ergonomic ivory chair, matte ceramic cabinets, oak | Translucent porcelain veneer models beside steel mirror on frosted glass |
| **Specialty Coffee** | Sunlit roastery bar, steel espresso machine, ceramic dripper, pale oak counter | Freshly roasted whole beans beside smooth crema pouring into ceramic cup |
| **Industrial CNC** | 5-axis CNC workshop floor, stainless enclosure, vise holding milled aluminum | Concentric milled toolpaths, steel swarf curls, stainless micrometer caliper |
| **Fintech** | Monolithic banking hall in honed basalt stone, walnut louvers, recessed linear light | Stacked blank titanium cards, dark calfskin cover, brushed bronze trim |
| **Architecture** | Concrete & Douglas-fir pavilion at oblique sun, crisp cantilevers, courtyard | Basswood scale model, honed travertine sample, black steel drafting scale |
| **Local AI Compute** | Liquid-cooled bench, graphite workstation chassis, copper heatpipes via smoked glass | Anodized aluminum heatsink fins, iridescent matte silicon wafer, fasteners |
| **Biotech / Lab** | Cleanroom bench, borosilicate glassware, matte ceramic micro-centrifuge | Clear borosilicate pipettes beside frosted quartz laboratory cuvettes |
| **EdTech** | Bright Nordic birch workshop table, open blank linen sketchbooks, wooden solids | Beechwood modular geometry blocks, matte aluminum ruler, cotton pages |

### Slots 2–7 — Direction, Polarity, Composition, Optics & Sanitization
- **Slot 2–3 (Direction & Polarity):** Pull `zimage_direction` from `styles/canons/{canon_id}.json`; anchor lighting from resolved `palette.bg` `L` (`Dark L < 0.25`: low-key 6:1 studio light, shadowed margins melting into dark UI, accent rim light; `Light L > 0.85`: high-key diffused northern daylight, pale stone/paper, clean contact shadows).
- **Slot 4 (Negative Space):** `fullbleed_scrim` anchors subject in **right 40%**, keeping **left 55%** calm low-detail negative space matching `bg` tone; `team_portrait` frames `3:4` chest-up with **20% empty headroom above hair** (`object-position: 50% 15%`); `brand_logo` renders 1 flat geometric symbol (`60%` fill, 2–3 flat pigments, legible at `32px`, text-free).
- **Slot 5–6 (Optics & Palette):** Only append `style_suffix` lens/light if prompt lacks `\b(?:\d{2,3}mm|lens|daylight|softbox|rim\s+light|golden\s+hour)\b`. Translate OKLCH into natural material pigments via `slot_prompt_recipes.json` (**NEVER raw `#HEX`/`oklch()`**).
- **Slot 7 (Sanitizer):** Run `harden_zimage_prompt()` (`VISUAL_PROTECT_WORDS` preserves `"stone"`, `"oak"`, `"white"`, `"brown"`, `"negative space"`, `"tactile buttons"`; rewrites `"sign"`/`"interface cards"` positively; strips `#HEX`, Cyrillic, member/distinctive brand tokens; clamps `<= 95` words).
