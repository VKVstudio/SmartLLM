// Port-free, offline headless Chrome 148 HTML batch renderer for WP-C2 (Calibration v2).
// Uses bundled puppeteer from chrome-devtools-mcp with pipe: true (0 TCP ports, 0 downloads).
// Usage: /usr/bin/node scripts/v2_calib/render_html_v2.mjs <manifest_json_path>

import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

import os from 'node:os';
const MCP_CANDIDATES = [
  process.env.SMARTLLM_MCP_THIRD_PARTY,
  ...(fs.existsSync(path.join(os.homedir(), 'Downloads'))
    ? fs.readdirSync(path.join(os.homedir(), 'Downloads')).map((d) =>
        path.join(os.homedir(), 'Downloads', d, 'resources', 'app.asar.unpacked', 'node_modules', 'chrome-devtools-mcp', 'build', 'src', 'third_party', 'index.js'))
    : []),
].filter(Boolean);

const CHROME_CANDIDATES = [
  process.env.SMARTLLM_CHROME_EXE,
  '/usr/bin/google-chrome-stable',
  '/usr/bin/chromium',
].filter(Boolean);

async function loadPuppeteer() {
  for (const cand of MCP_CANDIDATES) {
    if (fs.existsSync(cand)) {
      const mod = await import(pathToFileURL(cand).href);
      if (mod && mod.puppeteer) {
        return mod.puppeteer;
      }
    }
  }
  throw new Error(`Could not resolve bundled puppeteer from: ${MCP_CANDIDATES.join(', ')}`);
}

const chromePath = CHROME_CANDIDATES.find((p) => fs.existsSync(p));
if (!chromePath) {
  throw new Error(`Could not find headless Chrome binary in: ${CHROME_CANDIDATES.join(', ')}`);
}

const manifestPath = process.argv[2];
if (!manifestPath) {
  console.error('Usage: node render_html_v2.mjs <manifest_json_path>');
  process.exit(1);
}

const jobs = JSON.parse(fs.readFileSync(path.resolve(manifestPath), 'utf-8'));
const puppeteer = await loadPuppeteer();

const browser = await puppeteer.launch({
  executablePath: chromePath,
  headless: true,
  pipe: true,
  args: [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-gpu',
    '--disable-dev-shm-usage',
    '--hide-scrollbars',
    '--disable-background-networking',
    '--font-render-hinting=none',
  ],
});

try {
  const page = await browser.newPage();
  await page.setRequestInterception(true);
  page.on('request', (req) => {
    const url = req.url();
    if (url.startsWith('data:') || url.startsWith('about:')) {
      req.continue();
    } else {
      req.abort();
    }
  });

  for (const job of jobs) {
    const vw = Number(job.viewport_w || 1440);
    const vh = Number(job.viewport_h || 900);
    const scale = Number(job.scale || 1);
    await page.setViewport({
      width: vw,
      height: vh,
      deviceScaleFactor: scale,
    });
    await page.setContent(job.html, { waitUntil: 'load', timeout: 10000 });
    await new Promise((r) => setTimeout(r, 60));
    await page.screenshot({
      path: job.raw_png_path,
      type: 'png',
      clip: {
        x: 0,
        y: 0,
        width: vw,
        height: vh,
      },
    });
  }
  await page.close();
} finally {
  await browser.close();
}
