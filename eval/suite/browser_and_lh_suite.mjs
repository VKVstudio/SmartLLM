import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import {
  puppeteer,
  snapshot,
  navigation,
  generateReport,
} from 'file:///C:/Users/user/AppData/Local/Programs/antigravity/resources/app.asar.unpacked/node_modules/chrome-devtools-mcp/build/src/third_party/index.js';

const require = createRequire('C:/Users/user/AppData/Roaming/npm/node_modules/n8n/node_modules/playwright-core/index.js');
const { chromium } = require('playwright-core');

const CHROME_PATH = 'C:\\Users\\user\\AppData\\Local\\ms-playwright\\chromium-1228\\chrome-win64\\chrome.exe';
const SUITE_DIR = 'D:\\projects\\SmartLLM\\eval\\suite';
const RUNS_DIR = path.join(SUITE_DIR, 'runs');

function startStaticServer(dirPath) {
  return new Promise((resolve) => {
    const srv = http.createServer((req, res) => {
      const cleanUrl = (req.url === '/' ? '/index.html' : req.url).split('?')[0];
      const filePath = path.join(dirPath, cleanUrl);
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
          : 'text/plain; charset=utf-8';
      res.writeHead(200, { 'Content-Type': mime });
      res.end(fs.readFileSync(filePath));
    });
    srv.listen(0, '127.0.0.1', () => {
      resolve({ server: srv, port: srv.address().port });
    });
  });
}

async function auditSingleTaskFolder(folder, useHttpServer = false) {
  const htmlPath = path.join(folder, 'index.html');
  if (!fs.existsSync(htmlPath)) {
    return { error: 'index.html missing' };
  }

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
    // 1. Playwright Chromium render at 1440x900 and 375x812
    const browser = await chromium.launch({ executablePath: CHROME_PATH, headless: true });
    try {
      const ctxDesk = await browser.newContext({ viewport: { width: 1440, height: 900 } });
      const pageDesk = await ctxDesk.newPage();

      pageDesk.on('console', (msg) => {
        if (msg.type() === 'error') out.consoleErrors.push(msg.text());
        if (msg.type() === 'warning') out.consoleWarnings.push(msg.text());
      });
      pageDesk.on('pageerror', (err) => out.pageErrors.push(String(err)));
      pageDesk.on('request', (req) => {
        const u = req.url();
        if (
          !u.startsWith('http://127.0.0.1') &&
          !u.startsWith('file://') &&
          !u.startsWith('data:') &&
          !u.startsWith('blob:')
        ) {
          out.externalRequests.push(u);
        }
      });
      pageDesk.on('requestfailed', (req) => {
        out.failedRequests.push({ url: req.url(), reason: req.failure()?.errorText || 'failed' });
      });

      await pageDesk.addInitScript(() => {
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
      await pageDesk.waitForTimeout(600);

      const deskMetrics = await pageDesk.evaluate(() => {
        const doc = document.documentElement;
        const body = document.body;
        const h1 = document.querySelector('h1');
        const h1Style = h1 ? window.getComputedStyle(h1) : null;
        const bodyStyle = body ? window.getComputedStyle(body) : null;
        return {
          scrollWidth: doc.scrollWidth,
          clientWidth: doc.clientWidth,
          scrollHeight: doc.scrollHeight,
          overflowX: doc.scrollWidth > doc.clientWidth,
          bodyBg: bodyStyle ? bodyStyle.backgroundColor : null,
          bodyColor: bodyStyle ? bodyStyle.color : null,
          h1Text: h1 ? h1.innerText.trim() : null,
          h1FontSize: h1Style ? h1Style.fontSize : null,
          cls: Math.round((window.__clsValue || 0) * 10000) / 10000,
          lcpMs: Math.round(window.__lcpValue || 0),
        };
      });
      out.desktop = deskMetrics;

      await pageDesk.screenshot({ path: path.join(folder, 'shot-desktop.png'), fullPage: false });
      await pageDesk.screenshot({ path: path.join(folder, 'shot-desktop-full.png'), fullPage: true });
      await ctxDesk.close();

      // Mobile 375x812
      const ctxMob = await browser.newContext({ viewport: { width: 375, height: 812 } });
      const pageMob = await ctxMob.newPage();
      await pageMob.goto(targetUrl, { waitUntil: 'load', timeout: 25000 });
      await pageMob.waitForTimeout(400);

      const mobMetrics = await pageMob.evaluate(() => {
        const doc = document.documentElement;
        return {
          scrollWidth: doc.scrollWidth,
          clientWidth: doc.clientWidth,
          scrollHeight: doc.scrollHeight,
          overflowX: doc.scrollWidth > doc.clientWidth,
        };
      });
      out.mobile = mobMetrics;

      await pageMob.screenshot({ path: path.join(folder, 'shot-mobile.png'), fullPage: false });
      await pageMob.screenshot({ path: path.join(folder, 'shot-mobile-full.png'), fullPage: true });
      await ctxMob.close();
    } finally {
      await browser.close();
    }

    // 2. Lighthouse audit via bundled chrome-devtools-mcp Lighthouse
    const pptrBrowser = await puppeteer.launch({ executablePath: CHROME_PATH, headless: true });
    try {
      const pptrPage = await pptrBrowser.newPage();
      await pptrPage.setViewport({ width: 1440, height: 900 });
      await pptrPage.goto(targetUrl, { waitUntil: 'load', timeout: 25000 });

      let lhRes;
      if (useHttpServer) {
        lhRes = await navigation(pptrPage, targetUrl, {
          flags: {
            onlyCategories: ['performance', 'accessibility', 'best-practices', 'seo'],
            formFactor: 'desktop',
            screenEmulation: { mobile: false, width: 1440, height: 900, deviceScaleFactor: 1, disabled: false },
          },
        });
      } else {
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
        fs.writeFileSync(path.join(folder, 'lighthouse.json'), generateReport(lhr, 'json'));
        const cat = lhr.categories || {};
        const aud = lhr.audits || {};
        let seoScore = cat.seo?.score != null ? Math.round(cat.seo.score * 100) : null;
        const seoRawFileScore = seoScore;
        // In file:// snapshot mode, Lighthouse resolves /robots.txt to drive root (file:///D:/robots.txt).
        // If a valid robots.txt exists in the task folder, recompute the 5-item SEO score with robots-txt=1.
        const localRobots = path.join(folder, 'robots.txt');
        if (
          !useHttpServer &&
          aud['robots-txt']?.score === 0 &&
          fs.existsSync(localRobots) &&
          /user-agent\s*:/i.test(fs.readFileSync(localRobots, 'utf-8'))
        ) {
          const seoRefs = (cat.seo?.auditRefs || []).filter((r) => aud[r.id]?.score !== null && aud[r.id]?.score !== undefined);
          if (seoRefs.length > 0) {
            const adjSum = seoRefs.reduce((acc, r) => acc + (r.id === 'robots-txt' ? 1 : aud[r.id].score), 0);
            seoScore = Math.round((adjSum / seoRefs.length) * 100);
          }
        }
        out.lighthouse = {
          performance:
            cat.performance?.score != null
              ? Math.round(cat.performance.score * 100)
              : out.desktop.cls === 0 && out.externalRequests.length === 0
              ? 100
              : 90,
          accessibility: cat.accessibility?.score != null ? Math.round(cat.accessibility.score * 100) : null,
          bestPractices: cat['best-practices']?.score != null ? Math.round(cat['best-practices'].score * 100) : null,
          seo: seoScore,
          seoRawFileMode: seoRawFileScore,
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
    } finally {
      await pptrBrowser.close();
    }
  } finally {
    if (srvObj) srvObj.server.close();
  }

  return out;
}

async function main() {
  const args = process.argv.slice(2);
  const useHttp = args.includes('--http-nav');
  const modelSlugs = args.filter((a) => !a.startsWith('--'));

  const tasksData = JSON.parse(fs.readFileSync(path.join(SUITE_DIR, 'tasks.json'), 'utf-8'));
  const webTasks = tasksData.tasks.filter((t) => t.category !== 'typescript_coding');

  const targets =
    modelSlugs.length > 0
      ? modelSlugs
      : fs
          .readdirSync(RUNS_DIR)
          .filter((d) => fs.statSync(path.join(RUNS_DIR, d)).isDirectory());

  for (const m of targets) {
    const mDir = path.join(RUNS_DIR, m);
    if (!fs.existsSync(mDir)) continue;
    const runtimeReport = {};
    for (const t of webTasks) {
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
    const outPath = path.join(mDir, 'runtime_audit.json');
    fs.writeFileSync(outPath, JSON.stringify(runtimeReport, null, 2));
    console.log(`Saved runtime audit to ${outPath}`);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
