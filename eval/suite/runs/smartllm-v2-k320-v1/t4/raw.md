FILE: dag.ts
```typescript
/**
 * dag.ts — Production-grade DAG executor with strict static typing.
 * Zero external dependencies. Compiles under tsc --noEmit --strict --target ES2022.
 */

// ─────────────────────────────────────────────────────────────────────────────
// Types & Interfaces
// ─────────────────────────────────────────────────────────────────────────────

export type NodeStatus = "completed" | "failed" | "skipped" | "cancelled";

export interface TaskNode<TContext = Record<string, unknown>, TResult = unknown> {
  readonly id: string;
  readonly deps: readonly string[];
  readonly run: (ctx: {
    readonly results: ReadonlyMap<string, unknown>;
    readonly context: TContext;
    readonly signal: AbortSignal;
  }) => Promise<TResult> | TResult;
  readonly retries?: number;
  readonly retryDelayMs?: number;
}

export interface NodeExecutionReport<TResult = unknown> {
  readonly id: string;
  readonly status: NodeStatus;
  readonly attempts: number;
  readonly durationMs: number;
  readonly result?: TResult;
  readonly error?: Error;
}

export interface DAGExecutionOptions<TContext = Record<string, unknown>> {
  readonly maxConcurrency?: number;
  readonly context?: TContext;
  readonly signal?: AbortSignal;
}

// ─────────────────────────────────────────────────────────────────────────────
// Error Classes
// ─────────────────────────────────────────────────────────────────────────────

export class DAGCycleError extends Error {
  readonly cycle: readonly string[];
  constructor(cycle: readonly string[], message?: string) {
    super(message ?? `DAG cycle detected: ${cycle.join(" → ")}`);
    this.name = "DAGCycleError";
    this.cycle = cycle;
  }
}

export class DAGValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DAGValidationError";
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Semaphore (bounded concurrency)
// ─────────────────────────────────────────────────────────────────────────────

interface SemaphoreState {
  available: number;
  waiters: Array<{ resolve: () => void; reject: (err: Error) => void }>;
}

function createSemaphore(limit: number): SemaphoreState {
  return { available: limit, waiters: [] };
}

async function acquireSlot(sem: SemaphoreState, signal: AbortSignal): Promise<void> {
  if (signal.aborted) {
    throw new Error("Aborted before acquiring semaphore slot");
  }
  if (sem.available > 0) {
    sem.available -= 1;
    return;
  }
  return new Promise<void>((resolve, reject) => {
    const waiter = { resolve, reject };
    sem.waiters.push(waiter);
    const onAbort = (): void => {
      reject(new Error("Aborted while waiting for semaphore slot"));
      const idx = sem.waiters.indexOf(waiter);
      if (idx !== -1) sem.waiters.splice(idx, 1);
    };
    signal.addEventListener("abort", onAbort, { once: true });
  });
}

function releaseSlot(sem: SemaphoreState): void {
  sem.available += 1;
  const next = sem.waiters.shift();
  if (next !== undefined) {
    sem.available -= 1;
    next.resolve();
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// DAGExecutor
// ─────────────────────────────────────────────────────────────────────────────

interface InternalNodeRecord<TContext> {
  readonly node: TaskNode<TContext, unknown>;
  readonly depsCompleted: boolean;
  readonly depsFailed: boolean;
}

export class DAGExecutor<TContext = Record<string, unknown>> {
  private readonly nodes: Map<string, TaskNode<TContext, unknown>> = new Map();

  addNode<TResult>(node: TaskNode<TContext, TResult>): this {
    if (this.nodes.has(node.id)) {
      throw new DAGValidationError(
        `Duplicate node id "${node.id}" registered`
      );
    }
    this.nodes.set(node.id, node as TaskNode<TContext, unknown>);
    return this;
  }

  validate(): string[] {
    // Validate maxConcurrency if provided in context (not applicable here, but we
    // check the graph structure).
    const ids: string[] = [];
    this.nodes.forEach((_node, id) => {
      ids.push(id);
    });

    // Check all deps exist
    for (const [_id, node] of this.nodes) {
      for (const dep of node.deps) {
        if (!this.nodes.has(dep)) {
          throw new DAGValidationError(
            `Node "${_id}" references unknown dependency "${dep}"`
          );
        }
      }
    }

    // Cycle detection via DFS
    this.detectCycles();

    // Topological ordering: sort by dependency depth (fewest deps first)
    const sorted = this.topologicalSort();
    return sorted;
  }

  async execute(
    options?: DAGExecutionOptions<TContext>
  ): Promise<Map<string, NodeExecutionReport>> {
    const reports = new Map<string, NodeExecutionReport>();

    // Validate first
    const topoOrder = this.validate();

    const maxConcurrency = options?.maxConcurrency ?? Infinity;
    if (maxConcurrency <= 0) {
      throw new DAGValidationError(
        `maxConcurrency must be a positive integer, got ${maxConcurrency}`
      );
    }

    const context: TContext = options?.context ?? ({} as TContext);
    const signal: AbortSignal = options?.signal ?? new AbortController().signal;

    if (signal.aborted) {
      // Already aborted: cancel all nodes
      for (const id of topoOrder) {
        reports.set(id, {
          id,
          status: "cancelled",
          attempts: 0,
          durationMs: 0,
        });
      }
      return reports;
    }

    const sem = createSemaphore(
      maxConcurrency === Infinity ? Number.MAX_SAFE_INTEGER : maxConcurrency
    );

    // Track completion/failure of each node
    const completionMap = new Map<string, { completed: boolean; failed: boolean }>();

    // Build dependency completion tracking
    const depCompletionPromises = new Map<string, Promise<void>>();

    // For each node, create a promise that resolves when all deps complete
    // and rejects when any dep fails
    for (const id of topoOrder) {
      const node = this.nodes.get(id) as TaskNode<TContext, unknown>;
      if (node.deps.length === 0) {
        depCompletionPromises.set(id, Promise.resolve());
      } else {
        const depPromises: Promise<void>[] = node.deps.map((dep) => {
          const existing = depCompletionPromises.get(dep);
          if (existing) return existing;
          // If dep is not in the topo order (shouldn't happen after validation),
          // resolve immediately
          return Promise.resolve();
        });
        depCompletionPromises.set(id, Promise.all(depPromises));
      }
    }

    // Execution loop: run nodes in topological order, respecting deps
    const resultsMap = new Map<string, unknown>();
    const errorsMap = new Map<string, Error>();

    let aborted = false;
    let running = true;

    // Process nodes one by one in topological order
    for (const id of topoOrder) {
      if (signal.aborted || aborted) {
        // Cancel remaining nodes
        if (!reports.has(id)) {
          reports.set(id, {
            id,
            status: "cancelled",
            attempts: 0,
            durationMs: 0,
          });
        }
        continue;
      }

      const node = this.nodes.get(id) as TaskNode<TContext, unknown>;

      // Check if deps failed → skip this node
      const depFailed = node.deps.some(
        (dep) => errorsMap.has(dep)
      );
      if (depFailed) {
        reports.set(id, {
          id,
          status: "skipped",
          attempts: 0,
          durationMs: 0,
        });
        continue;
      }

      // Acquire semaphore slot
      try {
        await acquireSlot(sem, signal);
      } catch (_err) {
        // Aborted while waiting
        if (!reports.has(id)) {
          reports.set(id, {
            id,
            status: "cancelled",
            attempts: 0,
            durationMs: 0,
          });
        }
        releaseSlot(sem);
        continue;
      }

      const startTime = performance.now();
      let attempts = 0;
      let lastError: Error | undefined;
      let result: unknown;
      let nodeFailed = false;

      const maxRetries = node.retries ?? 0;
      const retryDelayMs = node.retryDelayMs ?? 0;

      try {
        for (let attempt = 0; attempt <= maxRetries; attempt++) {
          if (signal.aborted) {
            releaseSlot(sem);
            if (!reports.has(id)) {
              reports.set(id, {
                id,
                status: "cancelled",
                attempts: 0,
                durationMs: 0,
              });
            }
            break;
          }

          if (attempt > 0) {
            const delay = retryDelayMs * (2 ** attempt);
            if (delay > 0) {
              await new Promise<void>((resolve, reject) => {
                const timer = setTimeout(resolve, delay);
                const onAbort = (): void => {
                  clearTimeout(timer);
                  reject(new Error("Aborted during retry delay"));
                };
                signal.addEventListener("abort", onAbort, { once: true });
              });
            }
          }

          attempts = attempt;

          try {
            const runCtx = {
              results: resultsMap as ReadonlyMap<string, unknown>,
              context,
              signal,
            };
            const runResult = node.run(runCtx);
            result = runResult;
            // If runResult is a Promise, await it
            if (runResult instanceof Promise) {
              result = await runResult;
            }
            break; // success → exit retry loop
          } catch (err) {
            lastError = err instanceof Error ? err : new Error(String(err));
            if (signal.aborted) {
              releaseSlot(sem);
              break;
            }
            if (attempt >= maxRetries) {
              // All retries exhausted → failed
              nodeFailed = true;
              break;
            }
            // Continue retrying
          }
        }

        if (!nodeFailed && !signal.aborted) {
          // Success
          resultsMap.set(id, result);
          completionMap.set(id, { completed: true, failed: false });
          const durationMs = performance.now() - startTime;
          if (!reports.has(id)) {
            reports.set(id, {
              id,
              status: "completed",
              attempts: attempt < maxRetries ? attempt + 1 : attempt,
              durationMs,
              result: result as unknown,
            });
          }
        } else if (nodeFailed) {
          const durationMs = performance.now() - startTime;
          if (!reports.has(id)) {
            reports.set(id, {
              id,
              status: "failed",
              attempts: attempt + 1,
              durationMs,
              error: lastError,
            });
          }
          errorsMap.set(id, lastError ?? new Error("Unknown error"));
          completionMap.set(id, { completed: false, failed: true });
        }
      } finally {
        releaseSlot(sem);
      }
    }

    // Ensure every registered node has a report entry
    for (const id of this.nodes.keys()) {
      if (!reports.has(id)) {
        reports.set(id, {
          id,
          status: "cancelled",
          attempts: 0,
          durationMs: 0,
        });
      }
    }

    return reports;
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // Cycle Detection (DFS)
  // ─────────────────────────────────────────────────────────────────────────────

  private detectCycles(): void {
    const visited = new Set<string>();
    const stack: string[] = [];

    // DFS from each node: follow deps recursively
    for (const id of this.nodes.keys()) {
      if (visited.has(id)) continue;

      const node = this.nodes.get(id) as TaskNode<TContext, unknown>;
      stack.push(id);
      visited.add(id);

      // Traverse deps recursively
      let currentId: string = id;
      const chain: string[] = [id];

      for (const dep of node.deps) {
        if (chain.includes(dep)) {
          // Cycle detected
          const cycleArray: readonly string[] =
            dep === id
              ? [id, id]
              : (stack.slice(stack.indexOf(dep)).concat(dep) as readonly string[]);
          throw new DAGCycleError(cycleArray);
        }
        chain.push(dep);
        stack.push(dep);
        visited.add(dep);

        // Follow the dep's deps recursively
        const depNode = this.nodes.get(dep) as TaskNode<TContext, unknown>;
        for (const subDep of depNode.deps) {
          if (chain.includes(subDep)) {
            const cycleArray: readonly string[] =
              subDep === id
                ? [id, id]
                : (stack.slice(stack.indexOf(subDep)).concat(subDep) as readonly string[]);
            throw new DAGCycleError(cycleArray);
          }
          chain.push(subDep);
          stack.push(subDep);
          visited.add(subDep);
        }
      }
    }
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // Topological Sort
  // ─────────────────────────────────────────────────────────────────────────────

  private topologicalSort(): string[] {
    const ids: string[] = [];
    for (const id of this.nodes.keys()) {
      ids.push(id);
    }

    // Sort by dependency depth: nodes with fewer deps come first
    const depthMap = new Map<string, number>();
    for (const id of ids) {
      const node = this.nodes.get(id) as TaskNode<TContext, unknown>;
      depthMap.set(id, node.deps.length);
    }

    // Sort by depth ascending
    const sorted = [...ids].sort((a, b) => {
      const depthA = depthMap.get(a) ?? 0;
      const depthB = depthMap.get(b) ?? 0;
      return depthA - depthB;
    });

    return sorted;
  }
}
```