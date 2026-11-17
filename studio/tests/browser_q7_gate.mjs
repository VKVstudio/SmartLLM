import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const STUDIO_URL = process.argv[2];
const SHOTS_DIR = process.argv[3];

if (!STUDIO_URL || !SHOTS_DIR) {
  console.error('Usage: node browser_q7_gate.mjs <studio_url> <shots_dir>');
  process.exit(2);
}

function findChromeMcpEntry() {
  if (process.env.SMARTLLM_MCP_THIRD_PARTY && fs.existsSync(process.env.SMARTLLM_MCP_THIRD_PARTY)) {
    return process.env.SMARTLLM_MCP_THIRD_PARTY;
  }
  const downloads = path.join(os.homedir(), 'Downloads');
  if (fs.existsSync(downloads)) {
    for (const ent of fs.readdirSync(downloads)) {
      const cand = path.join(downloads, ent, 'resources', 'app.asar.unpacked', 'node_modules', 'chrome-devtools-mcp', 'build', 'src', 'third_party', 'index.js');
      if (fs.existsSync(cand)) return cand;
    }
  }
  return 'puppeteer';
}

const CHROME_PATH = process.env.SMARTLLM_CHROME_EXE || '/usr/bin/google-chrome-stable';
const MCP_THIRD_PARTY = findChromeMcpEntry();

const RU_LATIN_ALLOWLIST = new Set([
  'smartllm', 'studio', 'v0.0.1-beta', '0.0.1-beta', 'en', 'ru', 'aa',
  'oklch', 'wcag', 'aaa', 'csp', 'sha-256', 'seo', 'aeo', 'geo', 'serp',
  'og', 'opengraph', 'json-ld', 'json', 'faq', 'faqpage', 'html', 'html5',
  'css', 'ts', 'js', 'astro', 'vite', 'next.js', 'nextjs', 'sveltekit',
  'gsap', 'scrolltrigger', 'flip', 'svg', 'png', 'webp', 'avif', 'zip',
  'vram', 'ram', 'gib', 'mib', 'px', 'ms', 's', 'tok/s', 'tok', 'h1',
  'fsl-1.1-alv2', 'apache-2.0', 'gptbot', 'oai-searchbot', 'claudebot',
  'perplexitybot', 'google-extended', 'applebot-extended', 'ccbot',
  'bytespider', 'robots.txt', 'llms.txt', 'sitemap.xml', '_headers', 'headers',
  'hreflang', '100svh', 'svh', 'cls', 'unsafe-inline', 'coop', 'coep', 'corp', 'sse', 'z-image',
  'schema.org', 'organization', 'localbusiness', 'product',
  'softwareapplication', 'llama-server', 'stable-diffusion.cpp', 'sd-cli',
  'gguf', 'free_launch', 'pwyw', 'github', 'vkvstudio', 'vkvstudio.com',
  'donate.md', 'usdt', 'trx', 'tron', 'trc-20', 'ton', 'usdc', 'eth', 'evm',
  'btc', 'native', 'segwit', 'ethereum', 'arbitrum', 'base', 'optimism',
  'polygon', 'bsc', 'bitcoin', 'hero', 'graph', 'idle', 'free', 'pass',
  'index.html', 'specs.html', 'tokens.css', 'app.js', 'app.ts',
  'astro.config.mjs', 'zimage_prompts.json', 'project_blueprint.json',
  'brand-logo.svg', 'hero_primary.png', 'assets', 'overview', 'specifications',
  'swiss', 'international', 'typographic', 'grid', 'linear', 'dark', 'saas',
  'precision', 'nordic', 'minimal', 'brutalism', 'tactile', 'editorial',
  'serif', 'broadsheet', 'japanese', 'wabi', 'industrial', 'functional',
  'instrument', 'fintech', 'institutional', 'ledger', 'monospace', 'cli',
  'devtools', 'luxury', 'horology', 'maison', 'kinetic', 'typography',
  'poster', 'clinical', 'biotech', 'cleanroom', 'bauhaus', 'geometric',
  'modular', 'editorial-magazine', 'civic', 'gov', 'hardware', 'synth',
  'teenage', 'sustainable', 'climate', 'botanical', 'aerospace', 'mission',
  'control', 'architecture', 'monograph', 'scrollytelling', 'data',
  'journalism', 'constructivist', 'legal', 'advisory', 'chancery', 'audio',
  'dsp', 'rack', 'cartographic', 'field', 'expedition', 'museum', 'cultural',
  'exhibition', 'automotive', 'atelier', 'configurator', 'cybersecurity',
  'zero', 'trust', 'ops', 'craft', 'roastery', 'packaging', '35mm', '90mm',
  'https', 'example.org', 'smartllm-studio.example.org'
]);

async function main() {
  fs.mkdirSync(SHOTS_DIR, { recursive: true });
  const modSpec = MCP_THIRD_PARTY === 'puppeteer' ? 'puppeteer' : pathToFileURL(MCP_THIRD_PARTY).href;
  const mod = await import(modSpec);
  const puppeteer = mod.puppeteer || mod.default;
  const snapshot = mod.snapshot;

  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: true,
    pipe: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
  });

  const consoleErrors = [];
  const pageErrors = [];
  const externalRequests = [];

  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 });

    page.on('console', (msg) => {
      const t = typeof msg.type === 'function' ? msg.type() : msg.type;
      const txt = typeof msg.text === 'function' ? msg.text() : String(msg);
      if (t === 'error') consoleErrors.push(txt);
    });
    page.on('pageerror', (err) => pageErrors.push(String(err)));
    page.on('request', (req) => {
      const u = req.url();
      if (
        !u.startsWith('http://127.0.0.1') &&
        !u.startsWith('data:') &&
        !u.startsWith('blob:') &&
        !u.startsWith('about:')
      ) {
        externalRequests.push(u);
      }
    });

    await page.goto(STUDIO_URL, { waitUntil: 'networkidle0', timeout: 25000 });
    await new Promise((r) => setTimeout(r, 400));

    // 1. Dead-control test via CDP DOMDebugger.getEventListeners
    const client = await page.target().createCDPSession();
    const { result: docObj } = await client.send('Runtime.evaluate', {
      expression: 'Array.from(document.querySelectorAll("button, input, select, textarea, [role=button]"))',
      ObjectGroup: 'controls',
    });
    const props = await client.send('Runtime.getProperties', {
      objectId: docObj.objectId,
      ownProperties: true,
    });

    const unboundControls = [];
    let totalControlsChecked = 0;
    for (const prop of props.result) {
      if (!/^\d+$/.test(prop.name) || !prop.value?.objectId) continue;
      totalControlsChecked += 1;
      const oid = prop.value.objectId;
      const { listeners } = await client.send('DOMDebugger.getEventListeners', { objectId: oid });
      if (!listeners || listeners.length === 0) {
        const info = await client.send('Runtime.callFunctionOn', {
          objectId: oid,
          functionDeclaration: 'function() { return { tag: this.tagName, id: this.id, cls: this.className }; }',
          returnByValue: true,
        });
        unboundControls.push(info.result.value);
      }
    }

    // 2. Lighthouse / axe-core Accessibility & Best Practices check
    const lhRes = await snapshot(page, {
      flags: {
        onlyCategories: ['accessibility', 'best-practices'],
        formFactor: 'desktop',
        screenEmulation: { mobile: false, width: 1440, height: 900, deviceScaleFactor: 1, disabled: false },
      },
    });
    const lhr = lhRes.lhr;
    const lhA11y = Math.round((lhr.categories.accessibility?.score || 0) * 100);
    const lhBest = Math.round((lhr.categories['best-practices']?.score || 0) * 100);
    const failedA11yAudits = Object.values(lhr.audits || {})
      .filter((a) => a.score !== null && a.score < 1 && a.scoreDisplayMode === 'binary')
      .map((a) => a.id);

    // 3. Ensure RU mode and scan visible UI text nodes for unexpected Latin words
    await page.evaluate(() => {
      if (document.documentElement.lang !== 'ru') document.getElementById('btn-lang-switch').click();
    });
    await new Promise((r) => setTimeout(r, 200));

    const ruUnexpectedLatin = await page.evaluate((allowArr) => {
      const allow = new Set(allowArr);
      const bad = [];
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      let node;
      while ((node = walker.nextNode())) {
        const parent = node.parentElement;
        if (!parent) continue;
        if (['SCRIPT', 'STYLE', 'CODE', 'PRE', 'TEXTAREA', 'OPTION'].includes(parent.tagName)) continue;
        if (parent.closest('#s3-canon-gallery, #exp-canon-select, #stage-route-select, #s2-logo-grid')) continue;
        const txt = node.nodeValue.trim();
        if (!txt) continue;
        const words = txt.match(/[A-Za-z][A-Za-z0-9._+-]*/g) || [];
        for (const w of words) {
          const low = w.replace(/[.,:;!?)-]+$/, '').toLowerCase();
          if (low.length <= 2) continue;
          if (!allow.has(low)) {
            bad.push({ word: w, context: txt.slice(0, 60), id: parent.id || parent.className });
          }
        }
      }
      return bad;
    }, Array.from(RU_LATIN_ALLOWLIST));

    // 4. Capture all 54 screenshots (3 viewports x 2 languages x 9 states)
    const viewports = [
      { w: 1440, h: 900, tag: '1440x900' },
      { w: 1920, h: 1080, tag: '1920x1080' },
      { w: 1280, h: 800, tag: '1280x800' },
    ];
    const states = [
      { name: 'express', act: async (p) => { await p.evaluate(() => { document.getElementById('modal-settings').hidden = true; document.getElementById('modal-support').hidden = true; document.getElementById('mode-btn-express').click(); }); } },
      { name: 'step1', act: async (p) => { await p.evaluate(() => { document.getElementById('nav-step-1').click(); }); } },
      { name: 'step2', act: async (p) => { await p.evaluate(() => { document.getElementById('nav-step-2').click(); }); } },
      { name: 'step3', act: async (p) => { await p.evaluate(() => { document.getElementById('nav-step-3').click(); }); } },
      { name: 'step4_single', act: async (p) => { await p.evaluate(() => { document.getElementById('nav-step-4').click(); document.getElementById('s4-type-single-btn').click(); }); } },
      { name: 'step4_multi', act: async (p) => { await p.evaluate(() => { document.getElementById('nav-step-4').click(); document.getElementById('s4-type-multi-btn').click(); }); } },
      { name: 'step5', act: async (p) => { await p.evaluate(() => { document.getElementById('nav-step-5').click(); }); } },
      { name: 'settings', act: async (p) => { await p.evaluate(() => { document.getElementById('btn-open-settings').click(); }); } },
      { name: 'support', act: async (p) => { await p.evaluate(() => { document.getElementById('modal-settings').hidden = true; document.getElementById('btn-open-support').click(); }); } },
    ];

    const shotFiles = [];
    for (const lang of ['en', 'ru']) {
      await page.evaluate((targetLang) => {
        const cur = document.documentElement.lang;
        if (cur !== targetLang) document.getElementById('btn-lang-switch').click();
      }, lang);
      await new Promise((r) => setTimeout(r, 100));

      for (const vp of viewports) {
        await page.setViewport({ width: vp.w, height: vp.h, deviceScaleFactor: 1 });
        for (const st of states) {
          await st.act(page);
          await new Promise((r) => setTimeout(r, 60));
          const fname = `${lang}_${vp.tag}_${st.name}.png`;
          const fpath = path.join(SHOTS_DIR, fname);
          await page.screenshot({ path: fpath, fullPage: false });
          shotFiles.push(fname);
        }
        await page.evaluate(() => {
          document.getElementById('modal-settings').hidden = true;
          document.getElementById('modal-support').hidden = true;
        });
      }
    }

    // 5. Verify fonts loaded in browser
    const fontsLoaded = await page.evaluate(async () => {
      await document.fonts.ready;
      const families = new Set();
      for (const f of document.fonts) {
        if (f.status === 'loaded') families.add(f.family.replace(/['"]/g, ''));
      }
      return Array.from(families);
    });

    const report = {
      total_controls_checked: totalControlsChecked,
      unbound_controls_count: unboundControls.length,
      unbound_controls: unboundControls,
      console_errors_count: consoleErrors.length,
      console_errors: consoleErrors,
      page_errors_count: pageErrors.length,
      external_requests_count: externalRequests.length,
      external_requests: externalRequests,
      lighthouse_accessibility: lhA11y,
      lighthouse_best_practices: lhBest,
      failed_a11y_audits: failedA11yAudits,
      ru_unexpected_latin_count: ruUnexpectedLatin.length,
      ru_unexpected_latin: ruUnexpectedLatin.slice(0, 10),
      screenshots_count: shotFiles.length,
      fonts_loaded: fontsLoaded,
    };
    console.log(JSON.stringify(report, null, 2));
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
