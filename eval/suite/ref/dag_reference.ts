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

export class DAGCycleError extends Error {
  public readonly cycle: readonly string[];
  constructor(cycle: readonly string[]) {
    super(`Cycle detected in DAG: ${cycle.join(" -> ")}`);
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

export class DAGExecutor<TContext = Record<string, unknown>> {
  private readonly nodes = new Map<string, TaskNode<TContext, unknown>>();

  public addNode<TResult>(node: TaskNode<TContext, TResult>): this {
    if (!node.id || typeof node.id !== "string") {
      throw new DAGValidationError("Node ID must be a non-empty string.");
    }
    if (this.nodes.has(node.id)) {
      throw new DAGValidationError(`Duplicate node ID: "${node.id}"`);
    }
    this.nodes.set(node.id, node as TaskNode<TContext, unknown>);
    return this;
  }

  public validate(): string[] {
    for (const [id, node] of this.nodes.entries()) {
      for (const dep of node.deps) {
        if (!this.nodes.has(dep)) {
          throw new DAGValidationError(`Node "${id}" depends on unknown node "${dep}"`);
        }
      }
    }

    // Cycle detection via DFS coloring (0 = unvisited, 1 = visiting, 2 = visited)
    const state = new Map<string, 0 | 1 | 2>();
    const parent = new Map<string, string>();
    for (const id of this.nodes.keys()) {
      state.set(id, 0);
    }

    const visit = (u: string, stack: string[]): void => {
      state.set(u, 1);
      stack.push(u);
      const node = this.nodes.get(u)!;
      // Traverse edges dep -> u (or u -> dep; cycle is identical in reverse)
      for (const dep of node.deps) {
        const depState = state.get(dep) ?? 0;
        if (depState === 1) {
          const idx = stack.indexOf(dep);
          const cycleNodes = stack.slice(idx).reverse();
          cycleNodes.push(dep);
          throw new DAGCycleError(cycleNodes);
        }
        if (depState === 0) {
          parent.set(dep, u);
          visit(dep, stack);
        }
      }
      stack.pop();
      state.set(u, 2);
    };

    for (const id of this.nodes.keys()) {
      if (state.get(id) === 0) {
        visit(id, []);
      }
    }

    // Kahn's algorithm for deterministic topological order
    const inDegree = new Map<string, number>();
    const dependents = new Map<string, string[]>();
    for (const id of this.nodes.keys()) {
      inDegree.set(id, 0);
      dependents.set(id, []);
    }
    for (const [id, node] of this.nodes.entries()) {
      inDegree.set(id, node.deps.length);
      for (const dep of node.deps) {
        dependents.get(dep)!.push(id);
      }
    }

    const queue: string[] = [];
    for (const [id, deg] of inDegree.entries()) {
      if (deg === 0) queue.push(id);
    }

    const order: string[] = [];
    while (queue.length > 0) {
      const u = queue.shift()!;
      order.push(u);
      for (const v of dependents.get(u)!) {
        const nextDeg = (inDegree.get(v) ?? 0) - 1;
        inDegree.set(v, nextDeg);
        if (nextDeg === 0) queue.push(v);
      }
    }
    return order;
  }

  public async execute(
    options?: DAGExecutionOptions<TContext>
  ): Promise<Map<string, NodeExecutionReport>> {
    this.validate();

    const maxConcurrency = options?.maxConcurrency ?? Number.POSITIVE_INFINITY;
    if (maxConcurrency <= 0 || Number.isNaN(maxConcurrency)) {
      throw new DAGValidationError("maxConcurrency must be a positive number");
    }

    const context = (options?.context ?? ({} as TContext)) as TContext;
    const fallbackController = new AbortController();
    const signal = options?.signal ?? fallbackController.signal;

    const reports = new Map<string, NodeExecutionReport>();
    const completedResults = new Map<string, unknown>();
    if (this.nodes.size === 0) {
      return reports;
    }

    const inDegree = new Map<string, number>();
    const dependents = new Map<string, string[]>();
    for (const id of this.nodes.keys()) {
      inDegree.set(id, 0);
      dependents.set(id, []);
    }
    for (const [id, node] of this.nodes.entries()) {
      inDegree.set(id, node.deps.length);
      for (const dep of node.deps) {
        dependents.get(dep)!.push(id);
      }
    }

    const readyQueue: string[] = [];
    for (const [id, deg] of inDegree.entries()) {
      if (deg === 0) readyQueue.push(id);
    }

    let activeCount = 0;

    const markSkippedSubtree = (failedId: string): void => {
      const q: string[] = [...(dependents.get(failedId) ?? [])];
      while (q.length > 0) {
        const curr = q.shift()!;
        if (reports.has(curr)) continue;
        reports.set(curr, {
          id: curr,
          status: "skipped",
          attempts: 0,
          durationMs: 0,
        });
        for (const nxt of dependents.get(curr) ?? []) {
          if (!reports.has(nxt)) q.push(nxt);
        }
      }
    };

    return new Promise<Map<string, NodeExecutionReport>>((resolve) => {
      const schedule = (): void => {
        if (signal.aborted) {
          for (const id of this.nodes.keys()) {
            if (!reports.has(id) && !inFlight.has(id)) {
              reports.set(id, {
                id,
                status: "cancelled",
                attempts: 0,
                durationMs: 0,
              });
            }
          }
          if (activeCount === 0 && reports.size === this.nodes.size) {
            resolve(reports);
          }
          return;
        }

        while (activeCount < maxConcurrency && readyQueue.length > 0) {
          const nextId = readyQueue.shift()!;
          if (reports.has(nextId)) continue;

          if (signal.aborted) {
            reports.set(nextId, {
              id: nextId,
              status: "cancelled",
              attempts: 0,
              durationMs: 0,
            });
            continue;
          }

          activeCount++;
          inFlight.add(nextId);
          void runSingleNode(nextId).finally(() => {
            inFlight.delete(nextId);
            activeCount--;
            if (reports.size === this.nodes.size && activeCount === 0) {
              resolve(reports);
            } else {
              schedule();
            }
          });
        }

        if (reports.size === this.nodes.size && activeCount === 0) {
          resolve(reports);
        }
      };

      const inFlight = new Set<string>();

      const runSingleNode = async (id: string): Promise<void> => {
        const node = this.nodes.get(id)!;
        const maxRetries = Math.max(0, node.retries ?? 0);
        const baseDelay = Math.max(0, node.retryDelayMs ?? 0);
        const t0 = performance.now();
        let attempts = 0;
        let lastErr: Error | undefined;

        for (let attempt = 0; attempt <= maxRetries; attempt++) {
          if (signal.aborted) {
            reports.set(id, {
              id,
              status: "cancelled",
              attempts,
              durationMs: Math.round((performance.now() - t0) * 100) / 100,
            });
            return;
          }
          attempts++;
          try {
            const val = await node.run({
              results: completedResults,
              context,
              signal,
            });
            const durationMs = Math.round((performance.now() - t0) * 100) / 100;
            completedResults.set(id, val);
            reports.set(id, {
              id,
              status: "completed",
              attempts,
              durationMs,
              result: val,
            });
            for (const depId of dependents.get(id) ?? []) {
              if (reports.has(depId)) continue;
              const rem = (inDegree.get(depId) ?? 1) - 1;
              inDegree.set(depId, rem);
              if (rem === 0) {
                readyQueue.push(depId);
              }
            }
            return;
          } catch (err) {
            lastErr = err instanceof Error ? err : new Error(String(err));
            if (attempt < maxRetries && baseDelay > 0) {
              const delay = baseDelay * Math.pow(2, attempt);
              await new Promise((r) => setTimeout(r, delay));
            }
          }
        }

        const durationMs = Math.round((performance.now() - t0) * 100) / 100;
        reports.set(id, {
          id,
          status: "failed",
          attempts,
          durationMs,
          error: lastErr,
        });
        markSkippedSubtree(id);
      };

      schedule();
    });
  }
}
