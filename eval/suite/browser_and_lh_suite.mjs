import fs from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const SUITE_DIR = process.env.SMARTLLM_SUITE_DIR || __dirname;
const RUNS_DIR = path.join(SUITE_DIR, 'runs');

function resolveChromePath() {
  const candidates = [
    process.env.SMARTLLM_CHROME_EXE,
    '/usr/bin/google-chrome-stable',
    '/usr/bin/chromium',
    '/usr/bin/google-chrome',
    'C:\\Users\\user\\AppData\\Local\\ms-playwright\\chromium-1228\\chrome-win64\\chrome.exe',
  ].filter(Boolean);
  for (const c of candidates) {
    if (fs.existsSync(c)) return c;
  }
  return candidates[0] || '/usr/bin/google-chrome-stable';
}

function resolveMcpThirdPartyPath() {
  const candidates = [process.env.SMARTLLM_MCP_THIRD_PARTY].filter(Boolean);
  const downloads = path.join(os.homedir(), 'Downloads');
  if (fs.existsSync(downloads)) {
    for (const d of fs.readdirSync(downloads)) {
      candidates.push(path.join(downloads, d, 'resources', 'app.asar.unpacked', 'node_modules', 'chrome-devtools-mcp', 'build', 'src', 'third_party', 'index.js'));
    }
  }
  for (const c of candidates) {
    if (fs.existsSync(c)) return c;
  }
  throw new Error(
    `chrome-devtools-mcp third_party index.js not found in candidates: ${candidates.join(', ')}`
  );
}

const CHROME_PATH = resolveChromePath();

let _mcpThirdParty = null;
async function loadMcpThirdParty() {
  if (_mcpThirdParty) return _mcpThirdParty;
  const mcpPath = resolveMcpThirdPartyPath();
  _mcpThirdParty = await import(pathToFileURL(mcpPath).href);
  return _mcpThirdParty;
}

/**
 * Parse Cloudflare Pages `_headers` file so our local 127.0.0.1 HTTP server
 * serves the exact headers defined by the deliverable.
 */
export function parseLocalHeadersFile(dirPath) {
  const headersPath = path.join(dirPath, '_headers');
  const merged = {};
  if (!fs.existsSync(headersPath)) return merged;
  const raw = fs.readFileSync(headersPath, 'utf-8');
  if (raw.trim().startsWith('{')) return merged;

  let activeApplies = false;
  for (const rawLine of raw.split(/\r?\n/)) {
    const stripped = rawLine.trim();
    if (!stripped || stripped.startsWith('#')) continue;
    if (stripped.startsWith('/*') && stripped.endsWith('*/') && stripped.length > 2) {
      activeApplies = false;
      continue;
    }
    const isIndented = rawLine.startsWith(' ') || rawLine.startsWith('\t');
    if (!isIndented) {
      activeApplies =
        stripped === '/*' ||
        stripped === '/' ||
        stripped === '/index.html' ||
        stripped === '/*.html' ||
        stripped === '/index*';
      continue;
    }
    if (activeApplies && stripped.includes(':')) {
      const idx = stripped.indexOf(':');
      const k = stripped.slice(0, idx).trim();
      const v = stripped.slice(idx + 1).trim();
      if (k && v) merged[k] = v;
    }
  }
  return merged;
}

export function startStaticServer(dirPath) {
  const rootAbs = path.resolve(dirPath);
  const rootPrefix = rootAbs.endsWith(path.sep) ? rootAbs : rootAbs + path.sep;
  const customHeaders = parseLocalHeadersFile(rootAbs);

  return new Promise((resolve) => {
    const srv = http.createServer((req, res) => {
      const cleanUrl = (req.url === '/' ? '/index.html' : req.url || '/index.html').split('?')[0];
      const relUrl = decodeURIComponent(cleanUrl).replace(/^\/+/, '');
      const filePath = path.resolve(rootAbs, relUrl);
      if (filePath !== rootAbs && !filePath.startsWith(rootPrefix)) {
        res.writeHead(403);
        res.end('Forbidden');
        return;
      }
      if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
        res.writeHead(404);
        res.end('Not found');
        return;
      }
      const ext = path.extname(filePath).toLowerCase();
      const mime =
        ext === '.html'
          ? 'text/html; charset=utf-8'
          : ext === '.css'
          ? 'text/css; charset=utf-8'
          : ext === '.js' || ext === '.mjs'
          ? 'application/javascript; charset=utf-8'
          : ext === '.json'
          ? 'application/json; charset=utf-8'
          : ext === '.svg'
          ? 'image/svg+xml'
          : ext === '.png'
          ? 'image/png'
          : ext === '.webp'
          ? 'image/webp'
          : ext === '.woff2'
          ? 'font/woff2'
          : 'text/plain; charset=utf-8';
      const respHeaders = { 'Content-Type': mime, ...customHeaders };
      res.writeHead(200, respHeaders);
      res.end(fs.readFileSync(filePath));
    });
    srv.listen(0, '127.0.0.1', () => {
      resolve({ server: srv, port: srv.address().port, customHeaders });
    });
  });
}

function attachPageListeners(page, out, viewportTag) {
  const prefix = viewportTag ? `[${viewportTag}] ` : '';
  page.on('console', (msg) => {
    const type = typeof msg.type === 'function' ? msg.type() : msg.type;
    const text = typeof msg.text === 'function' ? msg.text() : String(msg);
    if (type === 'error') out.consoleErrors.push(prefix + text);
    if (type === 'warning') out.consoleWarnings.push(prefix + text);
  });
  page.on('pageerror', (err) => out.pageErrors.push(prefix + String(err)));
  page.on('request', (req) => {
    const u = req.url();
    if (
      !u.startsWith('http://127.0.0.1') &&
      !u.startsWith('http://localhost') &&
      !u.startsWith('file://') &&
      !u.startsWith('data:') &&
      !u.startsWith('blob:') &&
      !u.startsWith('about:') &&
      !u.startsWith('chrome')
    ) {
      out.externalRequests.push(prefix + u);
    }
  });
  page.on('requestfailed', (req) => {
    out.failedRequests.push({
      viewport: viewportTag || 'desktop',
      url: req.url(),
      reason: req.failure()?.errorText || 'failed',
    });
  });
}

/**
 * Evaluate DOM metrics + WCAG 2.2 SC 2.5.8 Target Size (>=24x24 CSS px)
 * and SC 2.4.11 Focus Not Obscured inside the browser page.
 * IMPORTANT: Never mutates DOM or injects fake <title>/<meta> before Lighthouse SEO.
 */
async function collectDomAndWcag22Metrics(page, includeExtended = true) {
  return page.evaluate((extended) => {
    const doc = document.documentElement;
    const body = document.body;
    const h1 = document.querySelector('h1');
    const h1Style = h1 ? window.getComputedStyle(h1) : null;
    const bodyStyle = body ? window.getComputedStyle(body) : null;
    const docStyle = doc ? window.getComputedStyle(doc) : null;

    // WCAG 2.2 SC 2.5.8 Target Size (Minimum): >= 24x24 CSS px on interactive controls
    const selector = [
      'a[href]',
      'button',
      'input:not([type="hidden"])',
      'select',
      'textarea',
      'summary',
      '[role="button"]',
      '[role="link"]',
      '[role="tab"]',
      '[role="menuitem"]',
      '[role="checkbox"]',
      '[role="radio"]',
      '[role="switch"]',
    ].join(',');

    const candidates = Array.from(document.querySelectorAll(selector));
    const violations = [];
    let interactiveCount = 0;

    for (const el of candidates) {
      const style = window.getComputedStyle(el);
      if (style.display === 'none' || style.visibility === 'hidden' || parseFloat(style.opacity || '1') === 0) {
        continue;
      }
      // Inline link inside prose sentence is exempt under WCAG 2.5.8
      if (
        el.tagName === 'A' &&
        style.display === 'inline' &&
        el.closest('p, li, dd, blockquote, td')
      ) {
        continue;
      }
      const rect = el.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) continue;
      interactiveCount += 1;
      const w = Math.round(rect.width * 100) / 100;
      const h = Math.round(rect.height * 100) / 100;
      if (w < 24 || h < 24) {
        violations.push({
          tag: el.tagName.toLowerCase(),
          id: el.id || null,
          text: (el.innerText || el.getAttribute('aria-label') || '').trim().slice(0, 40),
          width: w,
          height: h,
        });
      }
    }

    // WCAG 2.2 SC 2.4.11 Focus Not Obscured (sticky/fixed bars vs scroll-padding-top)
    let stickyHeaderHeight = 0;
    const allElements = Array.from(document.querySelectorAll('header, nav, div, section, aside'));
    for (const el of allElements) {
      const st = window.getComputedStyle(el);
      if (st.position === 'fixed' || st.position === 'sticky') {
        const r = el.getBoundingClientRect();
        if (r.height > 0 && r.height < window.innerHeight * 0.5 && r.top <= 40) {
          if (r.height > stickyHeaderHeight) stickyHeaderHeight = Math.round(r.height);
        }
      }
    }
    const scrollPaddingTopPx = docStyle ? parseFloat(docStyle.scrollPaddingTop) || 0 : 0;
    const wcag22FocusNotObscuredPassed =
      stickyHeaderHeight === 0 || scrollPaddingTopPx >= Math.min(24, stickyHeaderHeight * 0.5);

    const base = {
      scrollWidth: doc.scrollWidth,
      clientWidth: doc.clientWidth,
      scrollHeight: doc.scrollHeight,
      overflowX: doc.scrollWidth > doc.clientWidth,
      wcag22InteractiveCount: interactiveCount,
      wcag22TargetSizeViolationsCount: violations.length,
      wcag22TargetSizeViolations: violations.slice(0, 20),
      wcag22TargetSizePassed: violations.length === 0,
      wcag22StickyHeaderHeightPx: stickyHeaderHeight,
      wcag22ScrollPaddingTopPx: scrollPaddingTopPx,
      wcag22FocusNotObscuredPassed,
    };

    if (!extended) return base;

    return {
      ...base,
      titleText: document.title || '',
      hasMetaDescription: Boolean(document.querySelector('meta[name="description"][content]')),
      bodyBg: bodyStyle ? bodyStyle.backgroundColor : null,
      bodyColor: bodyStyle ? bodyStyle.color : null,
      h1Text: h1 ? h1.innerText.trim() : null,
      h1FontSize: h1Style ? h1Style.fontSize : null,
      cls: Math.round((window.__clsValue || 0) * 10000) / 10000,
      lcpMs: Math.round(window.__lcpValue || 0),
    };
  }, includeExtended);
}

export async function auditSingleTaskFolder(folder, useHttpServer = false, writeScreenshots = true) {
  const htmlPath = path.join(folder, 'index.html');
  if (!fs.existsSync(htmlPath)) {
    return { error: 'index.html missing' };
  }

  const { puppeteer, snapshot, navigation, generateReport } = await loadMcpThirdParty();

  let srvObj = null;
  let targetUrl = pathToFileURL(htmlPath).href;
  if (useHttpServer) {
    srvObj = await startStaticServer(folder);
    targetUrl = `http://127.0.0.1:${srvObj.port}/index.html`;
  }

  const out = {
    mode: useHttpServer ? 'http-navigation' : 'file-snapshot',
    desktop: {},
    mobile: {},
    consoleErrors: [],
    consoleWarnings: [],
    pageErrors: [],
    externalRequests: [],
    failedRequests: [],
    lighthouse: {},
  };

  try {
    const browser = await puppeteer.launch({
      executablePath: CHROME_PATH,
      headless: true,
      pipe: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
    });

    try {
      // 1. Desktop 1440x900 render + WCAG 2.2 audit
      const pageDesk = await browser.newPage();
      await pageDesk.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 });
      attachPageListeners(pageDesk, out, 'desktop');

      await pageDesk.evaluateOnNewDocument(() => {
        window.__clsValue = 0;
        window.__lcpValue = 0;
        try {
          new PerformanceObserver((list) => {
            for (const entry of list.getEntries()) {
              if (!entry.hadRecentInput) window.__clsValue += entry.value;
            }
          }).observe({ type: 'layout-shift', buffered: true });
          new PerformanceObserver((list) => {
            const entries = list.getEntries();
            if (entries.length) window.__lcpValue = entries[entries.length - 1].startTime;
          }).observe({ type: 'largest-contentful-paint', buffered: true });
        } catch {}
      });

      await pageDesk.goto(targetUrl, { waitUntil: 'load', timeout: 25000 });
      await new Promise((r) => setTimeout(r, 500));

      out.desktop = await collectDomAndWcag22Metrics(pageDesk, true);

      if (writeScreenshots) {
        await pageDesk.screenshot({ path: path.join(folder, 'shot-desktop.png'), fullPage: false });
        await pageDesk.screenshot({ path: path.join(folder, 'shot-desktop-full.png'), fullPage: true });
      }
      await pageDesk.close();

      // 2. Mobile 375x812 render + WCAG 2.2 audit
      const pageMob = await browser.newPage();
      await pageMob.setViewport({ width: 375, height: 812, deviceScaleFactor: 2, isMobile: true });
      attachPageListeners(pageMob, out, 'mobile');
      await pageMob.goto(targetUrl, { waitUntil: 'load', timeout: 25000 });
      await new Promise((r) => setTimeout(r, 350));

      out.mobile = await collectDomAndWcag22Metrics(pageMob, false);

      if (writeScreenshots) {
        await pageMob.screenshot({ path: path.join(folder, 'shot-mobile.png'), fullPage: false });
        await pageMob.screenshot({ path: path.join(folder, 'shot-mobile-full.png'), fullPage: true });
      }
      await pageMob.close();

      // 3. Lighthouse audit (NO fake <title>/<meta> injection and NO fabricated performance=100 in snapshot mode)
      const pptrPage = await browser.newPage();
      await pptrPage.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 });
      await pptrPage.goto(targetUrl, { waitUntil: 'load', timeout: 25000 });

      let lhRes = null;
      let usedNav = false;
      if (useHttpServer) {
        try {
          lhRes = await navigation(pptrPage, targetUrl, {
            flags: {
              onlyCategories: ['performance', 'accessibility', 'best-practices', 'seo'],
              formFactor: 'desktop',
              screenEmulation: { mobile: false, width: 1440, height: 900, deviceScaleFactor: 1, disabled: false },
            },
          });
          usedNav = true;
        } catch {
          usedNav = false;
        }
      }
      if (!lhRes) {
        lhRes = await snapshot(pptrPage, {
          flags: {
            onlyCategories: ['accessibility', 'best-practices', 'seo'],
            formFactor: 'desktop',
            screenEmulation: { mobile: false, width: 1440, height: 900, deviceScaleFactor: 1, disabled: false },
          },
        });
      }

      if (lhRes && lhRes.lhr) {
        const lhr = lhRes.lhr;
        if (writeScreenshots) {
          fs.writeFileSync(path.join(folder, 'lighthouse.json'), generateReport(lhr, 'json'));
        }
        const cat = lhr.categories || {};
        const aud = lhr.audits || {};
        const seoScore = cat.seo?.score != null ? Math.round(cat.seo.score * 100) : null;
        const perfScore = cat.performance?.score != null ? Math.round(cat.performance.score * 100) : null;
        const localRobots = path.join(folder, 'robots.txt');
        const hasLocalRobotsTxt =
          fs.existsSync(localRobots) && /user-agent\s*:/i.test(fs.readFileSync(localRobots, 'utf-8'));

        // NEW-BUG-05 fix: Never fabricate performance: 100 in snapshot mode when cat.performance is null.
        // Never inflate SEO score by injecting fake <title>/<meta> or overriding Lighthouse audits.
        out.lighthouse = {
          performance: perfScore,
          performanceMode:
            perfScore != null && usedNav ? 'lighthouse_navigation' : 'unmeasured_snapshot',
          accessibility: cat.accessibility?.score != null ? Math.round(cat.accessibility.score * 100) : null,
          bestPractices: cat['best-practices']?.score != null ? Math.round(cat['best-practices'].score * 100) : null,
          seo: seoScore,
          seoRawFileMode: seoScore,
          hasLocalRobotsTxt,
          cls:
            aud['cumulative-layout-shift']?.numericValue != null
              ? aud['cumulative-layout-shift'].numericValue
              : out.desktop.cls,
          lcpMs:
            aud['largest-contentful-paint']?.numericValue != null
              ? Math.round(aud['largest-contentful-paint'].numericValue)
              : out.desktop.lcpMs,
        };
      }
      await pptrPage.close();
    } finally {
      await browser.close();
    }
  } finally {
    if (srvObj) srvObj.server.close();
  }

  return out;
}

async function main() {
  const args = process.argv.slice(2);
  if (args[0] === '--single-folder') {
    const folder = path.resolve(args[1]);
    const useHttp = args.includes('--http-nav');
    const noShots = args.includes('--no-screenshots');
    const res = await auditSingleTaskFolder(folder, useHttp, !noShots);
    console.log(JSON.stringify(res, null, 2));
    return;
  }

  const useHttp = args.includes('--http-nav');
  const taskFilter = new Set();
  const modelSlugs = [];
  for (let i = 0; i < args.length; i += 1) {
    const a = args[i];
    if (a === '--http-nav') continue;
    if (a === '--tasks') {
      for (let j = i + 1; j < args.length && !args[j].startsWith('--'); j += 1) {
        taskFilter.add(args[j]);
        i = j;
      }
      continue;
    }
    if (!a.startsWith('--')) modelSlugs.push(a);
  }

  const tasksData = JSON.parse(fs.readFileSync(path.join(SUITE_DIR, 'tasks.json'), 'utf-8'));
  const webTasks = tasksData.tasks.filter((t) => t.category !== 'typescript_coding' && t.category !== 'copywriting');

  const targets =
    modelSlugs.length > 0
      ? modelSlugs
      : fs
          .readdirSync(RUNS_DIR)
          .filter((d) => fs.statSync(path.join(RUNS_DIR, d)).isDirectory());

  for (const m of targets) {
    const mDir = path.join(RUNS_DIR, m);
    if (!fs.existsSync(mDir)) continue;
    const outPath = path.join(mDir, 'runtime_audit.json');
    let runtimeReport = {};
    if (taskFilter.size > 0 && fs.existsSync(outPath)) {
      try {
        runtimeReport = JSON.parse(fs.readFileSync(outPath, 'utf-8')) || {};
      } catch {
        runtimeReport = {};
      }
    }
    for (const t of webTasks) {
      if (taskFilter.size > 0 && !taskFilter.has(t.id)) continue;
      const tfolder = path.join(mDir, t.id);
      if (!fs.existsSync(path.join(tfolder, 'index.html'))) continue;
      console.log(`[BROWSER+LH] Auditing ${m} / ${t.id} (${useHttp ? 'http' : 'file'})...`);
      try {
        runtimeReport[t.id] = await auditSingleTaskFolder(tfolder, useHttp);
      } catch (taskErr) {
        console.error(`[BROWSER+LH] Error on ${m} / ${t.id}:`, taskErr);
        runtimeReport[t.id] = { error: String(taskErr && taskErr.stack ? taskErr.stack : taskErr) };
      }
    }
    fs.writeFileSync(outPath, JSON.stringify(runtimeReport, null, 2));
    console.log(`Saved runtime audit to ${outPath}`);
  }
}

const isDirectRun =
  process.argv[1] && path.resolve(process.argv[1]) === path.resolve(__filename);
if (isDirectRun) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
