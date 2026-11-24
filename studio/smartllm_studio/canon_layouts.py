"""Canon-specific layouts (CPU, deterministic).

Each layout canon owns its full layout stylesheet (no shared base CSS) and its own
markup partials for header, hero and footer. Header/footer are site-level partials:
rendered by one function from the same site parts for every page (only aria-current
changes). Block markup comes from the legacy renderer and is laid out by the canon CSS
(per-block variants keyed by section id).

Spec cues implemented per canon are listed in LAYOUTS[...]["spec_cues"] (from
kb/styles/canons_v2/<id>.spec.md essence) so reviews can check spec -> layout.
"""
from __future__ import annotations

import html as _html
import re
from typing import Any

LAYOUTS: dict[str, dict[str, Any]] = {
    "13_cinematic_documentary": {
        "short": "cine",
        "spec_cues": ["dark filmic chapters", "amber key light", "captioned wide stills", "filmstrip", "Literata serif"],
        "header": "overlay", "hero": "fullbleed_scrim", "footer": "credits",
    },
    "16_artisan_craft_zine": {
        "short": "zine",
        "spec_cues": ["paper", "terracotta+indigo", "Vollkorn", "ink borders", "offset shadow", "margin notes"],
        "header": "masthead", "hero": "taped_collage", "footer": "colophon",
    },
    "17_fintech_institutional": {
        "short": "ledger",
        "spec_cues": ["trust ledger", "white cards", "navy", "emerald verified", "tabular tables", "fees visible"],
        "header": "topline_bar", "hero": "split_panel_index", "footer": "dense_legal",
    },
}


def is_layout_canon(canon_id: str) -> bool:
    return str(canon_id or "") in LAYOUTS


def _root_vars(tokens_css: str) -> str:
    m = re.search(r":root\s*\{.*?\n\}", tokens_css, flags=re.S)
    return (m.group(0) + "\n") if m else ""


# ---------------------------------------------------------------- CSS ----------
_CSS_CINE = r"""
*,*::before,*::after{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:5rem}
body{margin:0;background:#0b0a09;color:#ece6dc;font-family:var(--font-sans);line-height:1.7;font-size:1.0625rem;overflow-x:clip}
img{max-width:100%;height:auto;display:block}
a{color:inherit}
.skip-link{position:absolute;left:-9999px}.skip-link:focus{left:1rem;top:1rem;z-index:99;background:#d9a441;color:#0b0a09;padding:.75rem 1rem}
.hp-trap{position:absolute!important;left:-10000px!important;width:1px;height:1px;overflow:hidden}
.container{max-width:78rem;margin:0 auto;padding:0 clamp(1.25rem,5vw,4rem)}
h1,h2,h3{font-family:var(--font-heading);font-weight:500;letter-spacing:-.01em;margin:0 0 .6em}
h2{font-size:clamp(2rem,4.2vw,3.4rem);line-height:1.05;max-width:22ch}
h3{font-size:1.25rem;line-height:1.3}
p{margin:0 0 1em;max-width:62ch;color:#cfc6b8}
.eyebrow{font-family:var(--font-mono);font-size:.75rem;letter-spacing:.28em;text-transform:uppercase;color:#d9a441}
.btn{display:inline-flex;align-items:center;min-height:48px;padding:0 1.6rem;background:#d9a441;color:#120f0a;text-decoration:none;font-weight:600;letter-spacing:.04em;border:0;cursor:pointer}
.btn-secondary{background:transparent;color:#ece6dc;box-shadow:inset 0 0 0 1px rgba(236,230,220,.5)}
.btn:focus-visible,a:focus-visible,input:focus-visible,textarea:focus-visible{outline:2px solid #d9a441;outline-offset:3px}
.cta-row{display:flex;flex-wrap:wrap;gap:1rem;margin-top:2rem}
/* header: transparent overlay over the opening still */
.site-header{position:absolute;inset:0 0 auto;z-index:20;background:linear-gradient(#0b0a09cc,#0b0a0900)}
.site-header .header-inner{display:flex;align-items:center;justify-content:space-between;gap:1rem;min-height:5.5rem}
.brand-link{display:flex;align-items:center;gap:.75rem;text-decoration:none;font-family:var(--font-heading);font-size:1.35rem;letter-spacing:.02em}
.brand-link img{width:34px;height:34px;border-radius:50%}
.nav-list{display:flex;gap:0;list-style:none;margin:0;padding:0}
.nav-list li+li{border-left:1px solid rgba(236,230,220,.25)}
.nav-list a{display:block;padding:.6rem 1.1rem;text-decoration:none;font-size:.8125rem;letter-spacing:.18em;text-transform:uppercase;color:#e7dfd2}
.nav-list a[aria-current=page]{color:#d9a441}
.nav-toggle{display:none}
.lang-switch{display:flex;gap:.25rem}.lang-switch button{background:none;border:1px solid rgba(236,230,220,.35);color:#ece6dc;min-height:40px;min-width:44px;font-family:var(--font-mono);cursor:pointer}
.lang-switch button[aria-pressed=true]{background:#d9a441;color:#0b0a09;border-color:#d9a441}
/* hero: full-bleed still, scrim, title at the lower third, timecode */
.hero-shell{position:relative;min-height:100svh;display:grid;align-items:end;overflow:hidden;isolation:isolate}
.hero-backdrop{position:absolute;inset:0;margin:0;z-index:-2}
.hero-backdrop img{width:100%;height:100%;object-fit:cover;filter:saturate(.85) contrast(1.05)}
.hero-scrim{position:absolute;inset:0;z-index:-1;background:linear-gradient(180deg,#0b0a0966 0%,#0b0a0900 35%,#0b0a09e6 82%),linear-gradient(90deg,#0b0a09b3,#0b0a0900 65%)}
.hero-copy{padding-bottom:clamp(3rem,9vh,7rem)}
.hero-copy h1{font-size:clamp(2.6rem,6.4vw,5.6rem);line-height:.98;max-width:16ch;color:#f6efe4}
.hero-copy .lead-copy{font-size:1.15rem;color:#e2d9cb;max-width:52ch}
.hero-timecode{position:absolute;right:clamp(1.25rem,5vw,4rem);bottom:2rem;font-family:var(--font-mono);font-size:.75rem;letter-spacing:.2em;color:#d9a441;writing-mode:vertical-rl}
.crumbs{display:none}
/* chapters */
.section-block{padding:clamp(4.5rem,10vw,9rem) 0;border-top:1px solid #2a2520;counter-increment:chapter}
main{counter-reset:chapter}
.section-block>.container>h2::before{content:"Chapter " counter(chapter,decimal-leading-zero);display:block;font-family:var(--font-mono);font-size:.75rem;letter-spacing:.3em;text-transform:uppercase;color:#d9a441;margin-bottom:1.2rem}
html[lang=ru] .section-block>.container>h2::before{content:"Глава " counter(chapter,decimal-leading-zero)}
/* features = chapter rows: giant numeral | text */
#features .canon-grid,#values .canon-grid,#priorities .priority-list{display:block}
#features .spec-card,#values .spec-card,.priority-item{display:grid;grid-template-columns:minmax(5rem,12rem) 1fr;gap:2rem;padding:2.2rem 0;border-bottom:1px solid #2a2520}
#features .spec-card h3,#values .spec-card h3{font-family:var(--font-heading);font-size:clamp(2.4rem,5vw,4.5rem);color:#3a332b;line-height:1;margin:0}
#features .spec-card p{font-size:1.15rem;color:#e0d7c9;margin:0;align-self:center}
.scrolly-stage{display:grid;grid-template-columns:5fr 7fr;gap:4rem}
.scrolly-step{padding:2rem 0;border-bottom:1px solid #2a2520}
.scrolly-pin{position:sticky;top:6rem;align-self:start}.scrolly-pin-hud{font-family:var(--font-mono);font-size:.8rem;color:#d9a441;margin-top:.8rem}
/* gallery = filmstrip with sprocket rail */
#gallery .canon-grid{display:grid;grid-auto-flow:column;grid-auto-columns:min(78vw,46rem);gap:1.25rem;overflow-x:auto;scroll-snap-type:x mandatory;padding:1.6rem 0;background:repeating-linear-gradient(90deg,#1b1815 0 18px,#0b0a09 18px 30px) top/100% 10px no-repeat,repeating-linear-gradient(90deg,#1b1815 0 18px,#0b0a09 18px 30px) bottom/100% 10px no-repeat}
.gallery-card{margin:0;scroll-snap-align:start}
.gallery-card img{aspect-ratio:2.39/1;object-fit:cover;width:100%}
.gallery-card figcaption{font-family:var(--font-mono);font-size:.78rem;letter-spacing:.08em;color:#a99f90;padding-top:.7rem}
.carousel-controls{display:flex;gap:.5rem}.carousel-btn{background:none;border:1px solid #514839;color:#ece6dc;min-width:48px;min-height:48px}
/* about / manifesto: centered monologue */
.manifesto-section .container,#manifesto .container{text-align:center}
.manifesto-statement,#manifesto p{font-family:var(--font-heading);font-size:clamp(1.6rem,3.4vw,2.8rem);line-height:1.25;color:#f1e9dc;max-width:30ch;margin:0 auto 1em}
#about .canon-grid{display:grid;grid-template-columns:7fr 5fr;gap:4rem;align-items:center}
#about figure{margin:0}#about img{aspect-ratio:4/5;object-fit:cover}
/* stats = huge numerals */
#stats .canon-grid{display:flex;flex-wrap:wrap;gap:0}
.stat-card{flex:1 1 14rem;padding:2rem 1.5rem;border-left:1px solid #2a2520}
.stat-value{font-family:var(--font-heading);font-size:clamp(3rem,7vw,6rem);line-height:1;color:#d9a441;margin:0 0 .5rem}
/* process = timecodes */
.timeline{list-style:none;margin:0;padding:0;display:grid;gap:0}
.timeline li{display:grid;grid-template-columns:9rem 1fr;column-gap:2rem;padding:1.6rem 0;border-bottom:1px dashed #3a332b}
.timeline .step-index{grid-row:span 2;font-family:var(--font-mono);color:#d9a441;font-size:.9rem;letter-spacing:.2em}
.timeline .step-index::before{content:"00:";}
/* team */
#team .canon-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(15rem,1fr));gap:2rem}
.team-card img,.team-photo{aspect-ratio:3/4;object-fit:cover;filter:grayscale(.6)}
/* testimonials = one centred pull-quote after another */
.review-card{max-width:48rem;margin:0 auto 3.5rem;text-align:center}
.review-card p:first-child{font-family:var(--font-heading);font-size:clamp(1.4rem,2.6vw,2.1rem);line-height:1.35;color:#f1e9dc;margin-inline:auto}
#testimonials .canon-grid{display:block}
/* pricing / faq / locations */
#pricing .canon-grid,#locations .canon-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(16rem,1fr));gap:1px;background:#2a2520}
.price-card,.location-card{background:#0b0a09;padding:2rem;display:flex;flex-direction:column;justify-content:space-between;gap:1.5rem}
.price-table-wrap{overflow-x:auto}.price-table{width:100%;border-collapse:collapse}.price-table th,.price-table td{border-bottom:1px solid #2a2520;padding:.9rem;text-align:left}
.faq-item{border-bottom:1px solid #2a2520;padding:1.5rem 0;max-width:56rem}
.faq-item h3{font-family:var(--font-sans);font-weight:600;font-size:1.1rem;color:#f1e9dc}
/* cta = letterboxed band */
.cta-banner,#cta{background:#d9a441;color:#120f0a}
#cta h2,#cta p,#cta .eyebrow{color:#120f0a}#cta h2::before{color:#120f0a}
#cta .btn{background:#0b0a09;color:#f1e9dc}
/* contact */
.contact-layout{display:grid;grid-template-columns:1.2fr 1fr;gap:4rem}
.intake-form{display:grid;gap:1.2rem;margin-top:2rem}
.intake-form label{display:block;font-family:var(--font-mono);font-size:.72rem;letter-spacing:.2em;text-transform:uppercase;color:#a99f90;margin-bottom:.4rem}
.intake-form input,.intake-form textarea{width:100%;background:transparent;border:0;border-bottom:1px solid #6b604f;color:#f1e9dc;font:inherit;min-height:48px;padding:.5rem 0}
.form-status{font-family:var(--font-mono);color:#d9a441}
.contact-details{border-left:1px solid #2a2520;padding-left:2rem}
.blog-card,.legal-copy{border-bottom:1px solid #2a2520;padding:1.5rem 0}
.marquee,.scroll-progress{display:none}
/* footer = end credits */
.site-footer{padding:6rem 0 3rem;text-align:center;border-top:1px solid #2a2520;background:#070606}
.credits{display:grid;grid-template-columns:repeat(3,1fr);gap:3rem;align-items:start}
.credits .footer-h{font-family:var(--font-mono);font-size:.7rem;letter-spacing:.32em;text-transform:uppercase;color:#d9a441}
.credits ul{list-style:none;padding:0;margin:0;display:grid;gap:.4rem}
.credits a{text-decoration:none;color:#cfc6b8}
.credits p{margin-inline:auto}
.credits-end{margin-top:4rem;font-family:var(--font-mono);font-size:.75rem;letter-spacing:.2em;color:#776d5f;display:flex;justify-content:center;gap:2rem;flex-wrap:wrap}
@media (max-width:760px){
 .nav-toggle{display:inline-flex;min-height:44px;background:none;border:1px solid #6b604f;color:#ece6dc;padding:0 1rem}
 .site-header nav{flex-basis:100%}
 .site-header .header-inner{flex-wrap:wrap}
 .nav-list{display:none;flex-direction:column;background:#0b0a09f2}
 .nav-list[data-open=true]{display:flex}.nav-list li+li{border-left:0;border-top:1px solid #2a2520}
 .credits,.contact-layout,#about .canon-grid,.scrolly-stage{grid-template-columns:1fr}
 #features .spec-card,.timeline li{grid-template-columns:1fr;gap:.6rem}
 .hero-timecode{display:none}
}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
"""

_CSS_ZINE = r"""
*,*::before,*::after{box-sizing:border-box}
body{margin:0;background:#f3eadb radial-gradient(#d9ccb6 1px,transparent 1.2px) 0 0/22px 22px;color:#2b2118;font-family:var(--font-sans);line-height:1.62;overflow-x:clip}
img{max-width:100%;height:auto;display:block}
a{color:#2f3a8f}
.skip-link{position:absolute;left:-9999px}.skip-link:focus{left:1rem;top:1rem;z-index:99;background:#2f3a8f;color:#fff;padding:.7rem 1rem}
.hp-trap{position:absolute!important;left:-10000px!important;width:1px;height:1px;overflow:hidden}
.container{max-width:70rem;margin:0 auto;padding:0 clamp(1rem,4vw,2.5rem)}
h1,h2,h3{font-family:var(--font-heading);color:#2b2118;line-height:1.1;margin:0 0 .5em}
h2{font-size:clamp(1.9rem,3.8vw,3rem);display:inline-block;background:linear-gradient(transparent 62%,#e8a07a 62% 90%,transparent 90%);padding:0 .2em}
h3{font-size:1.2rem}
p{margin:0 0 .9em;max-width:60ch}
.eyebrow{display:inline-block;font-family:var(--font-mono);font-size:.78rem;text-transform:uppercase;letter-spacing:.08em;color:#b4532a;border:1.5px dashed #b4532a;padding:.15rem .55rem;transform:rotate(-1.5deg)}
.btn{display:inline-flex;align-items:center;min-height:48px;padding:0 1.4rem;background:#b4532a;color:#fff8ee;text-decoration:none;font-weight:700;border:2px solid #2b2118;box-shadow:4px 4px 0 #2b2118;border-radius:4px;cursor:pointer}
.btn:hover{transform:translate(-1px,-1px);box-shadow:5px 5px 0 #2b2118}
.btn-secondary{background:#fff8ee;color:#2b2118}
.btn:focus-visible,a:focus-visible,input:focus-visible,textarea:focus-visible{outline:3px solid #2f3a8f;outline-offset:3px}
.cta-row{display:flex;flex-wrap:wrap;gap:1rem;margin-top:1.5rem}
/* masthead header: big centred nameplate, issue line, tab nav */
.masthead{background:#f3eadb;border-bottom:3px double #2b2118;text-align:center;padding-top:1.4rem}
.masthead .issue{font-family:var(--font-mono);font-size:.75rem;letter-spacing:.12em;text-transform:uppercase;margin:0 auto .3rem;display:flex;justify-content:center;gap:1.2rem;max-width:none}
.masthead .brand-link{display:inline-flex;align-items:center;gap:.8rem;text-decoration:none;color:#2b2118;font-family:var(--font-heading);font-size:clamp(2rem,5vw,3.4rem);font-weight:800;line-height:1}
.masthead .brand-link img{width:52px;height:52px;border-radius:50%;border:2px solid #2b2118}
.masthead nav{margin-top:1rem;border-top:1px solid #2b2118}
.nav-list{display:flex;justify-content:center;flex-wrap:wrap;list-style:none;margin:0;padding:0}
.nav-list a{display:block;padding:.7rem 1rem;text-decoration:none;color:#2b2118;font-weight:600}
.nav-list a[aria-current=page]{background:#2f3a8f;color:#fff8ee;border-radius:0 0 8px 8px}
.nav-toggle{display:none}
.lang-switch button{min-height:40px;min-width:44px;border:2px solid #2b2118;background:#fff8ee}
.crumbs{font-family:var(--font-mono);font-size:.8rem;padding-top:1rem}.crumbs ol{list-style:none;display:flex;gap:.5rem;padding:0;margin:0}.crumbs li+li::before{content:"✂ ";color:#b4532a}
/* hero: taped photo collage + margin note */
.hero-shell{padding:clamp(2.5rem,6vw,5rem) 0 clamp(3rem,6vw,5rem)}
.zine-spread{display:grid;grid-template-columns:repeat(12,1fr);gap:1.5rem;align-items:start}
.zine-title{grid-column:1/8;grid-row:1;position:relative;z-index:2;padding-top:1rem}
.zine-title h1{font-size:clamp(2.4rem,5.6vw,4.6rem);line-height:1.02;margin-top:.6rem}
.zine-title h1 span{background:#fff8ee;box-decoration-break:clone;-webkit-box-decoration-break:clone;padding:0 .15em;box-shadow:6px 6px 0 #2f3a8f33}
.taped{grid-column:6/13;grid-row:1/3;margin:3rem 0 0;background:#fff;padding:.8rem .8rem 2.6rem;border:1px solid #cdbfa8;box-shadow:8px 10px 0 #2b211822;transform:rotate(2.2deg);position:relative}
.taped::before,.taped::after{content:"";position:absolute;width:110px;height:30px;background:#e8a07acc;top:-14px}
.taped::before{left:12%;transform:rotate(-6deg)}.taped::after{right:10%;transform:rotate(5deg);background:#9aa4dbcc}
.taped img{aspect-ratio:4/3;object-fit:cover;width:100%}
.taped figcaption{font-family:var(--font-heading);font-style:italic;font-size:.95rem;padding-top:.6rem;color:#6b5a48}
.zine-note{grid-column:1/7;grid-row:2;background:#fff8ee;border:2px solid #2b2118;padding:1.4rem 1.6rem;box-shadow:6px 6px 0 #b4532a;transform:rotate(-1deg);z-index:2}
.zine-note .lead-copy{font-size:1.08rem}
/* sections */
.section-block{padding:clamp(3rem,7vw,5.5rem) 0}
.section-block:nth-of-type(even){background:#ebe0cc;border-block:2px dashed #cdb894}
/* features = staggered notes in masonry columns */
#features .canon-grid,#values .canon-grid{columns:3 16rem;column-gap:1.6rem}
#features .spec-card,#values .spec-card{break-inside:avoid;margin:0 0 1.6rem;background:#fff8ee;border:2px solid #2b2118;border-radius:6px;padding:1.3rem;box-shadow:5px 5px 0 #2f3a8f}
#features .spec-card:nth-child(3n+2){transform:rotate(1.2deg);box-shadow:5px 5px 0 #b4532a}
#features .spec-card:nth-child(3n){transform:rotate(-1deg)}
#features .spec-card h3{font-family:var(--font-mono);font-size:.78rem;color:#b4532a;letter-spacing:.1em}
.scrolly-stage{display:grid;grid-template-columns:1fr 1fr;gap:2rem}.scrolly-step{background:#fff8ee;border:2px solid #2b2118;padding:1.2rem;margin-bottom:1rem}.scrolly-pin{position:sticky;top:1rem;align-self:start;border:2px solid #2b2118;padding:.6rem;background:#fff}
/* process = numbered stamps, zig-zag */
.timeline{list-style:none;padding:0;margin:0;display:grid;gap:1.4rem;max-width:52rem}
.timeline li{position:relative;padding:1.2rem 1.4rem 1.2rem 5.2rem;background:#fff8ee;border:2px dashed #2b2118;border-radius:10px;width:88%}
.timeline li:nth-child(even){margin-left:12%}
.timeline .step-index{position:absolute;left:1rem;top:1rem;width:3.2rem;height:3.2rem;border-radius:50%;background:#2f3a8f;color:#fff8ee;display:grid;place-items:center;font-family:var(--font-heading);font-size:1.3rem;font-weight:800;transform:rotate(-8deg);margin:0}
/* gallery = polaroids scattered */
#gallery .canon-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(15rem,1fr));gap:2rem 1.5rem;padding-top:1rem}
.gallery-card{margin:0;background:#fff;padding:.7rem .7rem 1.4rem;box-shadow:3px 6px 14px #2b211833;transform:rotate(-2deg)}
.gallery-card:nth-child(even){transform:rotate(2.5deg) translateY(1rem)}
.gallery-card img{aspect-ratio:1/1;object-fit:cover}
.gallery-card figcaption{font-family:var(--font-heading);font-style:italic;font-size:.92rem;padding-top:.5rem}
.carousel-controls{display:none}
/* manifesto = handwritten margin note */
.manifesto-section .container,#manifesto .container{border-left:6px solid #b4532a;padding-left:2rem}
.manifesto-statement,#manifesto p{font-family:var(--font-heading);font-size:clamp(1.4rem,2.6vw,2rem);line-height:1.35;font-style:italic}
#about .canon-grid{display:grid;grid-template-columns:1fr 1fr;gap:2.5rem;align-items:center}
#about figure{margin:0;border:2px solid #2b2118;transform:rotate(-1.5deg);background:#fff;padding:.6rem}
/* pricing = price tags with string hole */
#pricing .canon-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(14rem,1fr));gap:1.6rem}
.price-card{position:relative;background:#fff8ee;border:2px solid #2b2118;border-radius:6px 40px 6px 6px;padding:2.2rem 1.4rem 1.4rem;display:flex;flex-direction:column;justify-content:space-between;gap:1rem}
.price-card::before{content:"";position:absolute;top:.9rem;right:1.3rem;width:14px;height:14px;border-radius:50%;border:2px solid #2b2118;background:#f3eadb}
.price-table{width:100%;border-collapse:collapse;background:#fff8ee}.price-table th,.price-table td{border:1.5px solid #2b2118;padding:.7rem}
.price-table-wrap{overflow-x:auto}
/* stats = stickers */
#stats .canon-grid{display:flex;flex-wrap:wrap;gap:1.4rem;justify-content:center}
.stat-card{width:12rem;height:12rem;border-radius:50%;background:#2f3a8f;color:#fff8ee;display:grid;place-content:center;text-align:center;padding:1.2rem;transform:rotate(-4deg)}
.stat-card:nth-child(even){background:#b4532a;transform:rotate(5deg)}
.stat-card p{color:#fff8ee;font-size:.85rem;margin:0}
.stat-value{font-family:var(--font-heading);font-size:2.4rem;font-weight:800;margin:0}
/* testimonials = cut-out quotes */
#testimonials .canon-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(17rem,1fr));gap:1.6rem}
.review-card{background:#fff;padding:1.5rem;border:1px solid #cdbfa8;clip-path:polygon(0 3%,4% 0,96% 2%,100% 0,98% 97%,100% 100%,3% 98%,0 100%)}
.review-card p:first-child{font-family:var(--font-heading);font-style:italic;font-size:1.1rem}
/* team / locations / faq */
#team .canon-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(13rem,1fr));gap:1.6rem}
.team-card{background:#fff8ee;border:2px solid #2b2118;padding:.8rem;text-align:center}
.team-card img,.team-photo{border-radius:50%;aspect-ratio:1/1;object-fit:cover;border:3px solid #b4532a}
#locations .canon-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(15rem,1fr));gap:1.2rem}
.location-card{border:2px dashed #2f3a8f;padding:1.2rem;background:#fff8ee}
.faq-item{border-bottom:2px dotted #2b2118;padding:1rem 0;max-width:50rem}
.faq-item h3::before{content:"? ";color:#b4532a;font-weight:800}
/* cta */
#cta .container,.cta-banner{background:#2f3a8f;color:#fff8ee;border:3px solid #2b2118;box-shadow:10px 10px 0 #b4532a;padding:2.4rem;border-radius:10px}
#cta h2{background:none;color:#fff8ee}#cta p{color:#e9e5ff}
/* contact */
.contact-layout{display:grid;grid-template-columns:1.3fr 1fr;gap:2.5rem;align-items:start}
.intake-form{display:grid;gap:1rem;background:#fff8ee;border:2px solid #2b2118;padding:1.5rem;box-shadow:6px 6px 0 #2f3a8f;margin-top:1rem}
.intake-form label{font-weight:700;display:block;margin-bottom:.25rem}
.intake-form input,.intake-form textarea{width:100%;min-height:48px;border:2px solid #2b2118;border-radius:4px;background:#fff;font:inherit;padding:.5rem .7rem}
.contact-details{background:#ebe0cc;border:2px dashed #2b2118;padding:1.2rem}
.blog-card{background:#fff8ee;border:2px solid #2b2118;padding:1.2rem;margin-bottom:1rem}
.marquee,.scroll-progress{display:none}
/* footer = colophon */
.site-footer{background:#2b2118;color:#f3eadb;padding:3.5rem 0 2rem;text-align:center;margin-top:3rem}
.site-footer a{color:#f3c9a8}
.colophon .brand-link{font-family:var(--font-heading);font-size:2rem;text-decoration:none;color:#f3eadb;display:inline-flex;gap:.6rem;align-items:center}
.colophon .brand-link img{width:40px;height:40px;border-radius:50%}
.colophon ul{list-style:none;padding:0;margin:1.2rem 0;display:flex;justify-content:center;flex-wrap:wrap;gap:.2rem 1.4rem}
.colophon .footer-h{display:none}
.colophon p{margin-inline:auto}
.colophon .handmade{font-family:var(--font-heading);font-style:italic;color:#e8a07a;font-size:1.1rem}
.colophon .footer-bottom{border-top:1px dashed #6b5a48;margin-top:1.5rem;padding-top:1rem;font-size:.85rem;display:flex;justify-content:center;gap:1.5rem;flex-wrap:wrap}
@media (max-width:760px){
 .zine-spread{display:block}.taped{margin:1.5rem .4rem;transform:rotate(1deg)}.zine-note{transform:none}
 .contact-layout,#about .canon-grid,.scrolly-stage{grid-template-columns:1fr}
 .timeline li,.timeline li:nth-child(even){width:100%;margin-left:0}
 .nav-toggle{display:inline-flex;min-height:44px;margin:.6rem auto;border:2px solid #2b2118;background:#fff8ee;padding:0 1rem}
 .nav-list{display:none;flex-direction:column}.nav-list[data-open=true]{display:flex}
}
@media (prefers-reduced-motion:reduce){.btn:hover{transform:none}}
"""

_CSS_LEDGER = r"""
*,*::before,*::after{box-sizing:border-box}
body{margin:0;background:#f6f8fb;color:#0f1b33;font-family:var(--font-sans);font-size:1rem;line-height:1.55;font-variant-numeric:tabular-nums;overflow-x:clip}
img{max-width:100%;height:auto;display:block}
a{color:#1b3a8a}
.skip-link{position:absolute;left:-9999px}.skip-link:focus{left:1rem;top:1rem;z-index:99;background:#0f1b33;color:#fff;padding:.7rem 1rem}
.hp-trap{position:absolute!important;left:-10000px!important;width:1px;height:1px;overflow:hidden}
.container{max-width:76rem;margin:0 auto;padding:0 clamp(1rem,3vw,2rem)}
h1,h2,h3{font-family:var(--font-heading);color:#0b1630;letter-spacing:-.02em;margin:0 0 .5em;font-weight:650}
h2{font-size:clamp(1.6rem,2.6vw,2.2rem);line-height:1.15}
h3{font-size:1.02rem;line-height:1.35}
p{margin:0 0 .8em;max-width:66ch;color:#3b4863}
.eyebrow{font-size:.72rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#0f7a55;display:flex;align-items:center;gap:.45rem}
.eyebrow::before{content:"";width:.5rem;height:.5rem;border-radius:50%;background:#12a26f}
.btn{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:0 1.2rem;background:#12306e;color:#fff;text-decoration:none;font-weight:600;border-radius:6px;border:1px solid #12306e;font-size:.95rem;cursor:pointer}
.btn-secondary{background:#fff;color:#12306e;border-color:#c9d3e3}
.btn:focus-visible,a:focus-visible,input:focus-visible,textarea:focus-visible{outline:2px solid #12a26f;outline-offset:2px}
.cta-row{display:flex;flex-wrap:wrap;gap:.75rem;margin-top:1.4rem}
/* header: compliance topline + white bar with action */
.site-header{position:sticky;top:0;z-index:30;background:#fff;border-bottom:1px solid #dfe5ee}
.topline{background:#0b1630;color:#c6d1e6;font-size:.75rem}
.topline .container{display:flex;justify-content:space-between;align-items:center;min-height:2rem;gap:1rem}
.topline span::before{content:"✓ ";color:#3fd39b}
.header-inner{display:flex;align-items:center;gap:2rem;min-height:4rem}
.brand-link{display:flex;align-items:center;gap:.6rem;text-decoration:none;color:#0b1630;font-weight:750;font-family:var(--font-heading);font-size:1.15rem}
.brand-link img{width:30px;height:30px;border-radius:6px}
.site-header nav{flex:1}
.nav-list{display:flex;gap:.25rem;list-style:none;margin:0;padding:0}
.nav-list a{display:block;padding:.55rem .75rem;text-decoration:none;color:#3b4863;font-size:.9rem;font-weight:550;border-bottom:2px solid transparent}
.nav-list a[aria-current=page]{color:#0b1630;border-bottom-color:#12a26f}
.header-cta{min-height:40px}
.nav-toggle{display:none}
.lang-switch button{min-height:36px;min-width:44px;border:1px solid #c9d3e3;background:#fff;color:#0b1630}
.crumbs{font-size:.8rem;padding-top:1rem;color:#6a7690}.crumbs ol{display:flex;gap:.4rem;list-style:none;padding:0;margin:0}.crumbs li+li::before{content:"/ ";color:#9aa6bd}
/* hero: split text | framed panel, then on-this-page index */
.hero-shell{background:#fff;border-bottom:1px solid #dfe5ee;padding:clamp(2.5rem,5vw,4.5rem) 0 0}
.hero-grid{display:grid;grid-template-columns:minmax(0,6fr) minmax(0,5fr);gap:clamp(2rem,4vw,4rem);align-items:center}
.hero-grid h1{font-size:clamp(2.1rem,4vw,3.4rem);line-height:1.08}
.hero-grid .lead-copy{font-size:1.1rem}
.hero-panel{margin:0;border:1px solid #dfe5ee;border-radius:10px;background:#f6f8fb;padding:.6rem;box-shadow:0 1px 0 #dfe5ee,0 18px 40px -24px #0b163040}
.hero-panel img{border-radius:6px;aspect-ratio:4/3;object-fit:cover;width:100%}
.panel-meta{display:flex;justify-content:space-between;font-size:.75rem;color:#6a7690;padding:.55rem .3rem 0}
.panel-meta b{color:#0f7a55;font-weight:700}
.page-index{display:grid;grid-template-columns:repeat(auto-fit,minmax(10rem,1fr));margin-top:clamp(2rem,4vw,3.5rem);border-top:1px solid #dfe5ee}
.page-index a{display:flex;gap:.6rem;padding:1rem .4rem;text-decoration:none;color:#0b1630;font-size:.85rem;font-weight:600;border-right:1px solid #dfe5ee}
.page-index a span{color:#9aa6bd;font-weight:500}
/* sections */
.section-block{padding:clamp(3rem,6vw,5rem) 0;border-bottom:1px solid #dfe5ee}
.section-block:nth-of-type(odd){background:#fff}
/* features = hairline matrix */
#features .canon-grid,#values .canon-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(15rem,1fr));border-top:1px solid #dfe5ee;border-left:1px solid #dfe5ee}
#features .spec-card,#values .spec-card{padding:1.5rem;border-right:1px solid #dfe5ee;border-bottom:1px solid #dfe5ee;background:#fff}
#features .spec-card h3{font-size:.72rem;letter-spacing:.1em;color:#6a7690;font-weight:700}
.scrolly-stage{display:grid;grid-template-columns:1fr 1fr;gap:2.5rem}.scrolly-step{border-left:2px solid #dfe5ee;padding:1rem 1.2rem}.scrolly-step.is-active{border-left-color:#12a26f}.scrolly-pin{position:sticky;top:7rem;align-self:start;border:1px solid #dfe5ee;border-radius:10px;padding:.5rem;background:#fff}
/* pricing = comparison columns, middle plan highlighted */
#pricing .canon-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(15rem,1fr));gap:0;border:1px solid #dfe5ee;border-radius:10px;overflow:hidden;background:#fff}
.price-card{padding:1.8rem;border-right:1px solid #dfe5ee;display:flex;flex-direction:column;justify-content:space-between;gap:1.2rem}
.price-card:nth-child(2){background:#0b1630;color:#fff}.price-card:nth-child(2) h3,.price-card:nth-child(2) p{color:#e6ecf7}.price-card:nth-child(2) .btn{background:#12a26f;border-color:#12a26f;color:#fff}
.price-table-wrap{overflow-x:auto;border:1px solid #dfe5ee;border-radius:10px;background:#fff}
.price-table{width:100%;border-collapse:collapse;font-size:.92rem}.price-table th{background:#f0f3f8;text-align:left}.price-table th,.price-table td{padding:.8rem 1rem;border-bottom:1px solid #dfe5ee}
/* stats = KPI strip */
#stats .canon-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(11rem,1fr));background:#0b1630;border-radius:10px}
.stat-card{padding:1.6rem;border-right:1px solid #22325a}
.stat-card p{color:#aab6cf;font-size:.85rem;margin:0}
.stat-value{font-size:2.2rem;font-weight:700;color:#3fd39b!important;font-family:var(--font-mono)}
/* process = horizontal stepper */
.timeline{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(12rem,1fr));gap:1.5rem;counter-reset:s}
.timeline li{position:relative;padding-top:2.6rem}
.timeline li::before{content:"";position:absolute;top:.95rem;left:2.2rem;right:-1.5rem;height:1px;background:#c9d3e3}
.timeline li:last-child::before{display:none}
.timeline .step-index{position:absolute;top:0;left:0;width:2rem;height:2rem;border-radius:50%;border:1px solid #12306e;display:grid;place-items:center;font-size:.8rem;font-weight:700;color:#12306e;background:#fff;margin:0}
/* faq = sticky heading left, answers right */
#faq .container{display:grid;grid-template-columns:minmax(0,4fr) minmax(0,8fr);gap:3rem;align-items:start}
#faq h2{position:sticky;top:7rem}
#faq .faq-item{grid-column:2;border-bottom:1px solid #dfe5ee;padding:1rem 0}
#faq .faq-item:first-of-type{grid-row:1}
#faq .faq-item h3{font-size:1rem}
/* testimonials / team / locations / gallery */
#testimonials .canon-grid,#team .canon-grid,#locations .canon-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(16rem,1fr));gap:1rem}
.review-card,.team-card,.location-card,.blog-card{background:#fff;border:1px solid #dfe5ee;border-radius:10px;padding:1.4rem}
.review-card .eyebrow{color:#3b4863}.review-card .eyebrow::before{background:#c9d3e3}
.team-card img,.team-photo{border-radius:8px;aspect-ratio:1/1;object-fit:cover}
#gallery .canon-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(14rem,1fr));gap:1rem}
.gallery-card{margin:0;background:#fff;border:1px solid #dfe5ee;border-radius:10px;overflow:hidden}.gallery-card img{aspect-ratio:16/10;object-fit:cover}.gallery-card figcaption{padding:.7rem 1rem;font-size:.82rem;color:#6a7690}
.carousel-controls{display:none}
#about .canon-grid{display:grid;grid-template-columns:1fr 1fr;gap:2.5rem;align-items:center}#about figure{margin:0}#about img{border-radius:10px}
.manifesto-statement,#manifesto p{font-size:1.25rem;color:#0b1630;border-left:3px solid #12a26f;padding-left:1.2rem}
/* cta */
#cta{background:#12306e!important}
#cta h2,#cta p{color:#fff}#cta .eyebrow{color:#3fd39b}
#cta .btn{background:#fff;color:#12306e;border-color:#fff}
/* contact */
.contact-layout{display:grid;grid-template-columns:7fr 5fr;gap:2.5rem;align-items:start}
.intake-form{display:grid;grid-template-columns:1fr 1fr;gap:1rem;background:#fff;border:1px solid #dfe5ee;border-radius:10px;padding:1.5rem;margin-top:1.2rem}
.intake-form>div:nth-of-type(3),.intake-form>button,.intake-form>.form-status{grid-column:1/-1}
.intake-form label{display:block;font-size:.78rem;font-weight:650;color:#3b4863;margin-bottom:.3rem}
.intake-form input,.intake-form textarea{width:100%;min-height:44px;border:1px solid #c9d3e3;border-radius:6px;font:inherit;padding:.5rem .7rem;background:#fbfcfe}
.contact-details{background:#fff;border:1px solid #dfe5ee;border-radius:10px;padding:1.4rem}
.legal-copy{max-width:70ch}
.marquee,.scroll-progress{display:none}
/* footer = dense 4-col + legal row */
.site-footer{background:#0b1630;color:#aab6cf;padding:3rem 0 1.5rem;font-size:.88rem}
.site-footer a{color:#dbe3f2;text-decoration:none}
.footer-ledger{display:grid;grid-template-columns:2fr 1fr 1fr 1.4fr;gap:2rem}
.footer-ledger .footer-h{font-size:.7rem;letter-spacing:.12em;text-transform:uppercase;color:#6f7fa3;font-weight:700}
.footer-ledger ul{list-style:none;padding:0;margin:0;display:grid;gap:.35rem}
.footer-ledger .brand-link{color:#fff}
.footer-ledger p{color:#aab6cf}
.footer-trust{border:1px solid #22325a;border-radius:8px;padding:1rem}
.footer-trust p::before{content:"✓ ";color:#3fd39b}
.site-footer .footer-bottom{display:flex;justify-content:space-between;flex-wrap:wrap;gap:1rem;border-top:1px solid #22325a;margin-top:2rem;padding-top:1rem;font-size:.78rem}
@media (max-width:860px){
 .hero-grid,.contact-layout,#faq .container,#about .canon-grid,.scrolly-stage{grid-template-columns:1fr}
 #faq h2{position:static}#faq .faq-item{grid-column:1}
 .footer-ledger{grid-template-columns:1fr 1fr}
 .header-cta{display:none}
 .nav-toggle{display:inline-flex;margin-left:auto;min-height:44px;border:1px solid #c9d3e3;background:#fff;padding:0 .9rem;border-radius:6px}
 .site-header nav{flex-basis:100%;order:3}.header-inner{flex-wrap:wrap;gap:.5rem}
 .nav-list{display:none;flex-direction:column}.nav-list[data-open=true]{display:flex}
 .intake-form{grid-template-columns:1fr}
 .timeline li::before{display:none}
}
"""

_CSS = {"13_cinematic_documentary": _CSS_CINE, "16_artisan_craft_zine": _CSS_ZINE, "17_fintech_institutional": _CSS_LEDGER}


# Baseline behaviour every layout canon inherits (placed before the canon CSS so a canon can override it):
# no horizontal page scroll, 44px tap targets, reduced-motion / reduced-transparency respect.
_SHARED_BASE_CSS = (
    "html, body { overflow-x: clip; }\n"
    ".btn, input, select, textarea { min-height: 44px; }\n"
    "@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: 0.01ms !important; "
    "animation-iteration-count: 1 !important; transition-duration: 0.01ms !important; scroll-behavior: auto !important; } }\n"
    "@media (prefers-reduced-transparency: reduce) { * { backdrop-filter: none !important; -webkit-backdrop-filter: none !important; } }\n"
)
# Same below-the-fold rendering hint the shared layout emits (PageSpeed; keeps the phase-2 gate).
_SHARED_PERF_CSS = 'html[data-motion="reduced_motion_instant"] .section-block:not(#hero) { content-visibility: auto; contain-intrinsic-size: auto 600px; }\n'


def canon_layout_css(canon_id: str, tokens_css: str, font_css: str = "") -> str:
    """Full stylesheet for a layout canon: fonts + canon :root vars + canon-owned layout."""
    return (font_css + "\n" if font_css else "") + _root_vars(tokens_css) + _SHARED_BASE_CSS + _CSS[canon_id].strip() + "\n" + _SHARED_PERF_CSS


# ------------------------------------------------------------- markup ---------
def _grab(pattern: str, text: str, default: str = "") -> str:
    m = re.search(pattern, text, flags=re.S)
    return m.group(1) if m else default


def _site_parts(doc: str) -> dict[str, str]:
    header = _grab(r'(<header class="site-header">.*?</header>)', doc)
    footer = _grab(r'(<footer class="site-footer">.*?</footer>)', doc)
    return {
        "header": header,
        "footer": footer,
        "brand": _grab(r'(<a class="brand-link".*?</a>)', header),
        "toggle": _grab(r'(<button class="btn btn-secondary nav-toggle".*?</button>)', header),
        "nav_ul": _grab(r'(<ul class="nav-list".*?</ul>)', header),
        "lang": _grab(r'(<div class="lang-switch".*?</div>)', header),
        "f_brand": _grab(r'(<div class="footer-brand">.*?</div>)', footer),
        "f_brand_p": _grab(r'<div class="footer-brand">.*?</a>\s*(<p.*?</p>)', footer),
        "f_nav": _grab(r'(<nav aria-label="Footer">.*?</nav>)', footer),
        "f_nav_ul": _grab(r'(<ul class="footer-nav">.*?</ul>)', footer),
        "f_contacts": _grab(r'(<div class="footer-contacts">.*?</div>)\s*</div>', footer),
        "f_bottom": _grab(r'(<div class="container footer-bottom">.*?</div>)', footer),
    }


def _contact_href(nav_ul: str) -> tuple[str, str]:
    m = re.search(r'<a href="(contact\.html)"[^>]*>(.*?)</a>', nav_ul, flags=re.S)
    return (m.group(1), re.sub(r"<[^>]+>", "", m.group(2))) if m else ("", "")


def render_header(canon_id: str, parts: dict[str, str], page_label: str, page_no: int, lang: str) -> str:
    kind = LAYOUTS[canon_id]["header"]
    brand, toggle, nav_ul, lang_sw = parts["brand"], parts["toggle"], parts["nav_ul"], parts["lang"]
    toggle = toggle.replace('class="btn btn-secondary nav-toggle"', 'class="nav-toggle"')
    nav = f'<nav aria-label="Primary">\n        {nav_ul}\n      </nav>'
    if kind == "overlay":
        return (f'<header class="site-header">\n    <div class="container header-inner">\n      {brand}\n      {toggle}\n      {nav}\n      {lang_sw}\n    </div>\n  </header>')
    if kind == "masthead":
        issue = ("Выпуск" if lang == "ru" else "Issue") + f" № {page_no:02d}"
        return (f'<header class="site-header masthead">\n    <div class="container">\n      <p class="issue"><span>{issue}</span><span>{_html.escape(page_label)}</span></p>\n'
                f'      {brand}\n      {toggle}\n      {nav}\n      {lang_sw}\n    </div>\n  </header>')
    href, label = _contact_href(nav_ul)
    cta = f'<a class="btn header-cta" href="{href}">{_html.escape(label)}</a>' if href else ""
    eyebrow = parts.get("topline", "")
    return (f'<header class="site-header">\n    <div class="topline"><div class="container"><span>{_html.escape(eyebrow)}</span>{lang_sw}</div></div>\n'
            f'    <div class="container header-inner">\n      {brand}\n      {toggle}\n      {nav}\n      {cta}\n    </div>\n  </header>')


def render_footer(canon_id: str, parts: dict[str, str], lang: str) -> str:
    kind = LAYOUTS[canon_id]["footer"]
    if kind == "credits":
        return (f'<footer class="site-footer">\n    <div class="container credits">\n      {parts["f_brand"]}\n      {parts["f_nav"]}\n      {parts["f_contacts"]}\n    </div>\n'
                f'    <div class="container credits-end">{re.sub(r"^<div[^>]*>|</div>$", "", parts["f_bottom"])}</div>\n  </footer>')
    if kind == "colophon":
        hand = "Сделано руками в мастерской" if lang == "ru" else "Made by hand in the workshop"
        contacts_inner = re.sub(r'<p class="footer-h"[^>]*>.*?</p>', "", parts["f_contacts"], flags=re.S)
        return (f'<footer class="site-footer">\n    <div class="container colophon">\n      {_grab(r"(<a class=\"brand-link\".*?</a>)", parts["f_brand"])}\n'
                f'      <p class="handmade">{hand}</p>\n      {parts["f_brand_p"]}\n      <nav aria-label="Footer">{parts["f_nav_ul"]}</nav>\n      {contacts_inner}\n'
                f'      {parts["f_bottom"].replace("container footer-bottom", "footer-bottom")}\n    </div>\n  </footer>')
    trust = parts.get("trust", "")
    trust_html = f'<div class="footer-trust">{trust}</div>' if trust else "<div></div>"
    return (f'<footer class="site-footer">\n    <div class="container footer-ledger">\n      {parts["f_brand"]}\n      {parts["f_nav"]}\n      {parts["f_contacts"]}\n      {trust_html}\n    </div>\n'
            f'    {parts["f_bottom"]}\n  </footer>')


def _hero_parts(hero: str) -> dict[str, str]:
    return {
        "open": _grab(r'(<section class="hero-shell[^"]*" id="hero")', hero),
        "eyebrow": _grab(r'(<p class="eyebrow".*?</p>)', hero),
        "h1_attrs": _grab(r"<h1([^>]*)>", hero),
        "h1": _grab(r"<h1[^>]*>(.*?)</h1>", hero),
        "lead": _grab(r'(<p class="lead-copy".*?</p>)', hero),
        "cta": _grab(r'(<div class="cta-row">.*?</div>)', hero),
        "img": _grab(r'(<img [^>]*>)', hero),
        "alt": _html.unescape(_grab(r'<img [^>]*alt="([^"]*)"', hero)),
    }


def render_hero(canon_id: str, hero: str, page_no: int, page_label: str, section_index: list[tuple[str, str]]) -> str:
    p = _hero_parts(hero)
    if not p["h1"]:
        return hero
    kind = LAYOUTS[canon_id]["hero"]
    h1 = f'<h1{p["h1_attrs"]}>{p["h1"]}</h1>'
    if kind == "fullbleed_scrim":
        return (f'<section class="hero-shell" id="hero" data-variant="cine_fullbleed">\n      <figure class="hero-backdrop">{p["img"]}</figure>\n      <div class="hero-scrim" aria-hidden="true"></div>\n'
                f'      <div class="container hero-copy">\n        {p["eyebrow"]}\n        {h1}\n        {p["lead"]}\n        {p["cta"]}\n      </div>\n'
                f'      <p class="hero-timecode" aria-hidden="true">SC {page_no:02d} · {_html.escape(page_label.upper())}</p>\n    </section>')
    if kind == "taped_collage":
        h1z = f'<h1{p["h1_attrs"]}><span>{p["h1"]}</span></h1>'
        return (f'<section class="hero-shell" id="hero" data-variant="zine_collage">\n      <div class="container zine-spread">\n'
                f'        <div class="zine-title">{p["eyebrow"]}\n          {h1z}</div>\n'
                f'        <figure class="taped">{p["img"]}<figcaption>{_html.escape(p["alt"])}</figcaption></figure>\n'
                f'        <div class="zine-note">{p["lead"]}\n          {p["cta"]}</div>\n      </div>\n    </section>')
    idx = "".join(f'<a href="#{sid}"><span>{i:02d}</span>{_html.escape(lbl)}</a>' for i, (sid, lbl) in enumerate(section_index[:6], 1))
    return (f'<section class="hero-shell" id="hero" data-variant="ledger_split">\n      <div class="container hero-grid">\n'
            f'        <div class="hero-lead">{p["eyebrow"]}\n          {h1}\n          {p["lead"]}\n          {p["cta"]}</div>\n'
            f'        <figure class="hero-panel">{p["img"]}<figcaption class="panel-meta"><span>{_html.escape(page_label)}</span><b>●</b></figcaption></figure>\n      </div>\n'
            + (f'      <nav class="container page-index" aria-label="On this page">{idx}</nav>\n' if idx else "")
            + '    </section>')


def apply_layout(doc: str, canon_id: str, *, slug: str, page_no: int, page_label: str, lang: str, extras: dict[str, str] | None = None) -> str:
    """Replace legacy header/hero/footer with the canon's partials. Idempotent per page."""
    if not is_layout_canon(canon_id):
        return doc
    parts = _site_parts(doc)
    if not parts["header"] or not parts["footer"]:
        return doc
    parts.update(extras or {})
    section_index = []
    for sid, h2 in re.findall(r'<section class="[^"]*section-block[^"]*" id="([a-z_]+)"[^>]*>\s*<div class="container[^"]*">\s*(?:<div[^>]*>\s*)?<h2[^>]*>(.*?)</h2>', doc, flags=re.S):
        if sid in ("cta",):
            continue
        lbl = _html.unescape(re.sub(r"<[^>]+>", "", h2)).strip()
        if len(lbl) > 42:
            lbl = lbl[:42].rsplit(" ", 1)[0].rstrip(" ,;:-") + "…"
        section_index.append((sid, lbl))
    hero = _grab(r'(<section class="hero-shell.*?</section>)', doc)
    out = doc.replace(parts["header"], render_header(canon_id, parts, page_label, page_no, lang), 1)
    out = out.replace(parts["footer"], render_footer(canon_id, parts, lang), 1)
    if hero:
        out = out.replace(hero, render_hero(canon_id, hero, page_no, page_label, section_index), 1)
    return out.replace('data-canon="', f'data-layout="{LAYOUTS[canon_id]["short"]}" data-canon="', 1)


# ------------------------------------------------------------ metrics ---------
def _decls(css: str) -> list[str]:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"@font-face\s*\{[^}]*\}", "", css)
    css = re.sub(r":root\s*\{[^}]*\}", "", css)
    out = []
    for body in re.findall(r"\{([^{}]*)\}", css):
        for d in body.split(";"):
            d = re.sub(r"\s+", " ", d).strip().lower()
            if ":" in d:
                out.append(d)
    return out


def _rules(css: str) -> set[str]:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"@font-face\s*\{[^}]*\}", "", css)
    css = re.sub(r":root\s*\{[^}]*\}", "", css)
    res = set()
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        decl = ";".join(sorted(re.sub(r"\s+", " ", d).strip().lower() for d in body.split(";") if d.strip()))
        res.add(re.sub(r"\s+", " ", sel).strip().lower() + "{" + decl + "}")
    return res


def css_overlap(a: str, b: str) -> dict[str, float]:
    """Two views of sameness: identical rules (selector+declarations), and identical declarations."""
    ra, rb = _rules(a), _rules(b)
    da, db = set(_decls(a)), set(_decls(b))
    rule = len(ra & rb) / max(1, min(len(ra), len(rb)))
    decl = len(da & db) / max(1, len(da | db))
    return {"rule_overlap": round(rule, 3), "decl_jaccard": round(decl, 3)}
