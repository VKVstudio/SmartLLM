FILE: index.html
```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KRONOS PRECISION GEARWORKS — Strain-Wave &amp; Planetary Actuators for Surgical and Industrial Robotics</title>
<meta name="description" content="KRONOS PRECISION GEARWORKS manufactures zero-backlash strain-wave (harmonic) drives and planetary actuators for surgical and industrial robotics. KRG-14, KRG-25 and KRG-40 series with backlash under 0.5 arcmin, hollow-shaft outputs, ISO 5 cleanroom lubrication and L10-rated life testing.">
<link rel="canonical" href="https://www.kronosgearworks.example/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="KRONOS PRECISION GEARWORKS">
<meta property="og:title" content="KRONOS PRECISION GEARWORKS — Strain-Wave &amp; Planetary Actuators">
<meta property="og:description" content="Zero-backlash strain-wave (harmonic) drives and planetary actuators for surgical and industrial robotics. KRG-14, KRG-25 and KRG-40 series.">
<meta property="og:url" content="https://www.kronosgearworks.example/">
<meta name="theme-color" content="#1a222b">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'sha256-__CSP_SCRIPT__'; style-src 'sha256-__CSP_STYLE__'; img-src 'self' data:; font-src 'self'; connect-src 'none'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'; upgrade-insecure-requests">
<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[
{"@type":"Organization","@id":"https://www.kronosgearworks.example/#org","name":"KRONOS PRECISION GEARWORKS","url":"https://www.kronosgearworks.example/","description":"Manufacturer of zero-backlash strain-wave (harmonic) drives and planetary actuators for surgical and industrial robotics.","areaServed":["North America","EMEA","APAC"]},
{"@type":"WebSite","@id":"https://www.kronosgearworks.example/#website","url":"https://www.kronosgearworks.example/","name":"KRONOS PRECISION GEARWORKS Engineering Portal","publisher":{"@id":"https://www.kronosgearworks.example/#org"}},
{"@type":"BreadcrumbList","@id":"https://www.kronosgearworks.example/#breadcrumb","itemListElement":[{"@type":"ListItem","position":1,"name":"Home","item":"https://www.kronosgearworks.example/"},{"@type":"ListItem","position":2,"name":"Actuator Series","item":"https://www.kronosgearworks.example/#series"},{"@type":"ListItem","position":3,"name":"FAQ","item":"https://www.kronosgearworks.example/#faq"}]},
{"@type":"Product","@id":"https://www.kronosgearworks.example/#krg14","name":"KRG-14 Micro Surgical","description":"Micro strain-wave actuator for surgical robotics: 14 mm hollow-shaft output, backlash under 0.5 arcmin, continuous torque 1.4 Nm, peak torque 3.0 Nm, 180 g, ISO 5 cleanroom lubrication.","category":"Robotic Actuator","brand":{"@id":"https://www.kronosgearworks.example/#org"}},
{"@type":"Product","@id":"https://www.kronosgearworks.example/#krg25","name":"KRG-25 Cobot Joint","description":"Cobot joint strain-wave actuator: 25 mm hollow-shaft output, backlash under 0.5 arcmin, continuous torque 11 Nm, peak torque 24 Nm, 940 g, torsional stiffness 2.1 Nm/arcmin.","category":"Robotic Actuator","brand":{"@id":"https://www.kronosgearworks.example/#org"}},
{"@type":"Product","@id":"https://www.kronosgearworks.example/#krg40","name":"KRG-40 Heavy Palletizer","description":"Planetary actuator for heavy palletizers: 40 mm hollow-shaft output, backlash under 0.5 arcmin, continuous torque 52 Nm, peak torque 96 Nm, 3.1 kg, torsional stiffness 3.4 Nm/arcmin.","category":"Robotic Actuator","brand":{"@id":"https://www.kronosgearworks.example/#org"}},
{"@type":"FAQPage","@id":"https://www.kronosgearworks.example/#faq-ld","mainEntity":[
{"@type":"Question","name":"What causes torsional hysteresis in a strain-wave drive and how is it compensated?","acceptedAnswer":{"@type":"Answer","text":"Torsional hysteresis arises from the flexspline's elastic recovery. When the wave generator deforms the flexspline, the thin-walled cup stores strain energy and releases it slowly as the wave rotates. This lag shows up as torque ripple and position drift at low speeds. KRONOS compensates by pairing the flexspline with a preloaded cross-roller bearing, applying a static preload torque at assembly, and mapping the hysteresis curve in the servo controller so the drive can be closed-loop corrected within 0.5 arcmin. Torsional stiffness of 1.8 to 3.4 Nm/arcmin keeps deflection predictable under load."}},
{"@type":"Question","name":"What is ratcheting torque and how is it avoided?","acceptedAnswer":{"@type":"Answer","text":"Ratcheting is the sudden release of stored torsional energy when the gear teeth slip and re-engage, producing a torque spike. It occurs when the flexspline is over-torqued beyond its rated envelope, or when the input shaft is stopped abruptly under load. To avoid ratcheting, the torque-speed envelope defines a continuous duty band and a peak band. KRONOS KRG series are rated for peak torque at 120 percent of continuous torque, with a burst limit that is never exceeded in normal operation. The torque-speed envelope chart in this portal shows the safe operating zones for each series."}},
{"@type":"Question","name":"Why do hollow-shaft outputs use cross-roller bearings instead of ball bearings?","acceptedAnswer":{"@type":"Answer","text":"Cross-roller bearings distribute load across alternating rollers rather than discrete balls, which spreads the load over a larger contact area and reduces deflection under radial and axial loads. For hollow-shaft outputs where cables and fluid lines pass through the center, cross-roller bearings maintain stiffness without a solid shaft. KRONOS KRG series use cross-roller bearings to keep torsional stiffness above 1.8 Nm/arcmin and backlash under 0.5 arcmin across the full service life."}},
{"@type":"Question","name":"How is L10 life calculated for harmonic drives?","acceptedAnswer":{"@type":"Answer","text":"L10 life is the median life of a batch of drives under a defined load profile. KRONOS calculates L10 life using Weibull distribution analysis on a sample of 10 percent of units tested under the rated torque-speed envelope. For the KRG series, L10 life is rated at 10,000 hours under continuous duty at rated torque, with peak torque events counted as duty cycles. The calculation uses the torque-speed envelope, the lubrication life, and the flexspline fatigue curve. Life testing data is available on request."}},
{"@type":"Question","name":"Is the lubrication compatible with cleanroom environments?","acceptedAnswer":{"@type":"Answer","text":"Yes. KRONOS KRG series use ISO 5 cleanroom-compatible lubricants with low out-of-spec volatility. The lubricant is sealed within the gear housing and does not migrate into the air stream. For surgical applications, the drives are supplied with a fluorinated grease rated for ISO 5 cleanroom assembly. Lubrication life is 10,000 hours under continuous duty. Cleanroom assembly and packaging are performed at ISO 5 under ISO 9001:2015 quality control."}}]}
]}
</script>
<style>
*,*::before,*::after{box-sizing:border-box}
html,body{max-width:100%;overflow-x:clip}
:root{
--slate:oklch(0.15 0.015 250);
--grid:oklch(0.24 0.02 250);
--surface:oklch(0.19 0.018 250);
--surface-2:oklch(0.22 0.02 250);
--line:oklch(0.30 0.025 250);
--ink:oklch(0.95 0.01 250);
--ink-dim:oklch(0.72 0.015 250);
--signal:oklch(0.70 0.18 50);
--signal-dim:oklch(0.52 0.14 50);
--amber:oklch(0.78 0.13 75);
--font-mono:"JetBrains Mono","IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
--font-sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
}
body{margin:0;background:var(--slate);color:var(--ink);font:400 1rem/1.65 var(--font-sans);background-image:repeating-linear-gradient(to right,var(--grid) 0 1px,transparent 1px 48px),repeating-linear-gradient(to bottom,var(--grid) 0 1px,transparent 1px 48px);background-size:48px 48px}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px}
.mono{font-family:var(--font-mono)}
.skip-link{position:absolute;left:-999px;top:0;background:var(--signal);color:var(--slate);padding:10px 16px;z-index:100}
.skip-link:focus{left:8px;top:8px}
header{border-bottom:1px solid var(--line);background:var(--surface)}
.nav{display:flex;flex-wrap:wrap;align-items:center;gap:18px;padding:14px 0;min-width:0}
.logo{display:flex;align-items:center;gap:10px;font:700 1rem/1 var(--font-mono);letter-spacing:.14em;text-transform:uppercase;color:var(--ink);text-decoration:none}
.logo-mark{width:26px;height:26px;flex:none}
.nav-links{display:flex;flex-wrap:wrap;gap:2px;list-style:none;margin:0;padding:0;min-width:0}
.nav-links a{display:block;padding:8px 12px;color:var(--ink-dim);text-decoration:none;font:600 .82rem/1 var(--font-mono);letter-spacing:.08em;text-transform:uppercase}
.nav-links a:hover,.nav-links a:focus-visible{color:var(--ink);background:var(--surface-2)}
.nav-cta{margin-left:auto;padding:9px 16px;background:var(--signal);color:var(--slate);font:700 .82rem/1 var(--font-mono);letter-spacing:.08em;text-transform:uppercase;text-decoration:none;border:1px solid var(--signal)}
.nav-cta:hover,.nav-cta:focus-visible{background:var(--amber)}
.hero{padding:44px 0 36px}
.eyebrow{font:600 .78rem/1 var(--font-mono);letter-spacing:.22em;text-transform:uppercase;color:var(--signal);margin:0 0 16px}
h1{font:700 clamp(1.9rem,4.5vw,3rem)/1.1 var(--font-mono);letter-spacing:.01em;margin:0 0 18px;max-width:22ch}
.lede{font-size:1.12rem;color:var(--ink-dim);max-width:62ch;margin:0 0 24px}
.hero-grid{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:28px;align-items:start}
.chips{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 28px;padding:0;list-style:none}
.chip{display:inline-flex;align-items:center;gap:8px;padding:8px 14px;border:1px solid var(--line);background:var(--surface);font:600 .78rem/1 var(--font-mono);letter-spacing:.08em;text-transform:uppercase;color:var(--ink-dim)}
.chip b{color:var(--signal)}
.viz-panel{border:1px solid var(--line);background:var(--surface);padding:18px}
.viz-toolbar{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px}
.mode-btn{padding:9px 14px;border:1px solid var(--line);background:var(--surface-2);color:var(--ink-dim);font:600 .78rem/1 var(--font-mono);letter-spacing:.08em;text-transform:uppercase;cursor:pointer}
.mode-btn[aria-pressed="true"]{background:var(--signal);color:var(--slate);border-color:var(--signal)}
.mode-btn:hover,.mode-btn:focus-visible{border-color:var(--signal);color:var(--ink)}
canvas{display:block;width:100%;height:auto;border:1px solid var(--line);background:var(--slate)}
.controls{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:18px;margin:18px 0 0}
.control label{display:flex;justify-content:space-between;gap:10px;font:600 .74rem/1 var(--font-mono);letter-spacing:.1em;text-transform:uppercase;color:var(--ink-dim);margin-bottom:10px}
.control output{color:var(--signal);font-weight:700}
input[type=range]{width:100%;accent-color:var(--signal)}
.readouts{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);margin-top:18px}
.readout{background:var(--surface);padding:14px}
.readout .k{font:600 .68rem/1 var(--font-mono);letter-spacing:.14em;text-transform:uppercase;color:var(--ink-dim);margin-bottom:8px}
.readout .v{font:700 1.5rem/1 var(--font-mono);color:var(--ink)}
.readout .v small{font-size:.72rem;color:var(--ink-dim);margin-left:4px}
section{padding:56px 0;border-top:1px solid var(--line)}
h2{font:700 clamp(1.4rem,3vw,2rem)/1.15 var(--font-mono);letter-spacing:.02em;margin:0 0 10px}
.section-note{color:var(--ink-dim);max-width:64ch;margin:0 0 28px}
.cutaway-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:28px;align-items:start}
svg{max-width:100%;height:auto}
.panel{border:1px solid var(--line);background:var(--surface);padding:18px}
.panel h3{font:600 .82rem/1 var(--font-mono);letter-spacing:.12em;text-transform:uppercase;color:var(--signal);margin:0 0 14px}
.legend{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-top:16px}
.legend-item{display:flex;gap:10px;align-items:flex-start;font:500 .82rem/1.4 var(--font-sans);color:var(--ink-dim)}
.legend-item .dot{width:12px;height:12px;flex:none;margin-top:3px}
.table-wrap{overflow-x:auto;border:1px solid var(--line);background:var(--surface)}
table{width:100%;border-collapse:collapse;font:500 .85rem/1.5 var(--font-mono);min-width:640px}
th,td{padding:12px 14px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{font:700 .72rem/1 var(--font-mono);letter-spacing:.12em;text-transform:uppercase;color:var(--signal);background:var(--surface-2)}
tbody tr:hover{background:var(--surface-2)}
tbody td:first-child{font-weight:700;color:var(--ink)}
.series-tag{display:inline-block;padding:3px 8px;background:var(--signal);color:var(--slate);font:700 .72rem/1 var(--font-mono);letter-spacing:.08em;text-transform:uppercase;margin-bottom:6px}
.quality-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:20px}
.q-card{border:1px solid var(--line);background:var(--surface);padding:20px;display:flex;flex-direction:column;gap:12px}
.q-card .badge{align-self:flex-start;padding:6px 12px;border:1px solid var(--signal);color:var(--signal);font:700 .72rem/1 var(--font-mono);letter-spacing:.1em;text-transform:uppercase}
.q-card p{color:var(--ink-dim);font-size:.92rem;margin:0}
.faq{display:grid;gap:14px}
.faq-item{border:1px solid var(--line);background:var(--surface)}
.faq-item summary{cursor:pointer;padding:16px 18px;font:600 .95rem/1.3 var(--font-mono);color:var(--ink);list-style:none;display:flex;justify-content:space-between;gap:14px;align-items:center}
.faq-item summary::-webkit-details-marker{display:none}
.faq-item summary .chev{color:var(--signal);flex:none;transition:none}
.faq-item[open] summary{background:var(--surface-2)}
.faq-item .answer{padding:0 18px 18px;color:var(--ink-dim);font-size:.95rem;line-height:1.7}
.faq-item .answer p{margin:0}
.form-panel{border:1px solid var(--line);background:var(--surface);padding:22px}
.form-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px;margin-bottom:18px}
.field label{display:block;font:600 .74rem/1 var(--font-mono);letter-spacing:.1em;text-transform:uppercase;color:var(--ink-dim);margin-bottom:8px}
.field input,.field select,.field textarea{width:100%;padding:12px 14px;background:var(--slate);border:1px solid var(--line);color:var(--ink);font:500 .92rem/1.5 var(--font-sans)}
.field textarea{min-height:120px;resize:vertical}
.field input:focus,.field select:focus,.field textarea:focus{outline:2px solid var(--signal);outline-offset:1px}
.field .err{display:block;margin-top:6px;font:600 .74rem/1 var(--font-mono);color:var(--signal);min-height:1em}
.form-actions{display:flex;flex-wrap:wrap;gap:14px;align-items:center}
.btn{padding:12px 22px;background:var(--signal);color:var(--slate);border:1px solid var(--signal);font:700 .82rem/1 var(--font-mono);letter-spacing:.08em;text-transform:uppercase;cursor:pointer}
.btn:hover,.btn:focus-visible{background:var(--amber);border-color:var(--amber)}
.btn-ghost{background:transparent;color:var(--ink);border-color:var(--line)}
.btn-ghost:hover,.btn-ghost:focus-visible{border-color:var(--signal);color:var(--signal)}
.form-status{font:600 .82rem/1 var(--font-mono);color:var(--signal)}
footer{border-top:1px solid var(--line);background:var(--surface);padding:40px 0}
.footer-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:28px}
.footer-grid h3{font:600 .76rem/1 var(--font-mono);letter-spacing:.14em;text-transform:uppercase;color:var(--signal);margin:0 0 14px}
.footer-grid ul{list-style:none;margin:0;padding:0;display:grid;gap:8px}
.footer-grid a{color:var(--ink-dim);text-decoration:none;font-size:.9rem}
.footer-grid a:hover,.footer-grid a:focus-visible{color:var(--signal)}
.footer-bottom{margin-top:28px;padding-top:20px;border-top:1px solid var(--line);display:flex;flex-wrap:wrap;gap:16px;justify-content:space-between;font:500 .78rem/1 var(--font-mono);color:var(--ink-dim)}
@media (max-width:900px){.hero-grid,.cutaway-grid{grid-template-columns:1fr}}
@media (max-width:480px){.chip,.btn,.nav-cta,.mode-btn{white-space:normal}.readout .v{font-size:1.25rem}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>
</head>
<body>
<a class="skip-link" href="#main">Skip to main content</a>
<header>
<div class="wrap nav">
<a class="logo" href="#top" aria-label="KRONOS Precision Gearworks home">
<svg class="logo-mark" width="26" height="26" viewBox="0 0 26 26" aria-hidden="true" focusable="false"><circle cx="13" cy="13" r="9" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="13" cy="13" r="4.5" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M13 2v4M13 22v4M2 13h4M22 13h4" stroke="currentColor" stroke-width="1.5"/></svg>
KRONOS
</a>
<ul class="nav-links">
<li><a href="#visualizer">Visualizer</a></li>
<li><a href="#cross-section">Cross-Section</a></li>
<li><a href="#series">Series</a></li>
<li><a href="#quality">Quality</a></li>
<li><a href="#faq">FAQ</a></li>
</ul>
<a class="nav-cta" href="#consult">Consult</a>
</div>
</header>
<main id="main">
<section class="hero" id="top">
<div class="wrap">
<p class="eyebrow">Strain-Wave · Planetary · Zero-Backlash</p>
<h1>Precision gearwork for surgical and industrial robotics.</h1>
<p class="lede">KRONOS PRECISION GEARWORKS manufactures zero-backlash strain-wave (harmonic) drives and planetary actuators rated for continuous duty, hollow-shaft routing, and ISO 5 cleanroom assembly. Backlash under 0.5 arcmin across the full service life.</p>
<ul class="chips">
<li class="chip"><b>&lt; 0.5</b> arcmin backlash</li>
<li class="chip"><b>10,000 h</b> L10 life rating</li>
<li class="chip"><b>ISO 5</b> cleanroom lubrication</li>
<li class="chip"><b>1.8–3.4</b> Nm/arcmin stiffness</li>
</ul>
<div class="hero-grid">
<div>
<p class="mono" style="color:var(--ink-dim);font-size:.82rem;letter-spacing:.08em">Torsional stiffness and efficiency are computed live from the kinematics model. Drag the sliders to explore the torque-speed envelope.</p>
</div>
</div>
</div>
</section>
<section id="visualizer">
<div class="wrap">
<h2>Kinematics Visualizer</h2>
<p class="section-note">Interactive procedural model of the gear mesh. Switch between strain-wave and planetary kinematics. Sliders drive the live computation of output RPM, torsional stiffness, and efficiency.</p>
<div class="viz-panel">
<div class="viz-toolbar" role="group" aria-label="Kinematics mode">
<button class="mode-btn" id="mode-strain" aria-pressed="true" type="button">Strain-Wave</button>
<button class="mode-btn" id="mode-planetary" aria-pressed="false" type="button">Planetary</button>
</div>
<canvas id="kinematics" width="720" height="460" role="img" aria-label="Animated gear mesh visualization showing strain-wave or planetary kinematics with live rotation and torque indicators"></canvas>
<div class="controls">
<div class="control">
<label for="ratio">Reduction Ratio <output id="ratio-out">80:1</output></label>
<input type="range" id="ratio" min="50" max="160" step="1" value="80" aria-describedby="ratio-out">
</div>
<div class="control">
<label for="rpm">Input RPM <output id="rpm-out">1200</output></label>
<input type="range" id="rpm" min="500" max="6000" step="10" value="1200" aria-describedby="rpm-out">
</div>
<div class="control">
<label for="load">Load Torque <output id="load-out">18 Nm</output></label>
<input type="range" id="load" min="0" max="120" step="1" value="18" aria-describedby="load-out">
</div>
</div>
<div class="readouts" aria-live="polite">
<div class="readout"><div class="k">Output RPM</div><div class="v" id="ro-out">15<small>rpm</small></div></div>
<div class="readout"><div class="k">Torsional Stiffness</div><div class="v" id="ro-stiff">2.1<small>Nm/arcmin</small></div></div>
<div class="readout"><div class="k">Efficiency</div><div class="v" id="ro-eff">91<small>%</small></div></div>
<div class="readout"><div class="k">Backlash</div><div class="v" id="ro-back">0.4<small>arcmin</small></div></div>
</div>
</div>
</div>
</section>
<section id="cross-section">
<div class="wrap">
<h2>Cross-Section &amp; Torque-Speed Envelope</h2>
<p class="section-note">The strain-wave drive is a thin-walled flexspline, a rigid circular spline, and an elliptical wave generator. The torque-speed envelope defines the continuous, peak, and burst operating zones for each series.</p>
<div class="cutaway-grid">
<div class="panel">
<h3>Strain-Wave Cutaway</h3>
<svg id="cutaway" width="640" height="420" viewBox="0 0 640 420" role="img" aria-label="Cross-section of a strain-wave drive showing circular spline, flexspline, and wave generator">
<defs><linearGradient id="metal" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="oklch(0.32 0.02 250)"/><stop offset="1" stop-color="oklch(0.22 0.02 250)"/></linearGradient></defs>
<circle cx="320" cy="210" r="150" fill="url(#metal)" stroke="var(--line)" stroke-width="1"/>
<g id="cs-teeth" fill="none" stroke="var(--ink-dim)" stroke-width="1.5"></g>
<circle cx="320" cy="210" r="118" fill="none" stroke="var(--signal)" stroke-width="2" stroke-dasharray="4 3"/>
<g id="wg" fill="none" stroke="var(--amber)" stroke-width="2"></g>
<circle cx="320" cy="210" r="60" fill="var(--slate)" stroke="var(--line)" stroke-width="1"/>
<circle cx="320" cy="210" r="20" fill="var(--surface-2)" stroke="var(--signal)" stroke-width="1.5"/>
<text x="320" y="392" text-anchor="middle" font-family="var(--font-mono)" font-size="12" fill="var(--ink-dim)">Hollow shaft output</text>
</svg>
<div class="legend">
<div class="legend-item"><span class="dot" style="background:var(--ink-dim)"></span><span>Circular spline — rigid outer ring with internal teeth</span></div>
<div class="legend-item"><span class="dot" style="background:var(--signal)"></span><span>Flexspline — thin-walled cup, deforms under the wave</span></div>
<div class="legend-item"><span class="dot" style="background:var(--amber)"></span><span>Wave generator — elliptical cam, input shaft</span></div>
</div>
</div>
<div class="panel">
<h3>Torque-Speed Envelope</h3>
<svg id="envelope" width="640" height="420" viewBox="0 0 640 420" role="img" aria-label="Torque-speed operating envelope chart with continuous, peak, and burst zones">
<rect x="60" y="30" width="540" height="340" fill="var(--slate)" stroke="var(--line)" stroke-width="1"/>
<g font-family="var(--font-mono)" font-size="11" fill="var(--ink-dim)">
<line x1="60" y1="30" x2="60" y2="370" stroke="var(--line)"/><line x1="60" y1="30" x2="600" y2="30" stroke="var(--line)"/>
<line x1="120" y1="370" x2="120" y2="30" stroke="var(--line)"/><line x1="240" y1="370" x2="240" y2="30" stroke="var(--line)"/><line x1="360" y1="370" x2="360" y2="30" stroke="var(--line)"/><line x1="480" y1="370" x2="480" y2="30" stroke="var(--line)"/><line x1="600" y1="370" x2="600" y2="30" stroke="var(--line)"/>
<text x="60" y="385">0 rpm</text><text x="240" y="385">2000 rpm</text><text x="480" y="385">4000 rpm</text><text x="600" y="385">6000 rpm</text>
<text x="30" y="370" transform="rotate(-90 30 370)" transform-origin="30 370">0 Nm</text>
</g>
<polyline id="env-continuous" fill="none" stroke="var(--signal)" stroke-width="2" points="60,30 120,30 240,30 360,30 480,30 600,30"/>
<polyline id="env-peak" fill="none" stroke="var(--amber)" stroke-width="2" stroke-dasharray="6 4" points="60,30 120,30 240,30 360,30 480,30 600,30"/>
<circle id="env-marker" cx="240" cy="180" r="6" fill="var(--signal)" stroke="var(--slate)" stroke-width="2"/>
<text x="320" y="360" text-anchor="middle" font-family="var(--font-mono)" font-size="13" fill="var(--signal)">Operating point</text>
</svg>
<p class="mono" style="font-size:.78rem;color:var(--ink-dim);margin-top:14px">The marker tracks the load torque slider. Continuous zone is solid; peak zone is dashed.</p>
</div>
</div>
</div>
</section>
<section id="series">
<div class="wrap">
<h2>Actuator Series Specification</h2>
<p class="section-note">Three series cover surgical micro-actuation through cobot joints to heavy palletizing. All series are rated for continuous duty with backlash under 0.5 arcmin.</p>
<div class="table-wrap">
<table>
<thead><tr><th scope="col">Series</th><th scope="col">Reduction Ratio</th><th scope="col">Backlash</th><th scope="col">Continuous Torque</th><th scope="col">Peak Torque</th><th scope="col">Hollow Shaft Bore</th><th scope="col">Mass</th><th scope="col">Torsional Stiffness</th></tr></thead>
<tbody>
<tr><td><span class="series-tag">KRG-14</span><br>Micro Surgical</td><td>50:1 / 80:1 / 100:1</td><td>&lt; 0.5 arcmin</td><td>1.4 Nm</td><td>3.0 Nm</td><td>14 mm</td><td>180 g</td><td>1.8 Nm/arcmin</td></tr>
<tr><td><span class="series-tag">KRG-25</span><br>Cobot Joint</td><td>50:1 / 80:1 / 120:1</td><td>&lt; 0.5 arcmin</td><td>11 Nm</td><td>24 Nm</td><td>25 mm</td><td>940 g</td><td>2.1 Nm/arcmin</td></tr>
<tr><td><span class="series-tag">KRG-40</span><br>Heavy Palletizer</td><td>50:1 / 80:1 / 160:1</td><td>&lt; 0.5 arcmin</td><td>52 Nm</td><td>96 Nm</td><td>40 mm</td><td>3.1 kg</td><td>3.4 Nm/arcmin</td></tr>
</tbody>
</table>
</div>
</div>
</section>
<section id="quality">
<div class="wrap">
<h2>Quality &amp; Life-Testing Compliance</h2>
<p class="section-note">Every drive is manufactured under ISO 9001:2015 quality control, rated to AGMA 2001 gear accuracy, and assembled under ISO 5 cleanroom conditions with low-volatility lubrication.</p>
<div class="quality-grid">
<div class="q-card"><span class="badge">ISO 9001:2015</span><h3>Quality Management</h3><p>Full traceability from raw stock to final assembly. Each drive is serialized and torque-mapped at assembly. Process controls are audited quarterly.</p></div>
<div class="q-card"><span class="badge">AGMA 2001</span><h3>Gear Accuracy</h3><p>Teeth are cut to AGMA 2001 accuracy class A8. Tooth profile deviation is held within 0.012 mm to maintain zero-backlash engagement across the life envelope.</p></div>
<div class="q-card"><span class="badge">ISO 5</span><h3>Cleanroom Lubrication</h3><p>Fluorinated grease rated for ISO 5 cleanroom assembly. Low out-of-spec volatility prevents lubricant migration into the air stream. Sealed housing for surgical applications.</p></div>
<div class="q-card"><span class="badge">L10 · 10,000 h</span><h3>Life Testing</h3><p>Weibull L10 life testing at rated torque-speed envelope. 10 percent of units are tested to failure to establish the median life distribution. Life data available on request.</p></div>
</div>
</div>
</section>
<section id="faq">
<div class="wrap">
<h2>Mechanical Engineering FAQ</h2>
<p class="section-note">Frequently asked questions on torsional hysteresis, ratcheting torque, cross-roller bearings, L10 life calculation, and cleanroom lubrication.</p>
<div class="faq">
<details class="faq-item" name="faq" open>
<summary>What causes torsional hysteresis in a strain-wave drive and how is it compensated? <span class="chev" aria-hidden="true">+</span></summary>
<div class="answer"><p>Torsional hysteresis arises from the flexspline's elastic recovery. When the wave generator deforms the flexspline, the thin-walled cup stores strain energy and releases it slowly as the wave rotates. This lag shows up as torque ripple and position drift at low speeds. KRONOS compensates by pairing the flexspline with a preloaded cross-roller bearing, applying a static preload torque at assembly, and mapping the hysteresis curve in the servo controller so the drive can be closed-loop corrected within 0.5 arcmin. Torsional stiffness of 1.8 to 3.4 Nm/arcmin keeps deflection predictable under load.</p></div>
</details>
<details class="faq-item" name="faq">
<summary>What is ratcheting torque and how is it avoided? <span class="chev" aria-hidden="true">+</span></summary>
<div class="answer"><p>Ratcheting is the sudden release of stored torsional energy when the gear teeth slip and re-engage, producing a torque spike. It occurs when the flexspline is over-torqued beyond its rated envelope, or when the input shaft is stopped abruptly under load. To avoid ratcheting, the torque-speed envelope defines a continuous duty band and a peak band. KRONOS KRG series are rated for peak torque at 120 percent of continuous torque, with a burst limit that is never exceeded in normal operation. The torque-speed envelope chart in this portal shows the safe operating zones for each series.</p></div>
</details>
<details class="faq-item" name="faq">
<summary>Why do hollow-shaft outputs use cross-roller bearings instead of ball bearings? <span class="chev" aria-hidden="true">+</span></summary>
<div class="answer"><p>Cross-roller bearings distribute load across alternating rollers rather than discrete balls, which spreads the load over a larger contact area and reduces deflection under radial and axial loads. For hollow-shaft outputs where cables and fluid lines pass through the center, cross-roller bearings maintain stiffness without a solid shaft. KRONOS KRG series use cross-roller bearings to keep torsional stiffness above 1.8 Nm/arcmin and backlash under 0.5 arcmin across the full service life.</p></div>
</details>
<details class="faq-item" name="faq">
<summary>How is L10 life calculated for harmonic drives? <span class="chev" aria-hidden="true">+</span></summary>
<div class="answer"><p>L10 life is the median life of a batch of drives under a defined load profile. KRONOS calculates L10 life using Weibull distribution analysis on a sample of 10 percent of units tested under the rated torque-speed envelope. For the KRG series, L10 life is rated at 10,000 hours under continuous duty at rated torque, with peak torque events counted as duty cycles. The calculation uses the torque-speed envelope, the lubrication life, and the flexspline fatigue curve. Life testing data is available on request.</p></div>
</details>
<details class="faq-item" name="faq">
<summary>Is the lubrication compatible with cleanroom environments? <span class="chev" aria-hidden="true">+</span></summary>
<div class="answer"><p>Yes. KRONOS KRG series use ISO 5 cleanroom-compatible lubricants with low out-of-spec volatility. The lubricant is sealed within the gear housing and does not migrate into the air stream. For surgical applications, the drives are supplied with a fluorinated grease rated for ISO 5 cleanroom assembly. Lubrication life is 10,000 hours under continuous duty. Cleanroom assembly and packaging are performed at ISO 5 under ISO 9001:2015 quality control.</p></div>
</details>
</div>
<div class="form-panel">
<h3 style="font:600 .82rem/1 var(--font-mono);letter-spacing:.12em;text-transform:uppercase;color:var(--signal);margin:0 0 18px">CAD STEP Download &amp; Engineering Consultation</h3>
<form id="consult-form" novalidate>
<div class="form-grid">
<div class="field"><label for="f-name">Full Name</label><input type="text" id="f-name" name="name" autocomplete="name" required><span class="err" id="err-name" aria-live="assertive"></span></div>
<div class="field"><label for="f-company">Company</label><input type="text" id="f-company" name="company" autocomplete="organization" required><span class="err" id="err-company" aria-live="assertive"></span></div>
<div class="field"><label for="f-email">Work Email</label><input type="email" id="f-email" name="email" autocomplete="email" required><span class="err" id="err-email" aria-live="assertive"></span></div>
<div class="field"><label for="f-series">Actuator Series</label><select id="f-series" name="series" required><option value="">Select series…</option><option value="KRG-14">KRG-14 Micro Surgical</option><option value="KRG-25">KRG-25 Cobot Joint</option><option value="KRG-40">KRG-40 Heavy Palletizer</option></select><span class="err" id="err-series" aria-live="assertive"></span></div>
</div>
<div class="field" style="margin-bottom:18px"><label for="f-message">Application &amp; Requirements</label><textarea id="f-message" name="message" required></textarea><span class="err" id="err-message" aria-live="assertive"></span></div>
<div class="form-actions">
<button class="btn" type="submit">Request STEP Files</button>
<button class="btn btn-ghost" type="reset">Reset</button>
<span class="form-status" id="form-status" aria-live="polite"></span>
</div>
</form>
</div>
</div>
</section>
</main>
<footer>
<div class="wrap">
<div class="footer-grid">
<div><h3>Series</h3><ul><li><a href="#series">KRG-14 Micro Surgical</a></li><li><a href="#series">KRG-25 Cobot Joint</a></li><li><a href="#series">KRG-40 Heavy Palletizer</a></li></ul></div>
<div><h3>Engineering</h3><ul><li><a href="#visualizer">Kinematics Visualizer</a></li><li><a href="#cross-section">Cross-Section</a></li><li><a href="#faq">FAQ</a></li><li><a href="#consult">Consultation</a></li></ul></div>
<div><h3>Compliance</h3><ul><li><a href="#quality">ISO 9001:2015</a></li><li><a href="#quality">AGMA 2001</a></li><li><a href="#quality">ISO 5 Cleanroom</a></li><li><a href="#quality">L10 Life Testing</a></li></ul></div>
<div><h3>Contact</h3><ul><li><a href="#consult">Engineering Consultation</a></li><li><a href="#consult">CAD STEP Download</a></li><li><a href="#consult">Life Testing Data</a></li></ul></div>
</div>
<div class="footer-bottom"><span>© KRONOS PRECISION GEARWORKS</span><span class="mono">Strain-Wave · Planetary · Zero-Backlash</span></div>
</div>
</footer>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"WebPage","name":"KRONOS PRECISION GEARWORKS Engineering Portal","url":"https://www.kronosgearworks.example/","isPartOf":{"@id":"https://www.kronosgearworks.example/#website"},"about":{"@id":"https://www.kronosgearworks.example/#org"}}
</script>
<script>
(function(){
"use strict";
var canvas=document.getElementById("kinematics");
var cutaway=document.getElementById("cutaway");
var envelope=document.getElementById("envelope");
var ratioIn=document.getElementById("ratio");
var rpmIn=document.getElementById("rpm");
var loadIn=document.getElementById("load");
var ratioOut=document.getElementById("ratio-out");
var rpmOut=document.getElementById("rpm-out");
var loadOut=document.getElementById("load-out");
var roOut=document.getElementById("ro-out");
var roStiff=document.getElementById("ro-stiff");
var roEff=document.getElementById("ro-eff");
var roBack=document.getElementById("ro-back");
var modeStrain=document.getElementById("mode-strain");
var modePlanetary=document.getElementById("mode-planetary");
var csTeeth=document.getElementById("cs-teeth");
var wg=document.getElementById("wg");
var envContinuous=document.getElementById("env-continuous");
var envPeak=document.getElementById("env-peak");
var envMarker=document.getElementById("env-marker");
var form=document.getElementById("consult-form");
var status=document.getElementById("form-status");
var reduce=window.matchMedia("(prefers-reduced-motion: reduce)").matches;
var mode="strain";
var state={ratio:80,rpm:1200,load:18};
function setAttr(el,attr,val){el.setAttribute(attr,val);}
function clamp(v,a,b){return Math.max(a,Math.min(b,v));}
function compute(){var r=state.ratio,inp=state.rpm,load=state.load;var out=inp/r;var eff=92-(inp-500)/5000*0.008-(load/120)*0.006;eff=clamp(eff,84,96);var stiff=(r*load)/60*0.55+1.5;stiff=clamp(stiff,1.8,3.4);var back=0.4+load/120*0.003;back=clamp(back,0.3,0.5);ratioOut.textContent=r+":1";rpmOut.textContent=inp;loadOut.textContent=load+" Nm";roOut.textContent=Math.round(out);roStiff.textContent=stiff.toFixed(1);roEff.textContent=Math.round(eff);roBack.textContent=back.toFixed(1);updateEnvelope();}
function updateEnvelope(){var t=state.load,r=state.ratio;var cy=clamp(370-t/120*1.2,30,370);var cx=clamp(60+r*1.4,60,600);setAttr(envMarker,"cx",cx);setAttr(envMarker,"cy",cy);var pts=[];for(var i=0;i<=600;i+=60){var y=clamp(370-(i/6000)*1.1,30,370);pts.push(i+","+y);}envContinuous.setAttribute("points",pts.join(" "));envPeak.setAttribute("points",pts.join(" "));}
function drawTeeth(){var s="",c=320,r=150;for(var i=0;i<120;i++){var ang=i*Math.PI/120;var x=c+Math.cos(ang)*0;var y=c+Math.sin(ang)*0;}var seg=[];for(var i=0;i<60;i++){var a=i*Math.PI/60;var x1=c+Math.cos(a)*0;var y1=c+Math.sin(a)*0;var x2=c+Math.cos(a)*0;var y2=c+Math.sin(a)*0;seg.push("M"+x1+" "+y1+" L"+(x1+Math.cos(a)*0)+" "+(y1+Math.sin(a)*0));}csTeeth.setAttribute("d",seg.join(" "));var wgSeg=[];for(var i=0;i<2;i++){var a=i*Math.PI/2;wgSeg.push("M"+c+" "+210+" L"+(c+Math.cos(a)*0)+" "+(210+Math.sin(a)*0));}wg.setAttribute("d",wgSeg.join(" "));}
function polar(ctx,cx,cy,teeth,r,rot){ctx.beginPath();for(var i=0;i<teeth;i++){var a=rot+i*Math.PI/teeth;ctx.moveTo(cx,cy-r);ctx.lineTo(cx+Math.cos(a)*0,cy+Math.sin(a)*0);}ctx.stroke();}
function drawStrain(){var ctx=canvas.getContext("2d");var dpr=Math.min(2,window.devicePixelRatio||1);var cw=canvas.clientWidth;var ch=canvas.clientHeight;canvas.width=cw*dpr;canvas.height=ch*dpr;ctx.scale(dpr,dpr);var cx=cw/2,cy=ch/2;var r=state.ratio,inp=state.rpm,load=state.load;var rot=(inp*0.02);var outRot=(inp/r);var a=rot*0.01;ctx.save();ctx.translate(cx,cy);ctx.rotate(a);ctx.beginPath();ctx.arc(0,0,150,0,Math.PI*2);ctx.strokeStyle="oklch(0.32 0.02 250)";ctx.lineWidth=1;ctx.stroke();for(var i=0;i<120;i++){var ang=i*Math.PI/120;ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(Math.cos(ang)*0,Math.sin(ang)*0);ctx.strokeStyle="oklch(0.72 0.015 250)";ctx.lineWidth=1.5;ctx.stroke();}ctx.restore();ctx.save();ctx.translate(cx,cy);ctx.rotate(outRot*0.01);ctx.beginPath();ctx.arc(0,0,118,0,Math.PI*2);ctx.strokeStyle="oklch(0.70 0.18 50)";ctx.lineWidth=2;ctx.stroke();ctx.restore();ctx.save();ctx.translate(cx,cy);ctx.rotate(a);ctx.beginPath();ctx.ellipse(0,0,60,40,0,0,Math.PI*2);ctx.strokeStyle="oklch(0.78 0.13 75)";ctx.lineWidth=2;ctx.stroke();ctx.restore();}
function drawPlanetary(){var ctx=canvas.getContext("2d");var dpr=Math.min(2,window.devicePixelRatio||1);var cw=canvas.clientWidth;var ch=canvas.clientHeight;canvas.width=cw*dpr;canvas.height=ch*dpr;ctx.scale(dpr,dpr);var cx=cw/2,cy=ch/2;var inp=state.rpm;var a=inp*0.01;ctx.save();ctx.translate(cx,cy);ctx.rotate(a);ctx.beginPath();ctx.arc(0,0,60,0,Math.PI*2);ctx.strokeStyle="oklch(0.70 0.18 50)";ctx.lineWidth=2;ctx.stroke();for(var i=0;i<24;i++){var ang=i*Math.PI/24;ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(Math.cos(ang)*0,Math.sin(ang)*0);ctx.strokeStyle="oklch(0.72 0.015 250)";ctx.lineWidth=1.5;ctx.stroke();}ctx.restore();for(var p=0;p<3;p++){var pa=(inp*0.01)+(p*Math.PI/3);ctx.save();ctx.translate(cx+Math.cos(pa)*0,cy+Math.sin(pa)*0);ctx.beginPath();ctx.arc(0,0,30,0,Math.PI*2);ctx.strokeStyle="oklch(0.78 0.13 75)";ctx.lineWidth=1.5;ctx.stroke();ctx.restore();}}
function frame(){if(reduce){drawStrain();return;}requestAnimationFrame(frame);}
function setMode(m){mode=m;modeStrain.setAttribute("aria-pressed",m==="strain");modePlanetary.setAttribute("aria-pressed",m==="planetary");}
ratioIn.addEventListener("input",function(){state.ratio=parseInt(ratioIn.value,10);compute();});
rpmIn.addEventListener("input",function(){state.rpm=parseInt(rpmIn.value,10);compute();});
loadIn.addEventListener("input",function(){state.load=parseInt(loadIn.value,10);compute();});
modeStrain.addEventListener("click",function(){setMode("strain");});
modePlanetary.addEventListener("click",function(){setMode("planetary");});
form.addEventListener("submit",function(e){e.preventDefault();var ok=true;var fields=[{el:document.getElementById("f-name"),err:document.getElementById("err-name"),msg:"Full name is required."},{el:document.getElementById("f-company"),err:document.getElementById("err-company"),msg:"Company is required."},{el:document.getElementById("f-email"),err:document.getElementById("err-email"),msg:"Valid work email is required."},{el:document.getElementById("f-series"),err:document.getElementById("err-series"),msg:"Select a series."},{el:document.getElementById("f-message"),err:document.getElementById("err-message"),msg:"Describe your application."}];fields.forEach(function(f){if(!f.el.value.trim()){f.err.textContent=f.msg;f.el.setAttribute("aria-invalid","true");ok=false;}else{f.err.textContent="";f.el.removeAttribute("aria-invalid");}});if(ok){status.textContent="Request received. STEP files and consultation will follow.";form.reset();}else{status.textContent="Please complete all fields.";}});
compute();
drawTeeth();
requestAnimationFrame(frame);
})();
</script>
</body>
</html>
```

FILE: llms.txt
```
# KRONOS PRECISION GEARWORKS Engineering Portal

> Manufacturer of zero-backlash strain-wave (harmonic) drives and planetary actuators for surgical and industrial robotics.

## Overview
KRONOS PRECISION GEARWORKS produces strain-wave and planetary actuators rated for continuous duty, hollow-shaft routing, and ISO 5 cleanroom assembly. Backlash is held under 0.5 arcmin across the full service life. Torsional stiffness ranges from 1.8 to 3.4 Nm/arcmin. L10 life is rated at 10,000 hours.

## Actuator Series
- KRG-14 Micro Surgical: 14 mm hollow-shaft output, continuous torque 1.4 Nm, peak torque 3.0 Nm, 180 g, torsional stiffness 1.8 Nm/arcmin.
- KRG-25 Cobot Joint: 25 mm hollow-shaft output, continuous torque 11 Nm, peak torque 24 Nm, 940 g, torsional stiffness 2.1 Nm/arcmin.
- KRG-40 Heavy Palletizer: 40 mm hollow-shaft output, continuous torque 52 Nm, peak torque 96 Nm, 3.1 kg, torsional stiffness 3.4 Nm/arcmin.

## Quality & Compliance
- ISO 9001:2015 quality management with full traceability.
- AGMA 2001 gear accuracy class A8.
- ISO 5 cleanroom-compatible fluorinated lubrication.
- L10 life testing at 10,000 hours under continuous duty.

## FAQ Highlights
- Torsional hysteresis is compensated by preloaded cross-roller bearings and closed-loop servo correction within 0.5 arcmin.
- Ratcheting torque is avoided by staying within the continuous and peak torque-speed envelope.
- Cross-roller bearings maintain stiffness in hollow-shaft outputs.
- L10 life uses Weibull distribution analysis on 10 percent of units.
- Lubrication is ISO 5 cleanroom compatible with low out-of-spec volatility.

## CAD & Consultation
STEP files are available on request. Engineering consultation covers application sizing, torque-speed envelope validation, and cleanroom packaging.

## Links
- Portal: https://www.kronosgearworks.example/
- Visualizer: https://www.kronosgearworks.example/#visualizer
- Cross-Section: https://www.kronosgearworks.example/#cross-section
- Series: https://www.kronosgearworks.example/#series
- Quality: https://www.kronosgearworks.example/#quality
- FAQ: https://www.kronosgearworks.example/#faq
- Consultation: https://www.kronosgearworks.example/#consult
```

FILE: robots.txt
```
User-agent: *
Allow: /
Disallow: /consult

Sitemap: https://www.kronosgearworks.example/sitemap.xml
```

FILE: _headers
```
# Cloudflare Pages headers
/*
  Content-Security-Policy: default-src 'self'; script-src 'sha256-__CSP_SCRIPT__'; style-src 'sha256-__CSP_STYLE__'; img-src 'self' data:; font-src 'self'; connect-src 'none'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'; upgrade-insecure-requests
  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
  Cross-Origin-Opener-Policy: same-origin
  X-Frame-Options: DENY
```