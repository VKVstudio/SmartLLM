FILE: index.html
```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>VKVstudio.pro — When the story changes, what should you do?</title>
<style>
  /* ============ OKLCH TOKENS ============ */
  :root{
    --bg:        oklch(95% 0.012 90);
    --surface:   oklch(97.5% 0.008 90);
    --card:      oklch(96.5% 0.014 100);
    --ink:       oklch(23% 0.03 220);
    --muted:     oklch(46% 0.02 220);
    --faint:     oklch(60% 0.015 200);
    --teal:      oklch(48% 0.09 190);
    --teal-deep: oklch(40% 0.08 190);
    --line:      oklch(87% 0.012 90);
    --line-strong:oklch(80% 0.015 90);

    --sans: system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    --mono: ui-monospace,"SF Mono","Cascadia Code","JetBrains Mono",Menlo,Consolas,monospace;

    --maxw: 1200px;
    --pad: clamp(20px, 5vw, 64px);
  }

  *{box-sizing:border-box;}
  html{-webkit-text-size-adjust:100%;}
  body{
    margin:0;
    background:var(--bg);
    color:var(--ink);
    font-family:var(--sans);
    line-height:1.55;
    -webkit-font-smoothing:antialiased;
    text-rendering:optimizeLegibility;
  }
  a{color:inherit;text-decoration:none;}
  img{display:block;max-width:100%;}
  button,input{font:inherit;color:inherit;}

  .wrap{max-width:var(--maxw);margin-inline:auto;padding-inline:var(--pad);}

  .mono{font-family:var(--mono);}
  .eyebrow{
    font-family:var(--mono);
    font-size:.7rem;
    letter-spacing:.14em;
    text-transform:uppercase;
    color:var(--teal-deep);
  }

  /* ============ HEADER ============ */
  header.site{
    border-bottom:1px solid var(--line);
    position:sticky;top:0;z-index:50;
    background:color-mix(in oklab, var(--bg) 88%, transparent);
    backdrop-filter:saturate(120%) blur(6px);
  }
  .bar{
    display:flex;align-items:center;gap:24px;
    min-height:64px;
  }
  .brand{display:flex;align-items:center;gap:10px;font-weight:700;letter-spacing:-.01em;}
  .brand .mark{width:34px;height:20px;color:var(--teal);}
  .brand b{color:var(--ink);}
  .brand span{color:var(--teal);}
  nav.main{display:flex;gap:26px;margin-left:auto;}
  nav.main a{
    font-family:var(--mono);font-size:.82rem;color:var(--muted);
    display:inline-flex;align-items:center;gap:5px;transition:color .15s;
  }
  nav.main a:hover{color:var(--ink);}
  nav.main a.active{color:var(--ink);}
  .controls{display:flex;align-items:center;gap:16px;}
  .toggle{display:inline-flex;align-items:center;gap:8px;font-family:var(--mono);font-size:.78rem;color:var(--muted);}
  .switch{
    width:16px;height:16px;border:1.5px solid var(--line-strong);border-radius:3px;background:var(--surface);
    display:inline-block;position:relative;cursor:pointer;
  }
  select.theme{
    font-family:var(--mono);font-size:.78rem;
    padding:6px 8px;border:1px solid var(--line-strong);border-radius:4px;background:var(--surface);color:var(--ink);
  }

  /* ============ HERO ============ */
  .hero{position:relative;overflow:hidden;padding-block:clamp(48px,8vw,110px);}
  .rings{position:absolute;inset:0;pointer-events:none;opacity:.5;}
  .rings svg{position:absolute;right:-6%;top:-10%;height:120%;width:auto;color:var(--teal);}
  .hero-grid{
    position:relative;display:grid;grid-template-columns:1.05fr .95fr;gap:48px;align-items:center;
  }
  .kicker{display:flex;align-items:center;gap:12px;margin-bottom:26px;}
  .kicker .dash{width:26px;height:1px;background:var(--teal);}
  h1.headline{
    font-size:clamp(2.6rem,6.4vw,4.6rem);
    line-height:.98;letter-spacing:-.035em;font-weight:800;margin:0 0 26px;
  }
  h1.headline em{font-style:normal;color:var(--teal);}
  .lede{font-size:clamp(1.02rem,1.6vw,1.2rem);color:var(--muted);max-width:46ch;margin:0 0 34px;}
  .cta-row{display:flex;flex-wrap:wrap;gap:14px;}
  .btn{
    display:inline-flex;align-items:center;gap:12px;
    font-family:var(--mono);font-size:.82rem;
    padding:15px 20px;border-radius:3px;border:1px solid transparent;cursor:pointer;
    transition:transform .12s ease,background .15s,border-color .15s;
  }
  .btn .arw{font-size:.9rem;}
  .btn-primary{background:var(--teal);color:#fff;}
  .btn-primary:hover{background:var(--teal-deep);transform:translateY(-1px);}
  .btn-ghost{background:transparent;border-color:var(--line-strong);color:var(--ink);}
  .btn-ghost:hover{border-color:var(--teal);color:var(--teal-deep);}
  .byline{margin-top:34px;font-family:var(--mono);font-size:.72rem;color:var(--faint);letter-spacing:.02em;}

  /* hero card */
  .proof-card{
    position:relative;background:var(--card);border:1px solid var(--line-strong);border-radius:4px;
    padding:30px 30px 26px;box-shadow:0 30px 60px -40px rgba(0,0,0,.35);
  }
  .proof-card::before{content:"";position:absolute;top:-1px;left:26px;right:26px;height:3px;background:var(--teal);border-radius:0 0 3px 3px;}
  .pc-head{display:flex;justify-content:space-between;align-items:center;font-family:var(--mono);font-size:.68rem;letter-spacing:.12em;text-transform:uppercase;color:var(--teal-deep);margin-bottom:22px;}
  .pc-head .dot{width:7px;height:7px;border-radius:50%;background:var(--teal);display:inline-block;margin-right:8px;vertical-align:middle;}
  .pc-head .num{color:var(--muted);}
  .proof-card h2{font-size:clamp(1.5rem,2.4vw,2rem);line-height:1.05;letter-spacing:-.02em;margin:0 0 16px;font-weight:800;}
  .proof-card p{color:var(--muted);font-size:.94rem;margin:0 0 26px;}
  .pc-foot{border-top:1px solid var(--line);padding-top:20px;display:flex;justify-content:space-between;align-items:flex-end;gap:16px;}
  .pc-foot strong{font-size:1.15rem;letter-spacing:-.01em;line-height:1.1;}
  .pc-link{font-family:var(--mono);font-size:.76rem;color:var(--teal-deep);text-decoration:underline;text-underline-offset:3px;white-space:nowrap;}
  .services-note{text-align:right;font-family:var(--mono);font-size:.7rem;color:var(--faint);margin-top:14px;}

  /* ============ MAIN GRID ============ */
  .content{padding-block:clamp(40px,6vw,80px);}
  .cols{display:grid;grid-template-columns:1fr 380px;gap:clamp(32px,5vw,72px);align-items:start;}

  .desk-head{display:flex;justify-content:space-between;align-items:baseline;border-bottom:1px solid var(--line);padding-bottom:14px;margin-bottom:22px;}
  .desk-head h2{font-size:1.15rem;margin:0;letter-spacing:-.01em;}
  .desk-head .tag{font-family:var(--mono);font-size:.72rem;color:var(--faint);letter-spacing:.1em;text-transform:uppercase;}

  .search label{display:block;font-family:var(--mono);font-size:.74rem;color:var(--muted);margin-bottom:8px;}
  .search-row{display:flex;gap:10px;}
  .search input{
    flex:1;padding:12px 14px;border:1px solid var(--line-strong);border-radius:3px;background:var(--surface);min-width:0;
  }
  .search input:focus{outline:2px solid var(--teal);outline-offset:1px;border-color:var(--teal);}
  .search button{background:var(--teal);color:#fff;border:none;padding:0 20px;border-radius:3px;font-family:var(--mono);font-size:.82rem;cursor:pointer;}
  .search button:hover{background:var(--teal-deep);}
  .hint{font-family:var(--mono);font-size:.72rem;color:var(--faint);margin-top:12px;}

  /* featured article */
  .feature{margin-top:34px;background:var(--surface);border:1px solid var(--line);border-radius:4px;overflow:hidden;}
  .thumb{position:relative;aspect-ratio:16/9;width:100%;}
  .thumb figcaption{
    position:absolute;left:16px;bottom:14px;font-family:var(--mono);font-size:.68rem;letter-spacing:.1em;text-transform:uppercase;color:#fff;
    text-shadow:0 1px 3px rgba(0,0,0,.5);
  }
  .feature-body{padding:26px 28px 28px;}
  .meta{display:flex;justify-content:space-between;gap:16px;font-family:var(--mono);font-size:.74rem;color:var(--muted);margin-bottom:16px;flex-wrap:wrap;}
  .meta .cat{color:var(--teal-deep);}
  .feature h3{font-size:clamp(1.5rem,2.6vw,2.05rem);line-height:1.08;letter-spacing:-.02em;margin:0 0 14px;font-weight:800;}
  .feature p{color:var(--muted);margin:0;}
  .feat-foot{display:flex;justify-content:space-between;align-items:center;border-top:1px solid var(--line);margin-top:22px;padding-top:18px;font-family:var(--mono);font-size:.76rem;}
  .feat-foot .read{color:var(--teal-deep);}
  .feat-foot .read:hover{text-decoration:underline;text-underline-offset:3px;}

  /* read next sidebar */
  aside.next h2{font-size:1.15rem;margin:0 0 20px;letter-spacing:-.01em;}
  .next-head{display:flex;justify-content:space-between;align-items:baseline;border-bottom:1px solid var(--line);padding-bottom:14px;margin-bottom:22px;}
  .all-link{font-family:var(--mono);font-size:.72rem;color:var(--teal-deep);letter-spacing:.06em;text-transform:uppercase;}
  .mini{background:var(--surface);border:1px solid var(--line);border-radius:4px;overflow:hidden;margin-bottom:22px;}
  .mini .thumb{aspect-ratio:16/10;}
  .mini-body{padding:18px 20px 20px;}
  .mini h3{font-size:1.12rem;line-height:1.15;letter-spacing:-.015em;margin:12px 0 10px;font-weight:800;}
  .mini p{font-size:.86rem;color:var(--muted);margin:0 0 16px;}
  .mini .read{font-family:var(--mono);font-size:.76rem;color:var(--teal-deep);}
  .mini .read:hover{text-decoration:underline;text-underline-offset:3px;}
  .footnote{font-size:.82rem;color:var(--muted);border-top:1px solid var(--line);padding-top:16px;}

  /* ============ METHOD / RULE ============ */
  section.method{border-top:1px solid var(--line);padding-block:clamp(48px,7vw,90px);}
  .method-grid{display:grid;grid-template-columns:1fr 1.15fr;gap:clamp(32px,5vw,64px);align-items:start;}
  .method h2{font-size:clamp(2rem,4.4vw,3.1rem);line-height:1.02;letter-spacing:-.03em;font-weight:800;margin:14px 0 18px;}
  .method h2 em{font-style:normal;color:var(--teal);}
  .method .sub{color:var(--muted);max-width:34ch;margin:0 0 26px;}
  .method .link{font-family:var(--mono);font-size:.82rem;color:var(--teal-deep);}
  .method .link:hover{text-decoration:underline;text-underline-offset:3px;}
  ol.rules{list-style:none;margin:0;padding:0;}
  ol.rules li{display:grid;grid-template-columns:40px 1fr;gap:18px;padding:22px 0;border-bottom:1px solid var(--line);align-items:baseline;}
  ol.rules li:first-child{border-top:1px solid var(--line);}
  ol.rules .n{font-family:var(--mono);font-size:.78rem;color:var(--faint);}
  ol.rules .t{font-weight:700;font-size:1.05rem;margin-bottom:6px;}
  ol.rules .d{color:var(--muted);font-size:.92rem;}

  /* ============ FOOTER ============ */
  footer.site{background:var(--surface);border-top:1px solid var(--line);}
  .foot{display:flex;justify-content:space-between;align-items:center;gap:24px;flex-wrap:wrap;padding-block:34px;}
  .foot .brand small{display:block;font-family:var(--mono);font-size:.7rem;color:var(--faint);font-weight:400;margin-top:4px;}
  .foot nav{display:flex;gap:26px;flex-wrap:wrap;}
  .foot nav a{font-family:var(--mono);font-size:.76rem;color:var(--muted);}
  .foot nav a:hover{color:var(--ink);}

  /* ============ RESPONSIVE ============ */
  @media (max-width:960px){
    .hero-grid{grid-template-columns:1fr;gap:40px;}
    .cols{grid-template-columns:1fr;}
    .method-grid{grid-template-columns:1fr;gap:34px;}
    nav.main{display:none;}
  }
  @media (max-width:560px){
    .bar{flex-wrap:wrap;gap:14px;min-height:auto;padding-block:14px;}
    .controls{width:100%;justify-content:space-between;}
    .services-note{text-align:left;}
    .desk-head,.next-head{flex-direction:column;gap:6px;align-items:flex-start;}
    .foot{flex-direction:column;align-items:flex-start;}
    ol.rules li{grid-template-columns:28px 1fr;gap:12px;}
  }
</style>
</head>
<body>

<!-- ============ HEADER ============ -->
<header class="site">
  <div class="wrap bar">
    <a class="brand" href="#" aria-label="VKVstudio.pro home">
      <svg class="mark" viewBox="0 0 40 24" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true">
        <path d="M2 20 L14 4 L26 20 Z"/>
        <path d="M8 20 L20 4 L32 20"/>
        <circle cx="20" cy="12" r="1.6" fill="currentColor" stroke="none"/>
      </svg>
      <span><b>VKVstudio</b>.pro</span>
    </a>
    <nav class="main" aria-label="Primary">
      <a href="#">Briefings</a>
      <a href="#">The method</a>
      <a href="#">Studio</a>
      <a href="#" class="active">Services ↗</a>
    </nav>
    <div class="controls">
      <label class="toggle"><span class="switch" role="checkbox" aria-checked="false" tabindex="0"></span>Pause motion</label>
      <label class="toggle">Theme
        <select class="theme" aria-label="Colour theme">
          <option>System</option>
          <option>Light</option>
          <option>Dark</option>
        </select>
      </label>
    </div>
  </div>
</header>

<main>
  <!-- ============ HERO ============ -->
  <section class="hero">
    <div class="rings" aria-hidden="true">
      <svg viewBox="0 0 600 600" fill="none" stroke="currentColor" stroke-width="1">
        <circle cx="300" cy="300" r="120"/>
        <circle cx="300" cy="300" r="200"/>
        <circle cx="300" cy="300" r="280"/>
        <circle cx="300" cy="300" r="360"/>
        <circle cx="180" cy="150" r="4" fill="currentColor" stroke="none"/>
        <circle cx="420" cy="120" r="4" fill="currentColor" stroke="none"/>
      </svg>
    </div>
    <div class="wrap hero-grid">
      <div class="hero-copy">
        <p class="kicker eyebrow"><span class="dash"></span>EU &amp; UK · AI / Search / Web</p>
        <h1 class="headline">When the story changes, <em>what should you do?</em></h1>
        <p class="lede">A small editorial desk for consequential digital decisions. I read the source, show what was tested, and say what remains uncertain.</p>
        <div class="cta-row">
          <a class="btn btn-primary" href="#">Read the lead briefing <span class="arw">↗</span></a>
          <a class="btn btn-ghost" href="#">How the work is checked <span class="arw">↗</span></a>
        </div>
        <p class="byline mono">Written and edited by Valerii Karpov · VKV Studio</p>
      </div>

      <div>
        <article class="proof-card">
          <div class="pc-head">
            <span><span class="dot"></span>For a real business decision</span>
            <span class="num">01 / 01</span>
          </div>
          <h2>What can your own site prove?</h2>
          <p>A briefing explains the issue. A scoped VKV Studio audit applies the same discipline to your business and gives you a plan.</p>
          <div class="pc-foot">
            <strong>Start with a<br>baseline</strong>
            <a class="pc-link" href="#">View audit scope ↗</a>
          </div>
        </article>
        <p class="services-note mono">Commercial services live on vkvstudio.com.</p>
      </div>
    </div>
  </section>

  <!-- ============ CONTENT ============ -->
  <section class="content">
    <div class="wrap cols">

      <!-- LEFT: briefing desk -->
      <div>
        <div class="desk-head">
          <h2>The briefing desk</h2>
          <span class="tag">01 / Lead story</span>
        </div>

        <form class="search" role="search" onsubmit="return false;">
          <label for="q">Search briefings</label>
          <div class="search-row">
            <input id="q" type="search" placeholder="" autocomplete="off" />
            <button type="submit">Search</button>
          </div>
          <p class="hint">Search titles, introductions and topics. An empty search shows all briefings.</p>
        </form>

        <article class="feature">
          <figure class="thumb" style="margin:0">
            <img src="https://picsum.photos/seed/vkv-agent-infrastructure-panel/900/506" alt="A brushed-metal audio patch panel with several braided cables plugged into its jacks." width="900" height="506" loading="lazy" />
            <figcaption>Signal / Evidence / Decision</figcaption>
          </figure>
          <div class="feature-body">
            <div class="meta">
              <span>Update · <span class="cat">AI agents</span></span>
              <span>Event 2026-09-10</span>
            </div>
            <h3>Agent infrastructure got easier. Delegation still needs a boundary.</h3>
            <p>OpenAI's September 10 public beta manages parts of an agent workflow. A buyer still needs to define the task, permitted actions, data boundary and acceptance test.</p>
            <div class="feat-foot">
              <span>By Valerii Karpov</span>
              <a class="read" href="#">Read the briefing ↗</a>
            </div>
          </div>
        </article>
      </div>

      <!-- RIGHT: read next -->
      <aside class="next">
        <div class="next-head">
          <h2>Read next</h2>
          <a class="all-link" href="#">All briefings ↗</a>
        </div>

        <article class="mini">
          <figure class="thumb" style="margin:0">
            <img src="https://picsum.photos/seed/vkv-conversation-desk-books/760/475" alt="Two notebooks resting on a sunlit stone desk beside a plant." width="760" height="475" loading="lazy" />
          </figure>
          <div class="mini-body">
            <div class="meta">
              <span>Update · <span class="cat">AI commerce</span></span>
              <span>Event 2026-09-16</span>
            </div>
            <h3>A conversation after an ad is still an ad.</h3>
            <p>OpenAI is testing Sponsored Agents with select US advertisers while expanding ChatGPT Ads internationally. Paid brand conversations and independent answers are different channels.</p>
            <a class="read" href="#">Read briefing ↗</a>
          </div>
        </article>

        <article class="mini">
          <figure class="thumb" style="margin:0">
            <img src="https://picsum.photos/seed/vkv-agent-infrastructure-panel/760/475" alt="Close-up of a metal patch panel with braided cables connected." width="760" height="475" loading="lazy" />
          </figure>
          <div class="mini-body">
            <div class="meta">
              <span>Update · <span class="cat">AI agents</span></span>
              <span>Event 2026-09-10</span>
            </div>
            <h3>Agent infrastructure got easier. Delegation still needs a boundary.</h3>
            <p>OpenAI's September 10 public beta manages parts of an agent workflow. A buyer still needs to define the task, permitted actions, data boundary and acceptance test.</p>
            <a class="read" href="#">Read briefing ↗</a>
          </div>
        </article>

        <article class="mini">
          <figure class="thumb" style="margin:0">
            <img src="https://picsum.photos/seed/vkv-search-loupe-cards/760/475" alt="A magnifying glass over scattered index cards on a bright desk." width="760" height="475" loading="lazy" />
          </figure>
          <div class="mini-body">
            <div class="meta">
              <span>Update · <span class="cat">AI search</span></span>
              <span>Global rollout 2026-08-31</span>
            </div>
            <h3>AI Search now has a clearer baseline. It still needs a business question.</h3>
            <p>Google expanded Search Console insights and site-owner controls on August 31. Here is what the new view can answer—and what it cannot.</p>
            <a class="read" href="#">Read briefing ↗</a>
          </div>
        </article>

        <p class="footnote">Each briefing names its sources, the status of our own checks and what the evidence cannot establish.</p>
      </aside>

    </div>
  </section>

  <!-- ============ METHOD ============ -->
  <section class="method">
    <div class="wrap method-grid">
      <div>
        <p class="eyebrow">The editorial rule</p>
        <h2>Show the work.<br><em>Then make it useful.</em></h2>
        <p class="sub">The conclusion comes early. The underlying evidence stays in reach.</p>
        <a class="link" href="#">Read the complete method ↗</a>
      </div>
      <ol class="rules">
        <li>
          <span class="n">01</span>
          <div><p class="t">Original source</p><p class="d">A primary document or a link to the work itself.</p></div>
        </li>
        <li>
          <span class="n">02</span>
          <div><p class="t">Our check</p><p class="d">A test with conditions, or a clear “not tested”.</p></div>
        </li>
        <li>
          <span class="n">03</span>
          <div><p class="t">Decision</p><p class="d">What matters now, what can wait, and for whom.</p></div>
        </li>
      </ol>
    </div>
  </section>
</main>

<!-- ============ FOOTER ============ -->
<footer class="site">
  <div class="wrap foot">
    <a class="brand" href="#">
      <svg class="mark" viewBox="0 0 40 24" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true">
        <path d="M2 20 L14 4 L26 20 Z"/><path d="M8 20 L20 4 L32 20"/>
        <circle cx="20" cy="12" r="1.6" fill="currentColor" stroke="none"/>
      </svg>
      <span><b>VKVstudio</b>.pro<small>Edited by Valerii Karpov</small></span>
    </a>
    <nav aria-label="Footer">
      <a href="#">Editorial method</a>
      <a href="#">About the studio</a>
      <a href="#">Privacy and browser storage</a>
      <a href="#">Services on vkvstudio.com ↗</a>
    </nav>
  </div>
</footer>

<script>
  // Pause-motion toggle (visual state only)
  const sw = document.querySelector('.switch');
  if(sw){
    sw.addEventListener('click', () => {
      const on = sw.getAttribute('aria-checked') === 'true';
      sw.setAttribute('aria-checked', String(!on));
      sw.style.background = !on ? 'var(--teal)' : 'var(--surface)';
    });
    sw.addEventListener('keydown', e => {
      if(e.key === ' ' || e.key === 'Enter'){ e.preventDefault(); sw.click(); }
    });
  }
</script>
</body>
</html>
```