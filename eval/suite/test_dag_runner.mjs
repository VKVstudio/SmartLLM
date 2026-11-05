import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { pathToFileURL } from 'node:url';

const NODE_EXE = path.resolve('C:/Program Files/nodejs/node.exe');
const TSC_BIN = path.resolve('C:/projects/VKVstudio/node_modules/typescript/bin/tsc');

async function runSingleTestInWorker(emittedMjsUrl, testId) {
  return new Promise((resolve) => {
    const worker = new Worker(new URL(import.meta.url), {
      workerData: { emittedMjsUrl, testId },
    });
    const timer = setTimeout(() => {
      worker.terminate();
      resolve({
        passed: false,
        durationMs: 3000,
        error: 'Timed out after 3000ms (infinite synchronous loop or unresolved Promise)',
      });
    }, 3000);

    worker.on('message', (msg) => {
      clearTimeout(timer);
      worker.terminate();
      resolve(msg);
    });
    worker.on('error', (err) => {
      clearTimeout(timer);
      worker.terminate();
      resolve({
        passed: false,
        durationMs: 0,
        error: err && err.stack ? err.stack : String(err),
      });
    });
    worker.on('exit', (code) => {
      clearTimeout(timer);
      if (code !== 0) {
        resolve({
          passed: false,
          durationMs: 0,
          error: `Worker exited with code ${code}`,
        });
      }
    });
  });
}

async function executeWorkerTest(emittedMjsUrl, testId) {
  const t0 = performance.now();
  const mod = await import(emittedMjsUrl);
  const { DAGExecutor, DAGCycleError, DAGValidationError } = mod;

  function assert(cond, msg) {
    if (!cond) throw new Error(`Assertion failed: ${msg}`);
  }

  switch (testId) {
    case 1: {
      const dag = new DAGExecutor();
      const order = dag.validate();
      assert(Array.isArray(order) && order.length === 0, 'Empty topological order should be []');
      const rep = await dag.execute();
      assert(rep instanceof Map && rep.size === 0, 'Empty execute should return empty Map');
      break;
    }
    case 2: {
      const dag = new DAGExecutor();
      const orderSeen = [];
      dag
        .addNode({ id: 'A', deps: [], run: async () => { orderSeen.push('A'); return 10; } })
        .addNode({ id: 'B', deps: ['A'], run: async ({ results: r }) => { orderSeen.push('B'); return r.get('A') * 2; } })
        .addNode({ id: 'C', deps: ['B'], run: async ({ results: r }) => { orderSeen.push('C'); return r.get('B') + 5; } });
      const topo = dag.validate();
      assert(topo.indexOf('A') < topo.indexOf('B') && topo.indexOf('B') < topo.indexOf('C'), 'Invalid topo order');
      const rep = await dag.execute();
      assert(orderSeen.join(',') === 'A,B,C', `Expected A,B,C got ${orderSeen.join(',')}`);
      assert(rep.get('C')?.status === 'completed' && rep.get('C')?.result === 25, 'Expected C result 25');
      break;
    }
    case 3: {
      const dag = new DAGExecutor();
      let aRuns = 0;
      dag
        .addNode({ id: 'A', deps: [], run: () => { aRuns++; return 'root'; } })
        .addNode({ id: 'B', deps: ['A'], run: ({ results: r }) => `${r.get('A')}-B` })
        .addNode({ id: 'C', deps: ['A'], run: ({ results: r }) => `${r.get('A')}-C` })
        .addNode({ id: 'D', deps: ['B', 'C'], run: ({ results: r }) => `${r.get('B')}+${r.get('C')}` });
      const rep = await dag.execute();
      assert(aRuns === 1, `Expected A to run once, ran ${aRuns}`);
      assert(rep.get('D')?.result === 'root-B+root-C', `Unexpected D result: ${rep.get('D')?.result}`);
      break;
    }
    case 4: {
      const dag = new DAGExecutor();
      dag
        .addNode({ id: 'A', deps: ['C'], run: () => 1 })
        .addNode({ id: 'B', deps: ['A'], run: () => 2 })
        .addNode({ id: 'C', deps: ['B'], run: () => 3 });
      let caught = null;
      try { dag.validate(); } catch (e) { caught = e; }
      assert(caught instanceof DAGCycleError, `Expected DAGCycleError, got ${caught}`);
      assert(Array.isArray(caught.cycle) && caught.cycle.length >= 3, 'Expected cycle array on DAGCycleError');
      break;
    }
    case 5: {
      const dag = new DAGExecutor();
      dag.addNode({ id: 'A', deps: ['A'], run: () => 1 });
      let caught = null;
      try { dag.validate(); } catch (e) { caught = e; }
      assert(caught instanceof DAGCycleError, `Expected DAGCycleError on self-loop, got ${caught}`);
      break;
    }
    case 6: {
      const dag = new DAGExecutor();
      dag.addNode({ id: 'B', deps: ['NON_EXISTENT'], run: () => 1 });
      let caught = null;
      try { dag.validate(); } catch (e) { caught = e; }
      assert(caught instanceof DAGValidationError, `Expected DAGValidationError, got ${caught}`);
      break;
    }
    case 7: {
      const dag = new DAGExecutor();
      dag.addNode({ id: 'DUP', deps: [], run: () => 1 });
      let caught = null;
      try { dag.addNode({ id: 'DUP', deps: [], run: () => 2 }); } catch (e) { caught = e; }
      assert(caught instanceof DAGValidationError, `Expected DAGValidationError on duplicate ID, got ${caught}`);
      break;
    }
    case 8: {
      const dag = new DAGExecutor();
      let active = 0;
      let maxActive = 0;
      for (let i = 1; i <= 6; i++) {
        dag.addNode({
          id: `P${i}`,
          deps: [],
          run: async () => {
            active++;
            if (active > maxActive) maxActive = active;
            await new Promise((r) => setTimeout(r, 25));
            active--;
            return i;
          },
        });
      }
      const rep = await dag.execute({ maxConcurrency: 2 });
      assert(maxActive <= 2 && maxActive >= 2, `Expected maxActive === 2, got ${maxActive}`);
      assert(rep.size === 6, 'All 6 parallel tasks must complete');
      break;
    }
    case 9: {
      const dag = new DAGExecutor();
      let calls = 0;
      dag.addNode({
        id: 'FLAKY',
        deps: [],
        retries: 2,
        retryDelayMs: 10,
        run: async () => {
          calls++;
          if (calls < 3) throw new Error(`Transient failure #${calls}`);
          return 'RECOVERED';
        },
      });
      const rep = await dag.execute();
      const r = rep.get('FLAKY');
      assert(r?.status === 'completed', `Expected completed, got ${r?.status}`);
      assert(r?.attempts === 3, `Expected 3 attempts, got ${r?.attempts}`);
      assert(r?.result === 'RECOVERED', `Expected RECOVERED, got ${r?.result}`);
      break;
    }
    case 10: {
      const dag = new DAGExecutor();
      let skippedRan = false;
      dag
        .addNode({ id: 'ROOT', deps: [], run: () => 'ok' })
        .addNode({ id: 'FAIL_NODE', deps: ['ROOT'], retries: 1, retryDelayMs: 5, run: () => { throw new Error('Fatal crash'); } })
        .addNode({ id: 'DOWNSTREAM_1', deps: ['FAIL_NODE'], run: () => { skippedRan = true; return 'bad'; } })
        .addNode({ id: 'DOWNSTREAM_2', deps: ['DOWNSTREAM_1'], run: () => { skippedRan = true; return 'bad2'; } })
        .addNode({ id: 'INDEPENDENT', deps: ['ROOT'], run: () => 'independent_ok' });
      const rep = await dag.execute();
      assert(!skippedRan, 'Downstream dependents of failed node must not execute');
      assert(rep.get('FAIL_NODE')?.status === 'failed', 'FAIL_NODE must be failed');
      assert(rep.get('FAIL_NODE')?.attempts === 2, `FAIL_NODE expected 2 attempts, got ${rep.get('FAIL_NODE')?.attempts}`);
      assert(rep.get('DOWNSTREAM_1')?.status === 'skipped' && rep.get('DOWNSTREAM_1')?.attempts === 0, 'DOWNSTREAM_1 must be skipped with 0 attempts');
      assert(rep.get('DOWNSTREAM_2')?.status === 'skipped' && rep.get('DOWNSTREAM_2')?.attempts === 0, 'DOWNSTREAM_2 must be skipped with 0 attempts');
      assert(rep.get('INDEPENDENT')?.status === 'completed' && rep.get('INDEPENDENT')?.result === 'independent_ok', 'INDEPENDENT branch must complete');
      break;
    }
    case 11: {
      const ac = new AbortController();
      const dag = new DAGExecutor();
      dag
        .addNode({ id: 'STEP_1', deps: [], run: async () => { ac.abort(); return 'done_before_abort_check'; } })
        .addNode({ id: 'STEP_2', deps: ['STEP_1'], run: async () => 'should_not_run' });
      const rep = await dag.execute({ signal: ac.signal });
      assert(rep.get('STEP_2')?.status === 'cancelled', `Expected STEP_2 status 'cancelled', got ${rep.get('STEP_2')?.status}`);
      assert(rep.get('STEP_2')?.attempts === 0, `Expected STEP_2 attempts 0, got ${rep.get('STEP_2')?.attempts}`);
      break;
    }
    case 12: {
      const dag = new DAGExecutor();
      dag.addNode({
        id: 'CTX_READER',
        deps: [],
        run: async ({ context }) => {
          await new Promise((r) => setTimeout(r, 10));
          return context.multiplier * 7;
        },
      });
      const rep = await dag.execute({ context: { multiplier: 6 } });
      const nodeRep = rep.get('CTX_READER');
      assert(nodeRep?.status === 'completed' && nodeRep?.result === 42, `Expected 42, got ${nodeRep?.result}`);
      assert(typeof nodeRep?.durationMs === 'number' && nodeRep.durationMs >= 0, 'durationMs must be non-negative number');
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
    { id: 1, name: 'Empty graph validate and execute' },
    { id: 2, name: 'Linear chain topological order and result propagation' },
    { id: 3, name: 'Diamond dependency single execution and fan-in' },
    { id: 4, name: '3-node cycle throws DAGCycleError with cycle array' },
    { id: 5, name: 'Self-dependency cycle A -> A throws DAGCycleError' },
    { id: 6, name: 'Missing dependency throws DAGValidationError' },
    { id: 7, name: 'Duplicate node registration throws DAGValidationError' },
    { id: 8, name: 'Bounded maxConcurrency=2 never exceeds 2 simultaneous tasks' },
    { id: 9, name: 'Flaky task succeeds on retry and records attempts count' },
    { id: 10, name: 'Failed node skips transitive dependents while independent branch finishes' },
    { id: 11, name: 'AbortSignal cancels unstarted downstream tasks' },
    { id: 12, name: 'Shared context passed to nodes and durationMs >= 0 recorded' },
  ];

  async function main() {
    const dagTsPath = process.argv[2];
    if (!dagTsPath || !fs.existsSync(dagTsPath)) {
      console.error(JSON.stringify({ error: `dag.ts not found at ${dagTsPath}` }));
      process.exit(1);
    }

    const absDagTs = path.resolve(dagTsPath);
    const workDir = path.dirname(absDagTs);
    const outDir = path.join(workDir, '.tsc_out');
    fs.mkdirSync(outDir, { recursive: true });

    const noEmitRes = spawnSync(
      NODE_EXE,
      [
        TSC_BIN,
        '--noEmit',
        '--strict',
        '--target', 'ES2022',
        '--module', 'ES2022',
        '--moduleResolution', 'bundler',
        '--skipLibCheck',
        absDagTs,
      ],
      { encoding: 'utf-8', timeout: 30000 }
    );

    const tscPassed = noEmitRes.status === 0;
    const tscDiagnostics = ((noEmitRes.stdout || '') + '\n' + (noEmitRes.stderr || '')).trim();
    const srcText = fs.readFileSync(absDagTs, 'utf-8');
    const explicitAnyMatches = srcText.match(/\b:\s*any\b|\bas\s+any\b|<any>/g) || [];

    spawnSync(
      NODE_EXE,
      [
        TSC_BIN,
        '--target', 'ES2022',
        '--module', 'ES2022',
        '--moduleResolution', 'bundler',
        '--outDir', outDir,
        '--skipLibCheck',
        absDagTs,
      ],
      { encoding: 'utf-8', timeout: 30000 }
    );

    const emittedJs = path.join(outDir, path.basename(absDagTs, '.ts') + '.js');
    const emittedMjs = path.join(outDir, 'dag_compiled.mjs');
    if (!fs.existsSync(emittedJs)) {
      console.log(
        JSON.stringify(
          {
            tsc_strict_passed: tscPassed,
            tsc_exit_code: noEmitRes.status,
            tsc_diagnostics: tscDiagnostics,
            explicit_any_count: explicitAnyMatches.length,
            compiled_js_exists: false,
            tests_passed: 0,
            tests_total: 12,
            results: [],
          },
          null,
          2
        )
      );
      return;
    }

    fs.copyFileSync(emittedJs, emittedMjs);
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
          tsc_exit_code: noEmitRes.status,
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
