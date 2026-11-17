import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { pathToFileURL } from 'node:url';

const require = createRequire(import.meta.url);

function loadTypeScript() {
  const candidates = [
    process.env.SMARTLLM_TS_LIB,
    '/usr/lib/code/extensions/node_modules/typescript/lib/typescript.js',
    '/usr/lib/node_modules/typescript/lib/typescript.js',
    'typescript',
  ].filter(Boolean);
  for (const cand of candidates) {
    try {
      return require(cand);
    } catch {
      // try next candidate
    }
  }
  throw new Error('Could not resolve TypeScript compiler API');
}

async function runSingleTestInWorker(emittedMjsUrl, testId) {
  return new Promise((resolve) => {
    const worker = new Worker(new URL(import.meta.url), {
      workerData: { emittedMjsUrl, testId },
    });
    let settled = false;
    const done = (val) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(val);
    };
    const timer = setTimeout(() => {
      worker.terminate();
      done({
        passed: false,
        durationMs: 3000,
        error: 'Timed out after 3000ms',
      });
    }, 3000);

    worker.on('message', (msg) => {
      worker.terminate();
      done(msg);
    });
    worker.on('error', (err) => {
      worker.terminate();
      done({
        passed: false,
        durationMs: 0,
        error: err && err.stack ? err.stack : String(err),
      });
    });
    worker.on('exit', (code) => {
      if (code !== 0) {
        done({
          passed: false,
          durationMs: 0,
          error: `Worker exited with code ${code}`,
        });
      } else {
        done({
          passed: false,
          durationMs: 0,
          error: 'Worker exited cleanly before Promise settled',
        });
      }
    });
  });
}

async function executeWorkerTest(emittedMjsUrl, testId) {
  const t0 = performance.now();
  const mod = await import(emittedMjsUrl);
  const {
    buildSecurityHeaders,
    generateCsrfToken,
    verifyCsrfToken,
    sanitizeHtmlText,
    FormApiHandler,
  } = mod;

  function assert(cond, msg) {
    if (!cond) throw new Error(`Assertion failed: ${msg}`);
  }

  const SECRET = 'super-secret-hmac-key-2026-smartllm';
  let fakeNow = 1_763_000_000_000;

  switch (testId) {
    case 1: {
      const hdrs = buildSecurityHeaders();
      assert(hdrs['cross-origin-opener-policy'] === 'same-origin', 'Missing COOP same-origin');
      assert(hdrs['cross-origin-embedder-policy'] === 'require-corp', 'Missing COEP require-corp');
      assert(hdrs['cross-origin-resource-policy'] === 'same-origin', 'Missing CORP same-origin');
      assert(
        hdrs['strict-transport-security']?.includes('max-age=63072000') &&
          hdrs['strict-transport-security']?.includes('includeSubDomains'),
        'Invalid HSTS header'
      );
      assert(hdrs['x-content-type-options'] === 'nosniff', 'Missing X-Content-Type-Options nosniff');
      const csp = hdrs['content-security-policy'] || '';
      assert(!csp.includes('unsafe-inline') && !csp.includes('unsafe-eval'), 'CSP must not allow unsafe-inline/eval');
      assert(csp.includes("object-src 'none'"), 'CSP missing object-src none');
      assert(csp.includes("frame-ancestors 'none'"), 'CSP missing frame-ancestors none');
      assert(csp.includes("require-trusted-types-for 'script'"), 'CSP missing Trusted Types');
      assert(csp.includes('sha256-__CSP_SCRIPT__') && csp.includes('sha256-__CSP_STYLE__'), 'CSP missing default placeholders');
      break;
    }
    case 2: {
      const tok = generateCsrfToken('sess-01', fakeNow, SECRET);
      assert(typeof tok === 'string' && tok.includes('.'), 'Invalid token format');
      assert(verifyCsrfToken(tok, 'sess-01', SECRET, fakeNow + 5000) === true, 'Valid CSRF token rejected');
      assert(verifyCsrfToken(tok, 'sess-02', SECRET, fakeNow + 5000) === false, 'Wrong sessionId accepted');
      assert(verifyCsrfToken(tok, 'sess-01', 'wrong-secret-key-0000', fakeNow + 5000) === false, 'Wrong secret accepted');
      assert(verifyCsrfToken(tok, 'sess-01', SECRET, fakeNow + 950_000, 900_000) === false, 'Expired CSRF token accepted');
      break;
    }
    case 3: {
      const dirty = 'Hello \x00\x07<script>alert("xss" & \'1\')</script>';
      const clean = sanitizeHtmlText(dirty);
      assert(!clean.includes('<script>') && !clean.includes('\x00'), 'Control chars or raw tags leaked');
      assert(
        clean.includes('&lt;script&gt;alert(&quot;xss&quot; &amp; &#39;1&#39;)&lt;/script&gt;'),
        `Unexpected sanitized output: ${clean}`
      );
      break;
    }
    case 4: {
      let threw = false;
      try {
        new FormApiHandler({ csrfSecret: 'short', rateLimitMaxRequests: 5, rateLimitWindowMs: 60000 });
      } catch {
        threw = true;
      }
      assert(threw, 'Expected constructor to throw on weak csrfSecret (< 16 chars)');
      break;
    }
    case 5: {
      const handler = new FormApiHandler({
        csrfSecret: SECRET,
        rateLimitMaxRequests: 5,
        rateLimitWindowMs: 60000,
        nowFn: () => fakeNow,
      });
      const res405 = handler.handleRequest({
        method: 'GET',
        clientIp: '10.0.0.1',
        sessionId: 's1',
        contentType: 'application/json',
        body: {},
      });
      assert(res405.status === 405 && res405.body.errorCode === 'METHOD_NOT_ALLOWED', 'Expected 405 on GET');
      assert(res405.headers['allow'] === 'POST', 'Expected Allow: POST on 405');
      assert(res405.headers['cross-origin-opener-policy'] === 'same-origin', 'Security headers missing on 405');

      const res415 = handler.handleRequest({
        method: 'POST',
        clientIp: '10.0.0.1',
        sessionId: 's1',
        contentType: 'text/plain',
        body: {},
      });
      assert(res415.status === 415 && res415.body.errorCode === 'UNSUPPORTED_MEDIA_TYPE', 'Expected 415 on text/plain');
      break;
    }
    case 6: {
      const handler = new FormApiHandler({
        csrfSecret: SECRET,
        rateLimitMaxRequests: 5,
        rateLimitWindowMs: 60000,
        nowFn: () => fakeNow,
      });
      const csrf = generateCsrfToken('s-bot', fakeNow, SECRET);
      const resBot = handler.handleRequest({
        method: 'POST',
        clientIp: '10.0.0.2',
        sessionId: 's-bot',
        contentType: 'application/json; charset=utf-8',
        body: {
          fullName: 'Алексей Смирнов',
          workEmail: 'smirnov@nordic.ru',
          company: 'КБ Север',
          projectTier: 'enterprise',
          budgetUsd: 50000,
          message: 'Нужен расчёт большепролётной арки 72 м.',
          csrfToken: csrf,
          honeypot: 'http://spam-link.example',
          timestampMs: fakeNow,
        },
      });
      assert(resBot.status === 400 && resBot.body.errorCode === 'BOT_DETECTED', 'Honeypot bot not rejected with 400 BOT_DETECTED');
      break;
    }
    case 7: {
      const handler = new FormApiHandler({
        csrfSecret: SECRET,
        rateLimitMaxRequests: 5,
        rateLimitWindowMs: 60000,
        nowFn: () => fakeNow,
      });
      const resCsrf = handler.handleRequest({
        method: 'POST',
        clientIp: '10.0.0.3',
        sessionId: 's-csrf',
        contentType: 'application/json',
        body: {
          fullName: 'Jane Doe',
          workEmail: 'jane@acme.io',
          company: 'Acme Corp',
          projectTier: 'production',
          budgetUsd: 25000,
          message: 'Requesting technical architecture audit.',
          csrfToken: `${fakeNow}.deadbeef0000`,
          timestampMs: fakeNow,
        },
      });
      assert(resCsrf.status === 403 && resCsrf.body.errorCode === 'CSRF_INVALID', 'Invalid CSRF must return 403 CSRF_INVALID');
      break;
    }
    case 8: {
      const handler = new FormApiHandler({
        csrfSecret: SECRET,
        rateLimitMaxRequests: 5,
        rateLimitWindowMs: 60000,
        nowFn: () => fakeNow,
      });
      const csrf = generateCsrfToken('s-val', fakeNow, SECRET);
      const resVal = handler.handleRequest({
        method: 'POST',
        clientIp: '10.0.0.4',
        sessionId: 's-val',
        contentType: 'application/json',
        body: {
          fullName: 'A',
          workEmail: 'not-an-email',
          company: '',
          projectTier: 'invalid_tier',
          budgetUsd: 50,
          message: 'short',
          csrfToken: csrf,
          timestampMs: fakeNow,
        },
      });
      assert(resVal.status === 400 && resVal.body.errorCode === 'VALIDATION_FAILED', 'Expected 400 VALIDATION_FAILED');
      const fields = new Set((resVal.body.errors || []).map((e) => e.field));
      for (const reqField of ['fullName', 'workEmail', 'company', 'projectTier', 'budgetUsd', 'message']) {
        assert(fields.has(reqField), `Missing validation error for field: ${reqField}`);
      }
      break;
    }
    case 9: {
      const handler = new FormApiHandler({
        csrfSecret: SECRET,
        rateLimitMaxRequests: 5,
        rateLimitWindowMs: 60000,
        nowFn: () => fakeNow,
      });
      const csrf = generateCsrfToken('s-ok', fakeNow, SECRET);
      const resOk = handler.handleRequest({
        method: 'POST',
        clientIp: '10.0.0.5',
        sessionId: 's-ok',
        contentType: 'application/json; charset=utf-8',
        body: {
          fullName: '  Дмитрий Волков-Ing. ',
          workEmail: '  D.Volkov@Sever-Arch.RU ',
          company: ' КБ «Северный Горизонт» ',
          projectTier: 'enterprise',
          budgetUsd: 120000,
          message: 'Запрос расчёта узла <CLT-72> & нагрузки "Север".',
          csrfToken: csrf,
          honeypot: '',
          timestampMs: fakeNow,
        },
      });
      assert(resOk.status === 200 && resOk.body.ok === true, `Expected 200 ok, got ${resOk.status}`);
      const d = resOk.body.data;
      assert(d && typeof d.submissionId === 'string' && d.submissionId.length >= 8, 'Missing submissionId');
      assert(d.fullName === 'Дмитрий Волков-Ing.', `Unexpected fullName: ${d.fullName}`);
      assert(d.workEmail === 'd.volkov@sever-arch.ru', `Expected lowercased email, got ${d.workEmail}`);
      assert(
        d.sanitizedMessage === 'Запрос расчёта узла &lt;CLT-72&gt; &amp; нагрузки &quot;Север&quot;.',
        `Unexpected sanitizedMessage: ${d.sanitizedMessage}`
      );
      break;
    }
    case 10: {
      let clock = fakeNow;
      const handler = new FormApiHandler({
        csrfSecret: SECRET,
        rateLimitMaxRequests: 2,
        rateLimitWindowMs: 60000,
        nowFn: () => clock,
      });
      const csrf = generateCsrfToken('s-rl', clock, SECRET);
      const makeReq = () =>
        handler.handleRequest({
          method: 'POST',
          clientIp: '10.0.0.99',
          sessionId: 's-rl',
          contentType: 'application/json',
          body: {
            fullName: 'Elena Rostova',
            workEmail: 'elena@rostova.io',
            company: 'Rostova Acoustic Lab',
            projectTier: 'prototype',
            budgetUsd: 15000,
            message: 'Testing sliding window rate limiter behavior.',
            csrfToken: csrf,
            timestampMs: clock,
          },
        });
      assert(makeReq().status === 200, 'Req 1 should pass');
      clock += 1000;
      assert(makeReq().status === 200, 'Req 2 should pass');
      clock += 1000;
      const r3 = makeReq();
      assert(r3.status === 429 && r3.body.errorCode === 'RATE_LIMITED', 'Req 3 should be 429 RATE_LIMITED');
      assert(Number(r3.headers['retry-after']) > 0, 'Missing positive retry-after header on 429');
      clock += 61000;
      const csrf2 = generateCsrfToken('s-rl', clock, SECRET);
      const r4 = handler.handleRequest({
        method: 'POST',
        clientIp: '10.0.0.99',
        sessionId: 's-rl',
        contentType: 'application/json',
        body: {
          fullName: 'Elena Rostova',
          workEmail: 'elena@rostova.io',
          company: 'Rostova Acoustic Lab',
          projectTier: 'prototype',
          budgetUsd: 15000,
          message: 'Testing sliding window recovery after window expiry.',
          csrfToken: csrf2,
          timestampMs: clock,
        },
      });
      assert(r4.status === 200, 'Req 4 after window expiry should pass');
      break;
    }
  }

  return {
    passed: true,
    durationMs: Math.round((performance.now() - t0) * 100) / 100,
  };
}

if (!isMainThread) {
  executeWorkerTest(workerData.emittedMjsUrl, workerData.testId)
    .then((res) => parentPort.postMessage(res))
    .catch((err) =>
      parentPort.postMessage({
        passed: false,
        durationMs: 0,
        error: err && err.stack ? err.stack : String(err),
      })
    );
} else {
  const TEST_METADATA = [
    { id: 1, name: 'Security headers include COOP/COEP/CORP, HSTS, Trusted Types & CSP hashes' },
    { id: 2, name: 'HMAC-SHA256 CSRF token generation, constant-time verify & expiry' },
    { id: 3, name: 'HTML & ASCII control-char sanitization prevents stored XSS' },
    { id: 4, name: 'Constructor rejects weak csrfSecret (< 16 chars)' },
    { id: 5, name: 'Rejects non-POST (405) and non-JSON Content-Type (415) with security headers' },
    { id: 6, name: 'Honeypot field catches automated bots (400 BOT_DETECTED)' },
    { id: 7, name: 'Tampered CSRF token rejected with 403 CSRF_INVALID' },
    { id: 8, name: 'Invalid payload fields return 400 VALIDATION_FAILED with all 6 field codes' },
    { id: 9, name: 'Valid bilingual RU/EN submission normalizes email and escapes message (200)' },
    { id: 10, name: 'Sliding-window IP rate limiter enforces 429 + retry-after and resets after window' },
  ];

  async function main() {
    const tsPath = process.argv[2];
    if (!tsPath || !fs.existsSync(tsPath)) {
      console.error(JSON.stringify({ error: `form_handler.ts not found at ${tsPath}` }));
      process.exit(1);
    }

    const absTs = path.resolve(tsPath);
    const workDir = path.dirname(absTs);
    const outDir = path.join(workDir, '.tsc_out_backend');
    fs.mkdirSync(outDir, { recursive: true });
    const nodeShimsPath = path.join(outDir, 'node_builtins.d.ts');
    fs.writeFileSync(
      nodeShimsPath,
      [
        'declare class Buffer extends Uint8Array {',
        '  static from(data: string, encoding?: string): Buffer;',
        '  static from(data: ArrayBuffer | SharedArrayBuffer | ReadonlyArray<number> | Uint8Array): Buffer;',
        '  static alloc(size: number, fill?: number | string): Buffer;',
        '  toString(encoding?: string): string;',
        '}',
        'declare module "node:crypto" {',
        '  export interface Hmac {',
        '    update(data: string | Uint8Array): this;',
        '    digest(): Buffer;',
        '    digest(encoding: "hex" | "base64" | "base64url"): string;',
        '  }',
        '  export function createHmac(algorithm: string, key: string | Uint8Array): Hmac;',
        '  export function createHash(algorithm: string): Hmac;',
        '  export function timingSafeEqual(a: Uint8Array, b: Uint8Array): boolean;',
        '  export function randomUUID(): string;',
        '  export function randomBytes(size: number): Buffer;',
        '}',
        'declare module "crypto" {',
        '  export * from "node:crypto";',
        '}',
      ].join('\n'),
      'utf-8'
    );

    const ts = loadTypeScript();
    const srcText = fs.readFileSync(absTs, 'utf-8');
    const explicitAnyMatches = srcText.match(/\b:\s*any\b|\bas\s+any\b|<any>/g) || [];

    const options = {
      noEmit: true,
      strict: true,
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.ES2022,
      moduleResolution: ts.ModuleResolutionKind.Bundler,
      skipLibCheck: true,
    };

    const program = ts.createProgram([nodeShimsPath, absTs], options);
    const diagnostics = ts.getPreEmitDiagnostics(program);
    const realDiagnostics = diagnostics;

    const tscPassed = realDiagnostics.length === 0;
    const tscDiagnostics = realDiagnostics
      .map((d) => ts.flattenDiagnosticMessageText(d.messageText, '\n'))
      .join('\n');

    const transpiled = ts.transpileModule(srcText, {
      compilerOptions: {
        target: ts.ScriptTarget.ES2022,
        module: ts.ModuleKind.ES2022,
      },
    });

    const emittedMjs = path.join(outDir, 'form_handler_compiled.mjs');
    fs.writeFileSync(emittedMjs, transpiled.outputText, 'utf-8');
    const emittedMjsUrl = pathToFileURL(emittedMjs).href;

    const results = [];
    for (const meta of TEST_METADATA) {
      const r = await runSingleTestInWorker(emittedMjsUrl, meta.id);
      results.push({ id: meta.id, name: meta.name, ...r });
    }

    const passedCount = results.filter((r) => r.passed).length;
    console.log(
      JSON.stringify(
        {
          tsc_strict_passed: tscPassed,
          tsc_diagnostics: tscDiagnostics,
          explicit_any_count: explicitAnyMatches.length,
          compiled_js_exists: true,
          tests_passed: passedCount,
          tests_total: results.length,
          results,
        },
        null,
        2
      )
    );
  }

  main().catch((err) => {
    console.error(JSON.stringify({ fatal: String(err) }));
    process.exit(1);
  });
}
