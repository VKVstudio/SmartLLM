import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { chromium } = require('C:\\Users\\user\\AppData\\Local\\npm-cache\\_npx\\705bc6b22212b352\\node_modules\\playwright-core');

const CHROME_PATH = 'C:\\Users\\user\\AppData\\Local\\ms-playwright\\chromium-1228\\chrome-win64\\chrome.exe';
const LH_CLI = 'C:\\Users\\user\\AppData\\Local\\npm-cache\\_npx\\8003d8991b0d346b\\node_modules\\lighthouse\\cli\\index.js';
const NODE_EXE = 'C:\\Program Files\\nodejs\\node.exe';
const BASE_DIR = 'D:\\projects\\SmartLLM\\eval\\round2';
const SLUGS = ['qwen3.8-no-think', 'qwen3.8-think-8k', 'qwen3.6-35b-a3b'];
const TASKS = ['t1', 't2', 't3'];

function startStaticServer(rootDir) {
  const requestedUrls = [];
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const urlPath = (req.url || '/').split('?')[0];
      requestedUrls.push(urlPath);
      const rel = urlPath === '/' ? 'index.html' : urlPath.replace(/^\/+/, '');
      const filePath = path.join(rootDir, rel);
      if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
        res.writeHead(404);
        res.end('Not found');
        return;
      }
      const ext = path.extname(filePath).toLowerCase();
      const mime =
        ext === '.html' ? 'text/html; charset=utf-8' :
        ext === '.txt' ? 'text/plain; charset=utf-8' :
        ext === '.css' ? 'text/css; charset=utf-8' :
        ext === '.js' ? 'application/javascript; charset=utf-8' :
        ext === '.png' ? 'image/png' : 'application/octet-stream';
      res.writeHead(200, { 'Content-Type': mime });
      fs.createReadStream(filePath).pipe(res);
    });
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address();
      resolve({ server, port, requestedUrls });
    });
  });
}

function runLighthouseAsync(url, lhOutPath) {
  return new Promise((resolve) => {
    const child = spawn(
      NODE_EXE,
      [
        LH_CLI,
        url,
        '--output=json',
        `--output-path=${lhOutPath}`,
        '--only-categories=performance,accessibility,best-practices,seo',
        '--chrome-flags=--headless=new --no-sandbox --disable-gpu',
        '--quiet',
      ],
      {
        env: { ...process.env, CHROME_PATH },
        stdio: ['ignore', 'pipe', 'pipe'],
      }
    );
    let stderr = '';
    child.stderr.on('data', (d) => { stderr += d.toString(); });
    child.on('close', (code) => {
      resolve({ code, stderr });
    });
  });
}

async function evaluateFolder(slug, task) {
  const folder = path.join(BASE_DIR, slug, task);
  const htmlPath = path.join(folder, 'index.html');
  if (!fs.existsSync(htmlPath)) {
    return { slug, task, exists: false };
  }

  const { server, port, requestedUrls } = await startStaticServer(folder);
  const url = `http://127.0.0.1:${port}/index.html`;
  console.log(`[CHECK] ${slug}/${task} on ${url}`);

  const consoleErrors = [];
  const consoleWarnings = [];
  const pageErrors = [];
  const failedRequests = [];
  const badResponses = [];

  const browser = await chromium.launch({ executablePath: CHROME_PATH, headless: true });
  try {
    // Desktop 1440x900
    const ctxDesktop = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const pageDesktop = await ctxDesktop.newPage();
    pageDesktop.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
      else if (msg.type() === 'warning') consoleWarnings.push(msg.text());
    });
    pageDesktop.on('pageerror', (err) => pageErrors.push(String(err)));
    pageDesktop.on('requestfailed', (req) => failedRequests.push({ url: req.url(), reason: req.failure()?.errorText }));
    pageDesktop.on('response', (resp) => {
      if (resp.status() >= 400) badResponses.push({ url: resp.url(), status: resp.status() });
    });

    await pageDesktop.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
    await pageDesktop.waitForTimeout(500);
    await pageDesktop.screenshot({ path: path.join(folder, 'shot-desktop.png'), fullPage: false });
    await pageDesktop.screenshot({ path: path.join(folder, 'shot-desktop-full.png'), fullPage: true });
    await ctxDesktop.close();

    // Mobile 375x812
    const ctxMobile = await browser.newContext({ viewport: { width: 375, height: 812 } });
    const pageMobile = await ctxMobile.newPage();
    await pageMobile.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
    await pageMobile.waitForTimeout(500);
    await pageMobile.screenshot({ path: path.join(folder, 'shot-mobile.png'), fullPage: false });
    await pageMobile.screenshot({ path: path.join(folder, 'shot-mobile-full.png'), fullPage: true });
    const mobileOverflow = await pageMobile.evaluate(() => {
      return {
        clientWidth: document.documentElement.clientWidth,
        scrollWidth: document.documentElement.scrollWidth,
        hasHorizontalScroll: document.documentElement.scrollWidth > document.documentElement.clientWidth,
      };
    });
    await ctxMobile.close();

    await browser.close();

    const lhOutPath = path.join(folder, 'lighthouse.json');
    const lhRes = await runLighthouseAsync(url, lhOutPath);

    let lhSummary = null;
    if (fs.existsSync(lhOutPath)) {
      const lhData = JSON.parse(fs.readFileSync(lhOutPath, 'utf-8'));
      const cats = lhData.categories || {};
      const audits = lhData.audits || {};
      const failedAudits = {};
      for (const [catName, catObj] of Object.entries(cats)) {
        failedAudits[catName] = [];
        for (const ref of catObj.auditRefs || []) {
          const a = audits[ref.id];
          if (a && a.score !== null && a.score < 1 && (ref.weight > 0 || catName !== 'performance')) {
            failedAudits[catName].push({ id: ref.id, title: a.title, score: a.score, displayValue: a.displayValue });
          }
        }
      }
      lhSummary = {
        performance: Math.round((cats.performance?.score || 0) * 100),
        accessibility: Math.round((cats.accessibility?.score || 0) * 100),
        bestPractices: Math.round((cats['best-practices']?.score || 0) * 100),
        seo: Math.round((cats.seo?.score || 0) * 100),
        cls: audits['cumulative-layout-shift']?.numericValue,
        lcp_ms: Math.round(audits['largest-contentful-paint']?.numericValue || 0),
        tbt_ms: Math.round(audits['total-blocking-time']?.numericValue || 0),
        failedAudits,
      };
    } else {
      lhSummary = { error: lhRes.stderr || 'lighthouse.json not created' };
    }

    server.close();
    return {
      slug,
      task,
      exists: true,
      consoleErrors,
      consoleWarnings,
      pageErrors,
      failedRequests,
      badResponses,
      requestedUrls,
      mobileOverflow,
      lighthouse: lhSummary,
    };
  } catch (err) {
    try { await browser.close(); } catch {}
    server.close();
    return { slug, task, exists: true, error: String(err) };
  }
}

async function main() {
  const results = [];
  for (const slug of SLUGS) {
    for (const task of TASKS) {
      results.push(await evaluateFolder(slug, task));
    }
  }
  const outPath = path.join(BASE_DIR, 'runtime_audit.json');
  fs.writeFileSync(outPath, JSON.stringify(results, null, 2), 'utf-8');
  console.log('Runtime audit saved to', outPath);
}

main();
