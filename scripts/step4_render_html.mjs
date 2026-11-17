// Port-free, CPU-only headless Chromium HTML batch renderer for Step 4 multimodal calibration samples.
// Usage: node scripts/step4_render_html.mjs <manifest_json_path>
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

function loadPlaywrightChromium() {
  const candidateAnchors = [
    path.resolve(process.cwd(), 'package.json'),
    'C:/projects/VKVstudio/package.json',
    'C:/Users/user/AppData/Roaming/npm/node_modules/n8n/node_modules/playwright-core/index.js',
  ];
  for (const anchor of candidateAnchors) {
    if (!fs.existsSync(anchor)) continue;
    const req = createRequire(anchor);
    for (const pkg of ['playwright-core', 'playwright']) {
      try {
        const mod = req(pkg);
        if (mod && mod.chromium) return mod.chromium;
      } catch {
        // try next candidate
      }
    }
  }
  throw new Error('Could not resolve playwright-core or playwright from local or workstation node_modules.');
}

const chromium = loadPlaywrightChromium();

const CHROME_CANDIDATES = [
  process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH,
  'C:\\Users\\user\\AppData\\Local\\ms-playwright\\chromium-1228\\chrome-win64\\chrome.exe',
].filter(Boolean);

const CHROME_PATH = CHROME_CANDIDATES.find((p) => fs.existsSync(p));

const manifestPath = process.argv[2];
if (!manifestPath) {
  console.error('Missing manifest path argument');
  process.exit(1);
}

const jobs = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));

const browser = await chromium.launch({
  ...(CHROME_PATH ? { executablePath: CHROME_PATH } : {}),
  headless: true,
  args: [
    '--disable-gpu',
    '--no-sandbox',
    '--hide-scrollbars',
    '--disable-background-networking',
    '--font-render-hinting=none',
  ],
});

try {
  for (const job of jobs) {
    const context = await browser.newContext({
      viewport: {
        width: job.viewport_w,
        height: job.viewport_h,
      },
      deviceScaleFactor: job.scale || 1,
    });
    const page = await context.newPage();
    // Block any accidental external network requests strictly offline
    await page.route('**/*', (route) => {
      const url = route.request().url();
      if (url.startsWith('data:') || url.startsWith('about:')) {
        return route.continue();
      }
      return route.abort();
    });
    await page.setContent(job.html, { waitUntil: 'load', timeout: 10000 });
    await page.waitForTimeout(80);
    await page.screenshot({
      path: job.raw_png_path,
      type: 'png',
      clip: {
        x: 0,
        y: 0,
        width: job.viewport_w,
        height: job.viewport_h,
      },
    });
    await context.close();
  }
} finally {
  await browser.close();
}
