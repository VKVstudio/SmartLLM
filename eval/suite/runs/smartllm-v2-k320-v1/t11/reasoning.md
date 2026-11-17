Let me think through this carefully before emitting files.

The request: a single-page engineering portal for KRONOS PRECISION GEARWORKS, strain-wave/harmonic drives and planetary actuators. Design canon: dark anodized slate (oklch 0.15 0.015 250), CAD grid lines (oklch 0.24 0.02 250), titanium white (0.95 0.01 250), signal orange/amber (0.70 0.18 50). Monospace stack for technical data. No external requests.

Sections to build:
1. Hero + interactive canvas kinematics visualizer with sliders (reduction ratio 50–160, input RPM 500–6000, load torque Nm), computing live output RPM, torsional stiffness, efficiency.
2. SVG cutaway (flexspline, circular spline, wave generator) + torque-speed envelope chart (SVG).
3. Spec table for 3 series (KRG-14, KRG-25, KRG-40) with backlash < 0.5 arcmin, peak torque, hollow shaft bore, mass.
4. Quality/life testing compliance.
5. FAQ (5 Q&A) + CAD STEP download / consultation form with client-side validation.
6. Footer.

Constraints: strict CSP with placeholders, no inline handlers, addEventListener only, no element.style mutation, explicit dimensions on canvas/svg, prefers-reduced-motion, JSON-LD graph with Organization, Product x3, FAQPage verbatim, BreadcrumbList. llms.txt, robots.txt, _headers with 7 headers.

Let me design the canvas visualizer. Planetary gear mesh: render a sun gear + planet gears + ring gear, plus a strain-wave representation. Actually the request says "planetary/strain-wave gear mesh" — I'll do a hybrid: draw a wave generator ellipse, flexspline, circular spline teeth, and animate the wave generator rotation at input RPM, the circular spline at output... hmm. Strain-wave mechanics: wave generator rotates at input speed; flexspline deforms; circular spline rotates opposite direction at output... actually in a harmonic drive, the wave generator rotates at input speed, and the output (flexspline attached to output flange) rotates at output speed = input / ratio. The circular spline is stationary (fixed) in many configurations. Let me keep it simple: animate the wave generator ellipse rotating at input RPM scale, the flexspline teeth engaging, and the output flange rotating at output RPM. Plus a planetary mode toggle? Maybe a "MODE" toggle between strain-wave and planetary kinematics. That adds interactivity. Keep it manageable.

Canvas rendering: draw gear teeth procedurally with polar coordinates, teeth count based on ratio. Compute output RPM = input / ratio. Efficiency ~85-93%. Torsional stiffness Nm/arcmin. Sliders update readouts.

I need to keep the code concise so nothing truncates. This is a big build. Let me be disciplined: compact CSS, compact JS.

CSP: meta tag with placeholders sha256-__CSP_STYLE__ and sha256-__CSP_SCRIPT__. Directives: default-src 'self'; script-src 'sha256-__CSP_SCRIPT__'; style-src 'sha256-__CSP_STYLE__'; img-src 'self' data:; font-src 'self'; connect-src 'none'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'. Note: the JSON-LD script — is it subject to script-src? JSON-LD is not executed; but the build postprocessor hashes all scripts. The instructions say to place JSON-LD in head. The postprocessor will hash it. I don't know how it handles ld+json — probably treats it as a script block. To be safe, the JSON-LD script tag will also get hashed by the postprocessor; I should not include it in script-src... hmm, actually the postprocessor probably handles all <script> blocks. The rule says to use placeholders for script-src. I'll write script-src with __CSP_SCRIPT__ placeholder. The postprocessor will compute hashes for each script block and replace placeholders. Fine.

No external fonts: use system font stack: JetBrains Mono, IBM Plex Mono fallbacks. No <link> to fonts. OK.

Design tokens in :root with OKLCH.

Let me plan the HTML structure:

- header: nav with logo KRONOS, links to sections, CTA.
- hero: h1, copy, canvas visualizer panel with sliders + readouts, mode toggle buttons.
- section: cross-section SVG cutaway + torque-speed envelope SVG.
- section: spec table (3 series) inside .table-wrap.
- section: quality compliance cards + life testing.
- section: FAQ (5 items) + form.
- footer.

SVG cutaway: concentric rings: circular spline (outer ring with teeth), flexspline (thin-walled cup), wave generator (elliptical cam with bearing). Animate? Could animate the wave generator ellipse rotation via SMIL? SMIL is inline in HTML... is that allowed? SMIL doesn't violate CSP (no script). But prefers-reduced-motion... SMIL can't easily respect reduced motion. Better: animate via JS class toggles? But no style mutation. I can animate SVG geometry attributes (d, points, x2) with JS — allowed per rule 3. So animate the wave generator ellipse in the cutaway SVG by updating the transform via setAttribute (transform attribute is not style). Hmm, transform attribute vs style — setAttribute('transform', ...) is allowed? The rule says don't touch element.style.*, setAttribute('style'), setProperty. It says to toggle CSS classes, hidden, or SVG geometry attributes (d, points, x2). transform is an SVG attribute, not style — should be fine. I'll use transform attribute updates for the cutaway animation.

Torque-speed envelope chart: SVG with axes, a polyline envelope, zones (continuous, peak, burst). Static SVG, maybe hover tooltips via JS? Keep simple: static SVG with labels, plus interactive readout tied to sliders? I can tie the envelope chart to the slider values: as load torque changes, highlight the operating point on the chart. That's a nice touch: a marker circle whose cx/cy updates via setAttribute. Good.

Canvas visualizer JS: procedural rendering. Let me design the renderer:

- DPR-aware canvas sizing with explicit width/height attributes (e.g., width="640" height="420" with CSS max-width 100%). CLS 0: explicit dimensions.
- Draw function: polar coordinate gear teeth.
- Strain-wave mode: circular spline ring (static, teeth), flexspline ring (thin, rotating at output speed, with teeth), wave generator ellipse rotating at input speed. Draw teeth as radial lines/segments.
- Planetary mode: sun gear at center, planet gears orbiting, ring gear.
- Animation: requestAnimationFrame; respect prefers-reduced-motion by pausing animation (render a static frame).
- Sliders: ratio (50–160), input RPM (500–6000), load torque (0–120 Nm?). Compute: output RPM = input / ratio; efficiency = base 93% minus losses; torsional stiffness = Nm/arcmin derived.

Readouts: output RPM, torsional stiffness, efficiency, torque, maybe backlash arcmin.

Let me think about the physics-ish computation:

ratio = slider value (e.g., 80). inputRpm. outputRpm = inputRpm / ratio.
Efficiency: strain-wave ~85%, planetary ~91%. Efficiency depends on speed and load: e.g., base 92%, minus losses proportional to input rpm and load: efficiency = clamp(base - rpmLoss - loadLoss). Let me define: base efficiency 0.92; rpm loss: higher rpm → slightly lower efficiency (churn losses): subtract up to ~4% at 6000 rpm; load loss subtracts up to ~3% at max torque. Compute: eff = base - (rpm-500)/5000 * 0.008 - (load-0)/120 * 0.006. Something plausible.

Torsional stiffness: Nm/arcmin — for harmonic drives, stiffness is high; compute as a function of torque and ratio: e.g., stiffness = (load * ratio) / ... Actually torsional stiffness expressed as Nm/arcmin means angular deflection per torque. Let me compute deflection angle: torsional deflection = load * deflection coefficient; report stiffness as Nm/arcmin: e.g., stiffness = 0.9 + something. Let me just produce plausible numbers: torsional stiffness = (ratio * load) / 60 ... hmm. Let me define: deflectionArcmin = load * (ratio/60) * coefficient. And stiffness index = higher for higher ratio. Keep simple: stiffness = base 1.8 Nm/arcmin, modulated by ratio and torque.

The goal is plausible engineering-feel numbers, not strict physics.

Form validation: name, company, email, application select, message; client-side validation with error messages, aria-invalid. Submit handler: prevent default, show success panel. No network.

FAQ: 5 items: torsional hysteresis, ratcheting torque, cross-roller bearings, L10h life calculation, lubrication/cleanroom. JSON-LD FAQPage must match visible FAQ verbatim.

BreadcrumbList JSON-LD.

Open Graph, canonical, meta description.

llms.txt: markdown summary. robots.txt: allow all, sitemap? No external... keep simple.

_headers: 7 security headers: CSP, HSTS, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, Cross-Origin-Opener-Policy, X-Frame-Options? The request says "all 7 security headers" and lists: CSP with frame-ancestors 'none', HSTS, nosniff, Referrer-Policy, Permissions-Policy, Cross-Origin-Opener-Policy — that's 6 named; add X-Frame-Options DENY as the 7th.

Now, size management: this is a large page. I need to keep CSS and JS concise. Let me write compact but production-grade.

Let me draft the CSS tokens:

:root {
  --slate: oklch(0.15 0.015 250);
  --grid: oklch(0.24 0.02 250);
  --surface: oklch(0.19 0.018 250);
  --surface-2: oklch(0.21 0.02 250);
  --line: oklch(0.28 0.02 250);
  --ink: oklch(0.95 0.01 250);
  --ink-dim: oklch(0.72 0.015 250);
  --signal: oklch(0.70 0.18 50);
  --signal-dim: oklch(0.55 0.14 50);
  --amber: oklch(0.78 0.14 80);
}

Background grid: repeating linear-gradient on body or a fixed layer. Use background-image with repeating-linear-gradient for the CAD grid at 1px lines. Ensure it doesn't cause overflow.

Typography: system-ui stack for body? The request says monospace technical data. Body: system-ui sans? The design canon says monospace technical data (JetBrains Mono / IBM Plex Mono system stack). Let me use two stacks: --font-mono: "JetBrains Mono", "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; and --font-sans: system-ui... Actually the whole industrial B2B vibe could be monospace-dominant. Let me use mono for headings/labels/data and a clean sans for prose paragraphs. Hmm, the design canon says monospace technical data. Let me use mono for headings/labels/data and a sans for body copy.

Contrast: titanium white on dark slate = >7:1. Signal orange on dark: check contrast — oklch 0.70 0.18 50 on 0.15 background: luminance difference is fine for large text; use signal mainly for accents, borders, small labels might need care. Ensure primary text contrast ≥7:1: --ink 0.95 on --slate 0.15 is ~14:1. Good.

Now the canvas JS. Let me write a compact renderer:

const canvas = document.getElementById('kinematics');
const dpr = Math.min(2, devicePixelRatio || 1);
Set canvas.width = canvas.clientWidth * dpr, height similarly, with explicit attribute dimensions in HTML (width="720" height="480"). CSS: width:100%; height:auto? For canvas, height auto may distort. Better: aspect-ratio in CSS. But CLS 0: explicit width/height attributes give intrinsic ratio, and CSS width:100% height:auto preserves ratio. Good.

Draw function:

function drawGear(ctx, cx, cy, teeth, radius, toothLen, rot, opts) — draw tooth profile as trapezoidal segments: for each tooth, draw a wedge from inner radius to outer radius. Use ctx.rotate? Use ctx transform? That's fine — canvas drawing transforms are not DOM style.

Strain-wave rendering:
- Outer circular spline: ring with internal teeth; draw as ring band with teeth pointing inward.
- Flexspline: thin ring that deforms elliptically; animate ellipse by rotating wave generator.
- Wave generator: elliptical cam with two lobes; rotates at input speed.
- Output flange: outer shell that rotates at output speed.

Animation: rotation angle = accumulated by rpm * time. Use a "virtual time" so the animation is visible: scale rpm down? Visual rotation: input rpm 500–6000 → if actual, too fast. Scale: rotate at (rpm/60) rev per second? E.g., 6000 rpm = 100 rev/s — too fast. Scale factor: display at 1/60 of actual? Let me make the wave generator rotate visually at ~0.5 rev/s max. Multiply rpm by a visual factor.

Let me compute visual rotation: rot = (inputRpm * visualFactor) / 60 rev/s. visualFactor maybe 0.02. Then output rotates at outputRpm * same factor. Since ratio divides, output rotates slower.

Actually simpler: accumulate angle per frame: angle += (rpm * 0.02) * (frameTime/1000) * 360 degrees... let me just do: degPerSec = rpm * scaleFactor. With scaleFactor chosen so that at 6000 rpm the visual is ~2 rev/s. rpm*0.02 → 6000*0.02 = 120 deg/s? Hmm 120 deg/s ≈ 0.33 rev/s. At 500 rpm → 10 deg/s, slow. OK.

Let me not overthink; the visual should look smooth.

Planetary mode: sun gear at center rotating at input, 3 planet gears orbiting (meshing), ring gear stationary. Compute orbital motion.

Also draw meshing teeth engagement highlight (signal color).

Readouts update on input events.

Reduced motion: matchMedia('(prefers-reduced-motion: reduce)') → stop rAF, render a static frame once.

Mode toggle: buttons with aria-pressed, toggle classes on the panel; JS reads mode.

Torque-speed envelope: SVG chart with polyline; marker tied to load torque slider: update marker cx/cy via setAttribute. The envelope chart shows torque (y) vs speed (x): continuous duty zone, peak zone, burst. The marker represents current operating point: map load torque to y, output rpm to x. Nice interactive tie-in.

Cutaway SVG: animate wave generator rotation via transform attribute updated in JS loop, plus flexspline ellipse deformation? That's complex; maybe animate a subtle rotation of the wave generator group and a highlight pulse. Keep modest: rotate the wave generator ellipse group. Respect reduced motion.

Table: 3 series with columns: series, ratio options, backlash <0.5 arcmin, peak torque, continuous torque, hollow shaft bore mm, mass kg, output flange, etc. Wrap in .table-wrap.

Quality section: cards for ISO 9001:2015, AGMA 2001, ISO 5 cleanroom lubrication, life testing L10 = 10,000 hours? Let me write plausible copy.

FAQ: 5 questions:
1. What causes torsional hysteresis in strain-wave drives and how is it compensated?
2. What is ratcheting torque and how is it avoided?
3. Why cross-roller bearings for hollow-shaft output?
4. How is L10 life calculated?
5. Lubrication and cleanroom compatibility?

JSON-LD FAQPage must match verbatim. I'll write the questions/answers in the visible section and mirror them in JSON-LD.

Form: fields with validation on submit; show inline errors; success message. Use novalidate + custom validation.

Footer: nav, legal, contact.

Now let me think about file size and truncation risk. The system says keep clean and concise so each file completes. index.html will be large but manageable. I'll aim for compact CSS (maybe ~200 lines) and compact JS (~150 lines). Let me write carefully.

CSP meta:

<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'sha256-__CSP_SCRIPT__'; style-src 'sha256-__CSP_STYLE__'; img-src 'self' data:; font-src 'self'; connect-src 'none'; form-action 'self