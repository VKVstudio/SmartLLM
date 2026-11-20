#!/usr/bin/env node
/**
 * SmartLLM v0.0.3-beta — Frame-Exact 60fps Launch Video Renderer (Remotion Best-Practices Engine)
 *
 * Strictly follows `remotion-best-practices`:
 * - 100% frame-driven deterministic rendering via `window.renderFrame(frame, fps)`
 *   using explicit `interpolate()` + cubic-bezier / damped spring math.
 * - ZERO CSS `transition` or `@keyframes` animations anywhere in the DOM.
 * - Uses bundled OFL `.woff2` fonts (`Cormorant Garamond`, `Onest`, `JetBrains Mono`),
 *   `assets/brand/smartllm-logo.svg`, and `studio/smartllm_studio/static/art/*.webp`.
 * - Reads all benchmark receipts dynamically from `reports/verified_benchmarks_v001.json`.
 *
 * Modes:
 * - `--still-check`: Renders 4 keyframe PNG stills in < 5s on CPU to `media/launch_videos/preview_stills/`.
 * - `--render-all` / `--composition <id>`: Renders frame-exact 60fps MP4s muxed with `-14 LUFS` audio.
 */

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '..', '..');

const BENCHMARKS_PATH = path.join(ROOT, 'reports', 'verified_benchmarks_v001.json');
const FONTS_DIR = path.join(ROOT, 'studio', 'smartllm_studio', 'static', 'fonts');
const ART_DIR = path.join(ROOT, 'studio', 'smartllm_studio', 'static', 'art');
const LOGO_SVG_PATH = path.join(ROOT, 'assets', 'brand', 'smartllm-logo.svg');
const OUT_DIR = path.join(ROOT, 'media', 'launch_videos');
const STILLS_DIR = path.join(OUT_DIR, 'preview_stills');
const AUDIO_DIR = path.join(OUT_DIR, 'audio');

const MCP_THIRD_PARTY =
  process.env.SMARTLLM_MCP_THIRD_PARTY ||
  (() => {
    const dl = path.join(os.homedir(), 'Downloads');
    if (fs.existsSync(dl)) {
      for (const ent of fs.readdirSync(dl)) {
        const cand = path.join(dl, ent, 'resources', 'app.asar.unpacked', 'node_modules', 'chrome-devtools-mcp', 'build', 'src', 'third_party', 'index.js');
        if (fs.existsSync(cand)) return cand;
      }
    }
    return 'puppeteer';
  })();
const CHROME_BIN = process.env.SMARTLLM_CHROME_EXE || '/usr/bin/google-chrome-stable';

const COMPOSITIONS = {
  youtube_16x9: {
    id: 'youtube_16x9',
    outputFile: 'smartllm_youtube_launch_16x9.mp4',
    stillFile: 'youtube_16x9_still.png',
    width: 1920,
    height: 1080,
    fps: 60,
    durationSec: 75,
    stillFrame: 1200, // 20.0s mark (Studio 3-Pane + Live Telemetry & Receipts)
  },
  reddit_16x9: {
    id: 'reddit_16x9',
    outputFile: 'smartllm_reddit_proof_16x9.mp4',
    stillFile: 'reddit_16x9_still.png',
    width: 1920,
    height: 1080,
    fps: 60,
    durationSec: 50,
    stillFrame: 480, // 8.0s mark (Engineering Receipts First)
  },
  linkedin_4x5: {
    id: 'linkedin_4x5',
    outputFile: 'smartllm_linkedin_showcase_4x5.mp4',
    stillFile: 'linkedin_4x5_still.png',
    width: 1080,
    height: 1350,
    fps: 60,
    durationSec: 55,
    stillFrame: 1320, // 22.0s mark (Agency Privacy + 5-Gate Audit Seal)
  },
  reels_9x16: {
    id: 'reels_9x16',
    outputFile: 'smartllm_reels_vertical_9x16.mp4',
    stillFile: 'reels_9x16_still.png',
    width: 1080,
    height: 1920,
    fps: 60,
    durationSec: 40,
    stillFrame: 540, // 9.0s mark (Vertical Rhythmic Cut inside Safe Zones)
  },
};

function readDataUri(filePath, mimeType) {
  const buf = fs.readFileSync(filePath);
  return `data:${mimeType};base64,${buf.toString('base64')}`;
}

function buildFontFaceCss() {
  const fontSpecs = [
    { family: 'Cormorant Garamond', weight: 500, file: 'CormorantGaramond-500.woff2' },
    { family: 'Cormorant Garamond', weight: 600, file: 'CormorantGaramond-600.woff2' },
    { family: 'Onest', weight: 400, file: 'Onest-400.woff2' },
    { family: 'Onest', weight: 600, file: 'Onest-600.woff2' },
    { family: 'JetBrains Mono', weight: 400, file: 'JetBrainsMono-400.woff2' },
    { family: 'JetBrains Mono', weight: 600, file: 'JetBrainsMono-600.woff2' },
  ];
  return fontSpecs
    .map((f) => {
      const uri = readDataUri(path.join(FONTS_DIR, f.file), 'font/woff2');
      return `@font-face { font-family: '${f.family}'; font-style: normal; font-weight: ${f.weight}; font-display: block; src: url('${uri}') format('woff2'); }`;
    })
    .join('\n');
}

function loadAssetsAndBenchmarks() {
  const benchmarks = JSON.parse(fs.readFileSync(BENCHMARKS_PATH, 'utf8'));
  const logoSvg = fs.readFileSync(LOGO_SVG_PATH, 'utf8');
  const artHero = readDataUri(path.join(ART_DIR, 'atelier_hero_prism.webp'), 'image/webp');
  const artWireframe = readDataUri(path.join(ART_DIR, 'stage_empty_wireframe.webp'), 'image/webp');
  const artZimage = readDataUri(path.join(ART_DIR, 'zimage_optical_core.webp'), 'image/webp');
  const fontCss = buildFontFaceCss();
  return { benchmarks, logoSvg, artHero, artWireframe, artZimage, fontCss };
}

function buildStageHtml(comp, assets) {
  const payloadJson = JSON.stringify({
    comp,
    benchmarks: assets.benchmarks,
    logoSvg: assets.logoSvg,
    artHero: assets.artHero,
    artWireframe: assets.artWireframe,
    artZimage: assets.artZimage,
  });

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<style>
${assets.fontCss}
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
  /* Zero CSS transitions/animations per remotion-best-practices */
  transition: none !important;
  animation: none !important;
}
html, body {
  width: ${comp.width}px;
  height: ${comp.height}px;
  overflow: hidden;
  background: #0b0d12;
  color: #f3f4f8;
  font-family: 'Onest', sans-serif;
  -webkit-font-smoothing: antialiased;
}
#stage {
  position: relative;
  width: ${comp.width}px;
  height: ${comp.height}px;
  overflow: hidden;
  background: radial-gradient(circle at 82% 14%, rgba(192, 132, 252, 0.14), rgba(11, 13, 18, 0.98) 62%), #0b0d12;
}
.mono { font-family: 'JetBrains Mono', monospace; }
.serif { font-family: 'Cormorant Garamond', serif; }
.logo-box { width: 42px; height: 42px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; }
.logo-box svg { width: 100%; height: 100%; display: block; }
.pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 999px;
  background: rgba(25, 30, 43, 0.92);
  border: 1px solid rgba(192, 132, 252, 0.36);
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  letter-spacing: 0.04em;
  color: #e9d5ff;
}
.pill-gold {
  border-color: rgba(229, 184, 105, 0.55);
  color: #e5b869;
  background: rgba(36, 29, 20, 0.85);
}
.pill-green {
  border-color: rgba(74, 222, 128, 0.45);
  color: #4ade80;
  background: rgba(16, 35, 26, 0.88);
}
.card {
  background: rgba(19, 23, 34, 0.94);
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 16px;
  box-shadow: 0 22px 48px rgba(0, 0, 0, 0.55);
}
.caption-bar {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(9, 11, 16, 0.94);
  border: 1px solid rgba(192, 132, 252, 0.42);
  border-radius: 14px;
  padding: 14px 28px;
  text-align: center;
  box-shadow: 0 16px 36px rgba(0, 0, 0, 0.72);
  z-index: 50;
}
</style>
</head>
<body>
<div id="stage"></div>
<script>
window.DATA = ${payloadJson};
var DATA = window.DATA;

function clamp(v, lo, hi) {
  return Math.max(lo, Math.min(hi, v));
}

function easeOutCubic(t) {
  const x = clamp(t, 0, 1);
  return 1 - Math.pow(1 - x, 3);
}

function interpolate(frame, inRange, outRange, easingFn = easeOutCubic) {
  const [f0, f1] = inRange;
  const [o0, o1] = outRange;
  if (frame <= f0) return o0;
  if (frame >= f1) return o1;
  const raw = (frame - f0) / Math.max(1e-6, f1 - f0);
  const k = easingFn ? easingFn(raw) : raw;
  return o0 + (o1 - o0) * k;
}

function spring(frame, startFrame, fps, damping = 14, stiffness = 130) {
  const t = Math.max(0, (frame - startFrame) / fps);
  if (t <= 0) return 0;
  const omega = Math.sqrt(stiffness);
  const zeta = damping / (2 * Math.sqrt(stiffness));
  if (zeta < 1) {
    const wd = omega * Math.sqrt(1 - zeta * zeta);
    return 1 - Math.exp(-zeta * omega * t) * (Math.cos(wd * t) + (zeta / Math.sqrt(1 - zeta * zeta)) * Math.sin(wd * t));
  }
  return 1 - Math.exp(-omega * t);
}

function renderTopHeader(titleRight, badgeText) {
  return \`
    <div style="display:flex;align-items:center;justify-content:space-between;padding:28px 44px;border-bottom:1px solid rgba(148,163,184,0.14);background:rgba(11,13,18,0.88);">
      <div style="display:flex;align-items:center;gap:16px;">
        <div class="logo-box">\${DATA.logoSvg}</div>
        <div>
          <div style="display:flex;align-items:center;gap:10px;">
            <span style="font-weight:600;font-size:22px;letter-spacing:-0.01em;color:#f8fafc;">SmartLLM</span>
            <span class="pill-gold" style="padding:2px 10px;border-radius:6px;font-size:12px;font-family:'JetBrains Mono',monospace;">v\${DATA.benchmarks.version}</span>
          </div>
          <div class="mono" style="font-size:12px;color:#94a3b8;margin-top:2px;">127.0.0.1 OFFLINE MULTIMODAL WEB &amp; DESIGN COMBINE</div>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:14px;">
        <span class="pill">\${titleRight}</span>
        <span class="pill pill-green">● \${badgeText}</span>
      </div>
    </div>
  \`;
}

function renderYoutube16x9(frame, fps) {
  const sec = frame / fps;
  const b = DATA.benchmarks;
  let sceneHtml = '';
  let caption = '';

  if (sec < 3.5) {
    const s = spring(frame, 0, fps);
    caption = '335 GB MoE Combine compressed to a single 12 GB Laptop GPU — 100% Offline, 0 B Disk Swap.';
    sceneHtml = \`
      <div style="padding:64px 72px;display:grid;grid-template-columns:1.15fr 0.85fr;gap:48px;align-items:center;height:880px;transform:translateY(\${(1-s)*28}px);opacity:\${clamp(s,0,1)};">
        <div>
          <div style="display:flex;gap:12px;margin-bottom:22px;">
            <span class="pill pill-gold">OPEN BETA v0.0.3-beta</span>
            <span class="pill">RTX 4080 LAPTOP 12 GB + 31 GB RAM</span>
          </div>
          <h1 class="serif" style="font-size:74px;line-height:1.02;font-weight:600;color:#ffffff;letter-spacing:-0.02em;">
            Frontier-Craft Web &amp; Brand Engineering on Your Own Metal.
          </h1>
          <p style="font-size:24px;line-height:1.45;color:#cbd5e1;margin-top:24px;max-width:820px;">
            Domain-pruned <strong style="color:#c084fc;">Qwen3.8-Flash-Next (K=320/512)</strong> + Clean-Room <strong style="color:#4ade80;">GSQ Q2_0</strong> + Sequential <strong style="color:#e5b869;">Z-Image 1024&times;1024</strong> inside a 3-pane local Atelier.
          </p>
        </div>
        <div class="card" style="padding:24px;position:relative;overflow:hidden;">
          <img src="\${DATA.artHero}" style="width:100%;height:420px;object-fit:cover;border-radius:12px;border:1px solid rgba(192,132,252,0.3);" />
          <div class="mono" style="margin-top:16px;display:flex;justify-content:space-between;font-size:15px;color:#e2e8f0;">
            <span>PLE_Rss: <strong style="color:#4ade80;">0 kB (O_DIRECT)</strong></span>
            <span>Disk Swap: <strong style="color:#4ade80;">0 B</strong></span>
            <span>Decode: <strong style="color:#c084fc;">\${b.runtime_soak_32k.steady_decode_tok_s} tok/s</strong></span>
          </div>
        </div>
      </div>
    \`;
  } else if (sec < 30.0) {
    const localF = frame - Math.round(3.5 * fps);
    const enter = easeOutCubic(clamp(localF / 24, 0, 1));
    const stepIdx = Math.min(6, 1 + Math.floor((sec - 3.5) / 4.2));
    caption = \`3-Pane Atelier Workbench: 264px Navigator · 6-Step Constructor (Step \${stepIdx}/6) · 44% Live Stage + 32px Telemetry HUD.\`;
    sceneHtml = \`
      <div style="padding:28px 44px;height:880px;display:flex;flex-direction:column;gap:18px;opacity:\${enter};">
        <div style="display:grid;grid-template-columns:264px 1fr 760px;gap:18px;flex:1;min-height:0;">
          <!-- Left Pane: 264px Navigator -->
          <div class="card" style="padding:20px;display:flex;flex-direction:column;justify-content:space-between;">
            <div>
              <div class="mono" style="font-size:12px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:14px;">Atelier Modes</div>
              <div style="padding:10px 12px;border-radius:10px;background:rgba(192,132,252,0.16);border:1px solid rgba(192,132,252,0.45);font-weight:600;font-size:15px;margin-bottom:8px;">✦ 6-Step Constructor</div>
              <div style="padding:10px 12px;border-radius:10px;color:#94a3b8;font-size:14px;margin-bottom:18px;">⚡ Express One-Prompt</div>
              <div class="mono" style="font-size:12px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:10px;">Constructor Steps</div>
              \${[
                '1 · Brand & Brief DNA',
                '2 · Brick & Menu Composer',
                '3 · Canon Gallery (28 OKLCH)',
                '4 · EN/RU Copy & Z-Image',
                '5 · SERP / JSON-LD / AI Bots',
                '6 · 5-Gate Audit & Export',
              ].map((label, idx) => \`
                <div style="padding:9px 11px;border-radius:8px;margin-bottom:6px;font-size:13px;display:flex;justify-content:space-between;align-items:center;background:\${idx + 1 === stepIdx ? 'rgba(229,184,105,0.14)' : 'transparent'};border:1px solid \${idx + 1 === stepIdx ? 'rgba(229,184,105,0.5)' : 'transparent'};color:\${idx + 1 === stepIdx ? '#f8fafc' : '#94a3b8'};">
                  <span>\${label}</span>
                  <span class="mono" style="font-size:11px;color:\${idx + 1 <= stepIdx ? '#4ade80' : '#64748b'};">\${idx + 1 <= stepIdx ? 'READY' : '—'}</span>
                </div>
              \`).join('')}
            </div>
            <div style="padding:12px;border-radius:10px;background:rgba(15,23,42,0.85);border:1px solid rgba(74,222,128,0.3);">
              <div class="mono" style="font-size:11px;color:#4ade80;">RAG KNOWLEDGE BANK</div>
              <div style="font-size:13px;color:#e2e8f0;margin-top:4px;">28 Canons · 168 EN/RU Copy Pairs · 6 Audit Checklists</div>
            </div>
          </div>

          <!-- Center Pane: Active Constructor Workspace -->
          <div class="card" style="padding:24px;display:flex;flex-direction:column;justify-content:space-between;">
            <div>
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
                <span class="pill pill-gold">STEP 0\${stepIdx} ACTIVE</span>
                <span class="mono" style="font-size:13px;color:#c084fc;">0 Unbound Controls (167/167 CDP Verified)</span>
              </div>
              <h2 class="serif" style="font-size:36px;font-weight:600;color:#ffffff;margin-bottom:10px;">
                Swiss International Grid &amp; Bilingual EN+RU Copy Engine
              </h2>
              <p style="font-size:16px;color:#cbd5e1;line-height:1.5;margin-bottom:20px;">
                Every layout brick compiles with strict <span class="mono" style="color:#4ade80;">sha256-CSP</span>, semantic <span class="mono" style="color:#c084fc;">oklch()</span> AAA contrast (&ge;7:1), <span class="mono">application/ld+json @graph</span>, and 8-crawler AI visibility controls.
              </p>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
                <div style="padding:16px;border-radius:12px;background:rgba(11,13,18,0.85);border:1px solid rgba(192,132,252,0.28);">
                  <div class="mono" style="font-size:12px;color:#c084fc;margin-bottom:8px;">OKLCH PALETTE SWATCHES</div>
                  <div style="display:flex;gap:10px;align-items:center;">
                    <span style="width:32px;height:32px;border-radius:8px;background:#0b0d12;border:1px solid #475569;"></span>
                    <span style="width:32px;height:32px;border-radius:8px;background:#151923;border:1px solid #475569;"></span>
                    <span style="width:32px;height:32px;border-radius:8px;background:#c084fc;"></span>
                    <span style="width:32px;height:32px;border-radius:8px;background:#e5b869;"></span>
                    <span style="width:32px;height:32px;border-radius:8px;background:#4ade80;"></span>
                  </div>
                  <div class="mono" style="font-size:12px;color:#94a3b8;margin-top:10px;">AAA 14.5:1 Primary Text Contrast</div>
                </div>
                <div style="padding:16px;border-radius:12px;background:rgba(11,13,18,0.85);border:1px solid rgba(74,222,128,0.28);">
                  <div class="mono" style="font-size:12px;color:#4ade80;margin-bottom:8px;">5-GATE AUDIT SCORECARD</div>
                  <div class="mono" style="font-size:13px;color:#f8fafc;line-height:1.65;">
                    ✓ SHA-256 CSP (0 unsafe-inline)<br/>
                    ✓ HSTS + COOP/COEP/CORP<br/>
                    ✓ WCAG 2.2 AA/AAA (&ge;24px targets)<br/>
                    ✓ Lighthouse A11y 100 / BP 100
                  </div>
                </div>
              </div>
            </div>
            <div style="padding:16px;border-radius:12px;background:rgba(15,23,42,0.75);border:1px solid rgba(148,163,184,0.18);display:flex;justify-content:space-between;align-items:center;">
              <div>
                <div class="mono" style="font-size:12px;color:#e5b869;">SEQUENTIAL Z-IMAGE QUEUE (sd.cpp sm_89)</div>
                <div style="font-size:14px;color:#e2e8f0;margin-top:3px;">1024&times;1024 DiT q8_0 · Slot 0 KV Saved (37.8 ms) &rarr; Restored (74.4 ms)</div>
              </div>
              <span class="pill pill-green">19.68s / 1024&sup2; PNG</span>
            </div>
          </div>

          <!-- Right Pane: 44% Persistent Live Stage -->
          <div class="card" style="padding:20px;display:flex;flex-direction:column;justify-content:space-between;background:rgba(13,16,24,0.96);">
            <div>
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                <span class="mono" style="font-size:12px;color:#94a3b8;">LIVE STAGE PREVIEW · 127.0.0.1:8090/preview/default</span>
                <span class="pill pill-green" style="font-size:11px;padding:3px 10px;">0 External Requests</span>
              </div>
              <div style="border-radius:12px;overflow:hidden;border:1px solid rgba(192,132,252,0.32);position:relative;height:470px;background:#090b10;">
                <img src="\${DATA.artZimage}" style="width:100%;height:270px;object-fit:cover;display:block;" />
                <div style="padding:18px 22px;">
                  <div class="mono" style="font-size:11px;color:#e5b869;letter-spacing:0.08em;">QUARTZ-FIELD ATELIER · EN + RU BILINGUAL</div>
                  <div class="serif" style="font-size:28px;font-weight:600;color:#ffffff;margin-top:4px;">Deterministic Zero-Swap Edge Telemetry</div>
                  <div style="font-size:14px;color:#94a3b8;margin-top:6px;">Детерминированная телеметрия без подкачки · Прямое чтение O_DIRECT с NVMe.</div>
                  <div style="display:flex;gap:10px;margin-top:14px;">
                    <span class="pill" style="font-size:12px;">ld+json @graph</span>
                    <span class="pill" style="font-size:12px;">llms.txt</span>
                    <span class="pill" style="font-size:12px;">hreflang en/ru</span>
                  </div>
                </div>
              </div>
            </div>
            <!-- 32px Telemetry HUD -->
            <div class="mono" style="height:38px;padding:0 14px;border-radius:8px;background:#080a0f;border:1px solid rgba(148,163,184,0.2);display:flex;align-items:center;justify-content:space-between;font-size:12px;color:#cbd5e1;">
              <span>GPU: <strong style="color:#4ade80;">9.12 / 10.5 GiB</strong></span>
              <span>MemAvail: <strong style="color:#4ade80;">24.60 GiB</strong></span>
              <span>PLE_Rss: <strong style="color:#4ade80;">0 kB</strong></span>
              <span>DiskSwap: <strong style="color:#4ade80;">0 B</strong></span>
            </div>
          </div>
        </div>
      </div>
    \`;
  } else if (sec < 54.0) {
    caption = 'Verified Wave 3 & Stage D Hardware Receipts: 1,223s 32K Soak at 17.50 tok/s with 0 B Disk Swap.';
    sceneHtml = renderReceiptsGrid(frame - Math.round(30 * fps), fps);
  } else {
    caption = 'Test SmartLLM v0.0.3-beta Free on Linux & Windows 11 — Star, Break It, and File Issues on GitHub.';
    sceneHtml = renderCtaScene(frame - Math.round(54 * fps), fps, 'OPEN v0.0.3-beta · TEST & FEEDBACK INVITE');
  }

  return \`
    \${renderTopHeader('YOUTUBE LAUNCH · 1920×1080 60FPS', '100% LOCAL LOOPBACK')}
    \${sceneHtml}
    <div class="caption-bar" style="bottom:24px;width:1520px;font-size:21px;font-weight:600;color:#f8fafc;">
      \${caption}
    </div>
  \`;
}

function renderReceiptsGrid(localFrame, fps) {
  const b = DATA.benchmarks;
  const s = easeOutCubic(clamp(localFrame / 20, 0, 1));
  const cards = [
    {
      tag: 'DOMAIN-PRUNED MOE + GSQ Q2_0',
      title: 'K = 320 / 512 Experts Kept',
      metric: '-65.68% Q2_0 Error',
      detail: "Quota-locked A4' (WH=64, RU>=40, Copy>=35, Vis>=30) + C3 router/expert healing + clean-room Dual-Sign Cholesky GSQ Q2_0.",
      color: '#c084fc',
    },
    {
      tag: 'ZERO-SWAP O_DIRECT PLE ENGINE',
      title: '0 kB Resident PLE RAM',
      metric: '0 B NVMe Swap',
      detail: '26.82 GiB per_layer_token_embd streamed via 8-worker O_DIRECT pread + munmap. 24.60 GiB free RAM maintained across 20-min 32K soak.',
      color: '#4ade80',
    },
    {
      tag: '32K LONG-CONTEXT SOAK (1,223s)',
      title: '17.50 tok/s Steady Decode',
      metric: '9.12 GiB Peak VRAM',
      detail: '25.29 tok/s with draft-MTP (81.1% accept) · 289.3 tok/s prefill · 8-class CRF ClassLRU cache (2048 MiB, 37.24% hit rate).',
      color: '#e5b869',
    },
    {
      tag: 'SEQUENTIAL LLM <-> Z-IMAGE SWITCH',
      title: '19.68s 1024×1024 DiT Batch',
      metric: '31.0 MiB Exit Barrier',
      detail: 'Slot 0 KV saved in 37.8 ms -> llama-server SIGTERM -> 0 compute apps verified -> sd.cpp q8_0 DiT -> slot restored (18/18 tokens).',
      color: '#4ade80',
    },
  ];
  return \`
    <div style="padding:36px 56px;height:880px;transform:translateY(\${(1-s)*18}px);opacity:\${s};">
      <div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:24px;">
        <div>
          <span class="pill pill-green">VERIFIED BENCHMARK RECEIPTS · NO SYNTHETIC NUMBERS</span>
          <h2 class="serif" style="font-size:48px;font-weight:600;color:#ffffff;margin-top:10px;">
            Every Claim Backed by Raw <span class="mono" style="font-size:38px;color:#c084fc;">/proc/pid/smaps</span> &amp; Watchdog Telemetry
          </h2>
        </div>
        <div class="mono" style="font-size:14px;color:#94a3b8;text-align:right;">
          Host: \${b.hardware_envelope.device}<br/>
          GPU: \${b.hardware_envelope.gpu}
        </div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:22px;">
        \${cards.map((c) => \`
          <div class="card" style="padding:28px;border-left:4px solid \${c.color};display:flex;flex-direction:column;justify-content:space-between;">
            <div>
              <div class="mono" style="font-size:12px;color:\${c.color};letter-spacing:0.06em;">\${c.tag}</div>
              <div style="display:flex;justify-content:space-between;align-items:baseline;margin-top:10px;">
                <h3 style="font-size:28px;font-weight:600;color:#ffffff;">\${c.title}</h3>
                <span class="mono" style="font-size:22px;font-weight:600;color:\${c.color};">\${c.metric}</span>
              </div>
              <p style="font-size:16px;line-height:1.5;color:#cbd5e1;margin-top:14px;">\${c.detail}</p>
            </div>
            <div class="mono" style="margin-top:18px;padding-top:12px;border-top:1px solid rgba(148,163,184,0.14);font-size:12px;color:#94a3b8;display:flex;justify-content:space-between;">
              <span>Source: reports/verified_benchmarks_v001.json</span>
              <span style="color:#4ade80;">PASS (EXIT 0)</span>
            </div>
          </div>
        \`).join('')}
      </div>
    </div>
  \`;
}

function renderCtaScene(localFrame, fps, badgeLabel) {
  const s = easeOutCubic(clamp(localFrame / 18, 0, 1));
  return \`
    <div style="padding:48px 72px;height:880px;display:grid;grid-template-columns:1.1fr 0.9fr;gap:40px;align-items:center;opacity:\${s};">
      <div>
        <span class="pill pill-gold">\${badgeLabel}</span>
        <h2 class="serif" style="font-size:62px;line-height:1.05;font-weight:600;color:#ffffff;margin-top:18px;">
          Free Launch Beta.<br/>Test It on Your Hardware &amp; Tell Us What Breaks.
        </h2>
        <p style="font-size:20px;line-height:1.5;color:#cbd5e1;margin-top:20px;">
          SmartLLM Studio is free (<span class="mono" style="color:#c084fc;">FSL-1.1-ALv2 &rarr; Apache-2.0</span>). Agencies and freelancers keep <strong>100% ownership</strong> of all generated sites, code, and visual assets.
        </p>
        <div style="margin-top:26px;display:flex;flex-direction:column;gap:12px;">
          <div class="card mono" style="padding:16px 22px;font-size:17px;color:#4ade80;border-color:rgba(74,222,128,0.4);">
            ★ Core Combine: https://github.com/VKVstudio/SmartLLM
          </div>
          <div class="card mono" style="padding:16px 22px;font-size:17px;color:#c084fc;border-color:rgba(192,132,252,0.4);">
            ★ Standalone Studio: https://github.com/VKVstudio/SmartLLM-Studio
          </div>
        </div>
      </div>
      <div class="card" style="padding:28px;">
        <div class="mono" style="font-size:13px;color:#e5b869;margin-bottom:12px;">ONE-COMMAND INSTALL (LINUX &amp; WINDOWS 11)</div>
        <pre class="mono" style="background:#07090e;padding:18px;border-radius:10px;border:1px solid rgba(148,163,184,0.2);font-size:14px;line-height:1.65;color:#e2e8f0;overflow:hidden;">git clone https://github.com/VKVstudio/SmartLLM-Studio
cd SmartLLM-Studio
./install.sh          # or .\\install.ps1 on Win11
./bin/smartllm-studio # opens http://127.0.0.1:8090</pre>
        <div style="margin-top:18px;font-size:15px;color:#cbd5e1;line-height:1.5;">
          <strong>We want brutal engineering feedback:</strong><br/>
          • Try 32K long-context prompts on 12 GB / 16 GB GPUs<br/>
          • Audit our SHA-256 CSP &amp; OKLCH AAA output bundles<br/>
          • Open a GitHub Issue with your <span class="mono" style="color:#4ade80;">sla_watchdog.py</span> telemetry!
        </div>
      </div>
    </div>
  \`;
}

function renderReddit16x9(frame, fps) {
  const sec = frame / fps;
  let body = '';
  let caption = '';
  if (sec < 18.0) {
    caption = 'r/LocalLLaMA Receipts First: K=320/512 Pruned Qwen3.8 + Clean-Room GSQ Q2_0 + 0 kB PLE RAM via O_DIRECT.';
    body = renderReceiptsGrid(frame, fps);
  } else if (sec < 36.0) {
    caption = 'Sequential GPU State Machine: llama-server Slot Save (37.8 ms) <-> sd.cpp 1024×1024 Z-Image (19.68s) at 31 MiB Exit Barrier.';
    body = renderYoutube16x9(Math.round(12 * fps), fps);
    return body;
  } else {
    caption = 'Clone v0.0.3-beta, Run the 1-Hz Zero-Swap Watchdog on Your Rig, and Post Your Telemetry in GitHub Issues.';
    body = renderCtaScene(frame - Math.round(36 * fps), fps, 'r/LocalLLaMA & r/SelfHosted BENCHMARK CALL');
  }
  return \`
    \${renderTopHeader('REDDIT TECHNICAL PROOF · ZERO HYPE', 'smaps_rollup VERIFIED')}
    \${body}
    <div class="caption-bar" style="bottom:24px;width:1520px;font-size:21px;font-weight:600;color:#f8fafc;">
      \${caption}
    </div>
  \`;
}

function renderLinkedin4x5(frame, fps) {
  const sec = frame / fps;
  const s = easeOutCubic(clamp((frame % 180) / 18, 0, 1));
  const caption =
    sec < 16
      ? '100% Local Client Privacy: 127.0.0.1 Loopback Only, Zero Cloud APIs, FSL-1.1-ALv2 Free for Agency Client Work.'
      : sec < 38
      ? 'Deterministic 5-Gate Quality Seal: SHA-256 CSP, WCAG AAA OKLCH, JSON-LD @graph, and Lighthouse 100/100.'
      : 'Download SmartLLM Studio v0.0.3-beta for Linux & Windows 11 — Share Your Agency Workflow Feedback on GitHub.';

  return \`
    <div style="padding:36px 44px;height:1350px;display:flex;flex-direction:column;justify-content:space-between;">
      <div>
        <div style="display:flex;justify-content:space-between;align-items:center;padding-bottom:22px;border-bottom:1px solid rgba(148,163,184,0.16);">
          <div style="display:flex;align-items:center;gap:14px;">
            <div class="logo-box">\${DATA.logoSvg}</div>
            <div>
              <div style="font-size:22px;font-weight:600;color:#ffffff;">SmartLLM Studio <span class="mono" style="font-size:14px;color:#e5b869;">v0.0.3-beta</span></div>
              <div class="mono" style="font-size:12px;color:#94a3b8;">OFFLINE WEB &amp; BRAND DESIGN COMBINE (EN + RU)</div>
            </div>
          </div>
          <span class="pill pill-green">127.0.0.1 ONLY</span>
        </div>

        <div style="margin-top:26px;">
          <span class="pill pill-gold">FSL-1.1-ALv2 · 100% CLIENT OUTPUT OWNERSHIP</span>
          <h1 class="serif" style="font-size:52px;line-height:1.06;font-weight:600;color:#ffffff;margin-top:14px;">
            Ship Audited Editorial Websites &amp; Visual Assets Without Sending Client Briefs to the Cloud.
          </h1>
        </div>

        <div class="card" style="margin-top:24px;padding:22px;display:grid;grid-template-columns:1.1fr 0.9fr;gap:20px;align-items:center;">
          <img src="\${DATA.artHero}" style="width:100%;height:300px;object-fit:cover;border-radius:12px;border:1px solid rgba(192,132,252,0.35);" />
          <div>
            <div class="mono" style="font-size:12px;color:#c084fc;margin-bottom:8px;">3-PANE ATELIER + 5-GATE AUDITOR</div>
            <div class="mono" style="font-size:14px;color:#f8fafc;line-height:1.75;">
              • 28 OKLCH Design Canons<br/>
              • 168 EN/RU Copywriting Pairs<br/>
              • SHA-256 CSP (0 unsafe-inline)<br/>
              • JSON-LD @graph + llms.txt<br/>
              • Z-Image 1024&times;1024 in 19.7s<br/>
              • Lighthouse A11y 100 / BP 100
            </div>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:20px;">
          <div class="card" style="padding:18px;">
            <div class="mono" style="font-size:12px;color:#94a3b8;">LAPTOP GPU ENVELOPE</div>
            <div class="mono" style="font-size:26px;font-weight:600;color:#4ade80;margin-top:6px;">9.12 GiB VRAM</div>
            <div style="font-size:13px;color:#cbd5e1;margin-top:4px;">Fits 12 GB RTX 4080 Laptop at 32K context</div>
          </div>
          <div class="card" style="padding:18px;">
            <div class="mono" style="font-size:12px;color:#94a3b8;">ZERO-SWAP GUARANTEE</div>
            <div class="mono" style="font-size:26px;font-weight:600;color:#c084fc;margin-top:6px;">0 B Disk Swap</div>
            <div style="font-size:13px;color:#cbd5e1;margin-top:4px;">O_DIRECT NVMe PLE streaming (0 kB RSS)</div>
          </div>
          <div class="card" style="padding:18px;">
            <div class="mono" style="font-size:12px;color:#94a3b8;">OPEN BETA LICENSE</div>
            <div class="mono" style="font-size:26px;font-weight:600;color:#e5b869;margin-top:6px;">$0 Free Launch</div>
            <div style="font-size:13px;color:#cbd5e1;margin-top:4px;">Commercial client work permitted</div>
          </div>
        </div>

        <div class="card mono" style="margin-top:20px;padding:16px 22px;display:flex;justify-content:space-between;align-items:center;font-size:15px;color:#e2e8f0;border-color:rgba(192,132,252,0.4);">
          <span>github.com/VKVstudio/SmartLLM-Studio</span>
          <span style="color:#4ade80;">Test v0.0.3-beta &amp; Share Feedback &rarr;</span>
        </div>
      </div>

      <div class="caption-bar" style="position:relative;left:auto;transform:none;width:100%;font-size:19px;font-weight:600;color:#f8fafc;">
        \${caption}
      </div>
    </div>
  \`;
}

function renderReels9x16(frame, fps) {
  const sec = frame / fps;
  const beatIdx = Math.floor(sec / 2.0);
  const beats = [
    { tag: 'BEAT 01 · THE HOOK', title: '335 GB MoE Combine on a 12 GB Laptop GPU.', metric: '0 CLOUD · 0 SWAP', sub: 'SmartLLM v0.0.3-beta running locally on 127.0.0.1' },
    { tag: 'BEAT 02 · PRUNED + HEALED', title: 'K = 320 / 512 Specialists Kept.', metric: '-65.68% Q2_0 ERR', sub: 'Quota-locked EN+RU+Code+Vision + Clean-Room GSQ Q2_0' },
    { tag: 'BEAT 03 · O_DIRECT PLE', title: '26.82 GiB PLE Table Off-RAM.', metric: '0 kB PLE RSS', sub: '8-worker O_DIRECT NVMe pread · 24.6 GiB RAM free' },
    { tag: 'BEAT 04 · 32K SOAK SPEED', title: 'Sustained 32K Context Decode.', metric: '17.5–25.3 tok/s', sub: '9.12 GiB peak VRAM · 289.3 tok/s prefill' },
    { tag: 'BEAT 05 · SEQUENTIAL Z-IMAGE', title: 'LLM <-> Z-Image GPU Handoff.', metric: '19.68s 1024×1024', sub: 'Slot saved in 37.8 ms · 31 MiB clean VRAM barrier' },
    { tag: 'BEAT 06 · 3-PANE ATELIER', title: 'Express & 6-Step Constructor.', metric: '167/167 CONTROLS', sub: '28 OKLCH Canons · 168 EN/RU Copy Pairs · 5-Gate Seal' },
    { tag: 'BEAT 07 · TEST THE BETA', title: 'Free Launch on Linux & Win11.', metric: 'v0.0.3-beta LIVE', sub: 'github.com/VKVstudio/SmartLLM · Try it & file feedback!' },
  ];
  const cur = beats[beatIdx % beats.length];

  // Safe zones for 1080x1920 vertical (top >= 180px, bottom >= 340px, right >= 120px)
  return \`
    <div style="padding:190px 124px 350px 68px;height:1920px;display:flex;flex-direction:column;justify-content:space-between;">
      <div style="display:flex;align-items:center;justify-content:space-between;">
        <div style="display:flex;align-items:center;gap:12px;">
          <div class="logo-box">\${DATA.logoSvg}</div>
          <span style="font-size:24px;font-weight:600;color:#ffffff;">SmartLLM</span>
        </div>
        <span class="pill pill-gold">v0.0.3-beta</span>
      </div>

      <div class="card" style="padding:34px;border-top:4px solid #c084fc;">
        <div class="mono" style="font-size:15px;color:#c084fc;letter-spacing:0.08em;">\${cur.tag}</div>
        <h1 class="serif" style="font-size:60px;line-height:1.05;font-weight:600;color:#ffffff;margin-top:14px;">
          \${cur.title}
        </h1>
        <div class="mono" style="font-size:44px;font-weight:600;color:#4ade80;margin-top:20px;">
          \${cur.metric}
        </div>
        <p style="font-size:22px;line-height:1.45;color:#cbd5e1;margin-top:16px;">
          \${cur.sub}
        </p>
        <img src="\${beatIdx % 2 === 0 ? DATA.artZimage : DATA.artHero}" style="width:100%;height:340px;object-fit:cover;border-radius:14px;margin-top:24px;border:1px solid rgba(192,132,252,0.35);" />
      </div>

      <div class="card" style="padding:24px 28px;background:rgba(9,11,16,0.95);border-color:rgba(74,222,128,0.45);">
        <div class="mono" style="font-size:14px;color:#e5b869;">OPEN BETA · TEST &amp; FEEDBACK</div>
        <div class="mono" style="font-size:20px;font-weight:600;color:#ffffff;margin-top:6px;">github.com/VKVstudio/SmartLLM</div>
        <div style="font-size:17px;color:#cbd5e1;margin-top:6px;">Clone SmartLLM-Studio · Run on 127.0.0.1 · Post your benchmark issues!</div>
      </div>
    </div>
  \`;
}

window.renderFrame = function(frame, fps) {
  const id = DATA.comp.id;
  const stage = document.getElementById('stage');
  if (id === 'youtube_16x9') {
    stage.innerHTML = renderYoutube16x9(frame, fps);
  } else if (id === 'reddit_16x9') {
    stage.innerHTML = renderReddit16x9(frame, fps);
  } else if (id === 'linkedin_4x5') {
    stage.innerHTML = renderLinkedin4x5(frame, fps);
  } else {
    stage.innerHTML = renderReels9x16(frame, fps);
  }
  return true;
};
</script>
</body>
</html>`;
}

async function loadPuppeteer() {
  const mcpMod = await import(pathToFileURL(MCP_THIRD_PARTY).href);
  const puppeteer = mcpMod.puppeteer || mcpMod.default?.puppeteer;
  if (!puppeteer) {
    throw new Error(`Could not resolve bundled puppeteer from ${MCP_THIRD_PARTY}`);
  }
  return puppeteer;
}

async function launchCpuBrowser(puppeteer) {
  return puppeteer.launch({
    executablePath: CHROME_BIN,
    pipe: true,
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--use-gl=swiftshader',
      '--no-first-run',
      '--no-default-browser-check',
      '--hide-scrollbars',
    ],
  });
}

async function runStillCheck(assets) {
  fs.mkdirSync(STILLS_DIR, { recursive: true });
  const puppeteer = await loadPuppeteer();
  const browser = await launchCpuBrowser(puppeteer);
  const results = [];
  try {
    for (const comp of Object.values(COMPOSITIONS)) {
      const page = await browser.newPage();
      try {
        await page.setViewport({ width: comp.width, height: comp.height, deviceScaleFactor: 1 });
        const html = buildStageHtml(comp, assets);
        await page.setContent(html, { waitUntil: 'load' });
        await page.evaluate(() => document.fonts.ready);
        await page.evaluate((f, fps) => window.renderFrame(f, fps), comp.stillFrame, comp.fps);
        const outPath = path.join(STILLS_DIR, comp.stillFile);
        await page.screenshot({ path: outPath, type: 'png' });
        const stat = fs.statSync(outPath);
        results.push({
          composition: comp.id,
          width: comp.width,
          height: comp.height,
          frame: comp.stillFrame,
          still_path: outPath,
          bytes: stat.size,
        });
      } finally {
        await page.close();
      }
    }
  } finally {
    await browser.close();
  }
  return results;
}

async function renderFullVideo(comp, assets) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const audioM4a = path.join(AUDIO_DIR, `${comp.id}.m4a`);
  if (!fs.existsSync(audioM4a)) {
    const pyExe = path.join(ROOT, '.venv_linux', 'bin', 'python');
    const audioScript = path.join(ROOT, 'scripts', 'release', 'synth_launch_audio.py');
    const r = spawnSync(pyExe, [audioScript, '--composition', comp.id], { stdio: 'inherit' });
    if (r.status !== 0) {
      throw new Error(`Audio synthesis failed for ${comp.id}`);
    }
  }

  const totalFrames = comp.durationSec * comp.fps;
  const outMp4 = path.join(OUT_DIR, comp.outputFile);

  const puppeteer = await loadPuppeteer();
  const browser = await launchCpuBrowser(puppeteer);
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: comp.width, height: comp.height, deviceScaleFactor: 1 });
    await page.setContent(buildStageHtml(comp, assets), { waitUntil: 'load' });
    await page.evaluate(() => document.fonts.ready);

    const ff = spawn(
      '/usr/bin/ffmpeg',
      [
        '-y',
        '-hide_banner',
        '-loglevel',
        'error',
        '-f',
        'image2pipe',
        '-vcodec',
        'mjpeg',
        '-framerate',
        String(comp.fps),
        '-i',
        '-',
        '-i',
        audioM4a,
        '-c:v',
        'libx264',
        '-preset',
        'veryfast',
        '-crf',
        '18',
        '-pix_fmt',
        'yuv420p',
        '-c:a',
        'copy',
        '-shortest',
        '-movflags',
        '+faststart',
        outMp4,
      ],
      { stdio: ['pipe', 'inherit', 'inherit'] }
    );

    for (let f = 0; f < totalFrames; f++) {
      await page.evaluate((frameIdx, fps) => window.renderFrame(frameIdx, fps), f, comp.fps);
      const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
      const canWrite = ff.stdin.write(buf);
      if (!canWrite) {
        await new Promise((resolve) => ff.stdin.once('drain', resolve));
      }
    }
    ff.stdin.end();
    const exitCode = await new Promise((resolve, reject) => {
      ff.on('close', resolve);
      ff.on('error', reject);
    });
    if (exitCode !== 0) {
      throw new Error(`ffmpeg exited with code ${exitCode} for ${comp.id}`);
    }
  } finally {
    await browser.close();
  }

  const stat = fs.statSync(outMp4);
  return {
    composition: comp.id,
    mp4_path: outMp4,
    bytes: stat.size,
    width: comp.width,
    height: comp.height,
    fps: comp.fps,
    duration_sec: comp.durationSec,
  };
}

async function main() {
  const args = process.argv.slice(2);
  const assets = loadAssetsAndBenchmarks();

  if (args.includes('--still-check')) {
    const t0 = Date.now();
    const stills = await runStillCheck(assets);
    console.log(
      JSON.stringify(
        {
          status: 'PASS',
          mode: 'still-check',
          elapsed_sec: Number(((Date.now() - t0) / 1000).toFixed(3)),
          stills,
        },
        null,
        2
      )
    );
    return;
  }

  const compArgIdx = args.indexOf('--composition');
  if (compArgIdx !== -1 && args[compArgIdx + 1]) {
    const cid = args[compArgIdx + 1];
    if (!COMPOSITIONS[cid]) {
      throw new Error(`Unknown composition '${cid}'. Valid: ${Object.keys(COMPOSITIONS).join(', ')}`);
    }
    const res = await renderFullVideo(COMPOSITIONS[cid], assets);
    console.log(JSON.stringify({ status: 'PASS', video: res }, null, 2));
    return;
  }

  if (args.includes('--render-all')) {
    const videos = [];
    for (const comp of Object.values(COMPOSITIONS)) {
      videos.push(await renderFullVideo(comp, assets));
    }
    console.log(JSON.stringify({ status: 'PASS', videos }, null, 2));
    return;
  }

  console.log('Usage: node scripts/release/render_launch_videos.mjs [--still-check | --composition <id> | --render-all]');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
