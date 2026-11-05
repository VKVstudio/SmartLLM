FILE: dag.ts
```typescript
export type NodeStatus = "completed" | "failed" | "skipped" | "cancelled";

export interface TaskNode<TContext = Record<string, unknown>, TResult = unknown> {
  id: string;
  deps: readonly string[];
  run: (ctx: {
    readonly results: ReadonlyMap<string, unknown>;
    readonly context: TContext;
    readonly signal: AbortSignal;
  }) => Promise<TResult> | TResult;
  retries?: number;
  retryDelayMs?: number;
}

export interface NodeExecutionReport<TResult = unknown> {
  id: string;
  status: NodeStatus;
  attempts: number;
  durationMs: number;
  result?: TResult;
  error?: Error;
}

export interface DAGExecutionOptions<TContext = Record<string, unknown>> {
  maxConcurrency?: number;
  context?: TContext;
  signal?: AbortSignal;
}

export class DAGCycleError extends Error {
  readonly cycle: readonly string[];

  constructor(cycle: readonly string[]) {
    super(`DAG cycle detected: ${cycle.join(" -> ")}`);
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

interface StoredNode {
  id: string;
  deps: readonly string[];
  run: TaskNode["run"];
  retries: number;
  retryDelayMs: number;
}

interface Frame {
  id: string;
  deps: readonly string[];
  depIndex: number;
}

class MinStringHeap {
  private readonly items: string[] = [];

  constructor(initial: readonly string[] = []) {
    this.items = [...initial];
    this.heapify();
  }

  get size(): number {
    return this.items.length;
  }

  push(value: string): void {
    this.items.push(value);
    this.bubbleUp(this.items.length - 1);
  }

  pop(): string | undefined {
    if (this.items.length === 0) {
      return undefined;
    }

    const top = this.items[0];
    const last = this.items.pop();

    if (this.items.length > 0 && last !== undefined) {
      this.items[0] = last;
      this.bubbleDown(0);
    }

    return top;
  }

  private heapify(): void {
    for (let i = (this.items.length >> 1) - 1; i >= 0; i -= 1) {
      this.bubbleDown(i);
    }
  }

  private bubbleUp(index: number): void {
    while (index > 0) {
      const parent = (index - 1) >> 1;

      if (this.items[index] >= this.items[parent]) {
        break;
      }

      const tmp = this.items[index];
      this.items[index] = this.items[parent];
      this.items[parent] = tmp;
      index = parent;
    }
  }

  private bubbleDown(index: number): void {
    const length = this.items.length;

    while (true) {
      const left = (index << 1) + 1;
      const right = left + 1;
      let smallest = index;

      if (left < length && this.items[left] < this.items[smallest]) {
        smallest = left;
      }

      if (right < length && this.items[right] < this.items[smallest]) {
        smallest = right;
      }

      if (smallest === index) {
        break;
      }

      const tmp = this.items[index];
      this.items[index] = this.items[smallest];
      this.items[smallest] = tmp;
      index = smallest;
    }
  }
}

function asError(value: unknown): Error {
  if (value instanceof Error) {
    return value;
  }

  return new Error(typeof value === "string" ? value : String(value));
}

function normalizeDeps(deps: readonly string[]): string[] {
  const seen = new Set<string>();
  const normalized: string[] = [];

  for (const dep of deps) {
    if (!seen.has(dep)) {
      seen.add(dep);
      normalized.push(dep);
    }
  }

  return normalized;
}

function sortedUnique(values: Iterable<string>): string[] {
  return [...new Set(values)].sort();
}

function createAbortPromise(signal: AbortSignal): Promise<"aborted"> {
  if (signal.aborted) {
    return Promise.resolve("aborted");
  }

  return new Promise<"aborted">((resolve) => {
    signal.addEventListener(
      "abort",
      () => {
        resolve("aborted");
      },
      { once: true }
    );
  });
}

function delay(ms: number, signal: AbortSignal): Promise<void | "aborted"> {
  if (ms <= 0) {
    return Promise.resolve();
  }

  if (signal.aborted) {
    return Promise.resolve("aborted");
  }

  return new Promise<void | "aborted">((resolve) => {
    const timer = setTimeout(() => {
      signal.removeEventListener("abort", onAbort);
      resolve();
    }, ms);

    function onAbort(): void {
      clearTimeout(timer);
      resolve("aborted");
    }

    signal.addEventListener("abort", onAbort, { once: true });
  });
}

export class DAGExecutor<TContext = Record<string, unknown>> {
  private readonly nodes = new Map<string, StoredNode>();

  addNode<TResult>(node: TaskNode<TContext, TResult>): this {
    if (this.nodes.has(node.id)) {
      throw new DAGValidationError(`Duplicate node id: ${node.id}`);
    }

    const retries = node.retries ?? 0;
    const retryDelayMs = node.retryDelayMs ?? 0;

    if (!Number.isInteger(retries) || retries < 0) {
      throw new DAGValidationError(`Invalid retries for node ${node.id}: ${node.retries}`);
    }

    if (!Number.isFinite(retryDelayMs) || retryDelayMs < 0) {
      throw new DAGValidationError(`Invalid retryDelayMs for node ${node.id}: ${node.retryDelayMs}`);
    }

    this.nodes.set(node.id, {
      id: node.id,
      deps: normalizeDeps(node.deps),
      run: node.run as StoredNode["run"],
      retries,
      retryDelayMs,
    });

    return this;
  }

  validate(): string[] {
    const ids = [...this.nodes.keys()].sort();
    const idSet = new Set(ids);

    for (const id of ids) {
      const node = this.nodes.get(id);

      if (!node) {
        throw new DAGValidationError(`Internal error: missing node ${id}`);
      }

      for (const dep of node.deps) {
        if (!idSet.has(dep)) {
          throw new DAGValidationError(`Missing dependency "${dep}" for node "${id}"`);
        }
      }
    }

    this.detectCycle(ids);

    return this.topologicalOrder(ids);
  }

  async execute(
    options: DAGExecutionOptions<TContext> = {}
  ): Promise<Map<string, NodeExecutionReport>> {
    const maxConcurrency = options.maxConcurrency;

    if (maxConcurrency !== undefined) {
      if (maxConcurrency === Number.POSITIVE_INFINITY) {
        // Valid: unlimited concurrency.
      } else if (
        !Number.isFinite(maxConcurrency) ||
        maxConcurrency <= 0 ||
        !Number.isInteger(maxConcurrency)
      ) {
        throw new DAGValidationError(`Invalid maxConcurrency: ${String(maxConcurrency)}`);
      }
    }

    const order = this.validate();
    const reports = new Map<string, NodeExecutionReport>();
    const reported = new Set<string>();

    const ids = [...this.nodes.keys()].sort();
    const adjacency = new Map<string, string[]>();
    const indegree = new Map<string, number>();

    for (const id of ids) {
      adjacency.set(id, []);
      indegree.set(id, 0);
    }

    for (const id of ids) {
      const node = this.nodes.get(id);

      if (!node) {
        throw new DAGValidationError(`Internal error: missing node ${id}`);
      }

      indegree.set(id, node.deps.length);

      for (const dep of node.deps) {
        const dependents = adjacency.get(dep);

        if (!dependents) {
          throw new DAGValidationError(`Internal error: missing adjacency for ${dep}`);
        }

        dependents.push(id);
      }
    }

    const signal = options.signal ?? new AbortController().signal;
    const context = options.context ?? ({} as TContext);
    const results = new Map<string, unknown>();

    function markNode(
      id: string,
      status: NodeStatus,
      attempts: number,
      error?: Error
    ): void {
      if (reported.has(id)) {
        return;
      }

      reported.add(id);

      const report: NodeExecutionReport = {
        id,
        status,
        attempts,
        durationMs: 0,
      };

      if (error !== undefined) {
        report.error = error;
      }

      reports.set(id, report);
    }

    function propagateStatus(
      startId: string,
      status: NodeStatus,
      error?: Error
    ): void {
      const queue: string[] = [startId];
      const visited = new Set<string>([startId]);

      while (queue.length > 0) {
        const current = queue.shift();

        if (current === undefined) {
          continue;
        }

        if (current !== startId) {
          markNode(current, status, 0, error);
        }

        const dependents = adjacency.get(current) ?? [];

        for (const dependent of dependents) {
          if (!visited.has(dependent)) {
            visited.add(dependent);
            queue.push(dependent);
          }
        }
      }
    }

    function markAllUnreported(status: NodeStatus, attempts: number, error?: Error): void {
      for (const id of ids) {
        markNode(id, status, attempts, error);
      }
    }

    const ready = new MinStringHeap();

    for (const id of ids) {
      if ((indegree.get(id) ?? 0) === 0) {
        ready.push(id);
      }
    }

    let activeCount = 0;
    let stopped = false;

    function stopOnAbort(): void {
      if (!stopped) {
        stopped = true;
      }

      markAllUnreported("cancelled", 0);
    }

    if (signal.aborted) {
      markAllUnreported("cancelled", 0);
      return reports;
    }

    signal.addEventListener("abort", stopOnAbort, { once: true });

    async function runNode(id: string): Promise<void> {
      const node = this.nodes.get(id);

      if (!node) {
        throw new DAGValidationError(`Internal error: missing node ${id}`);
      }

      if (reported.has(id)) {
        return;
      }

      if (signal.aborted) {
        markNode(id, "cancelled", 0);
        propagateStatus(id, "cancelled");
        return;
      }

      const startedAt = Date.now();
      const maxAttempts = node.retries + 1;
      let attempts = 0;

      while (attempts < maxAttempts) {
        if (signal.aborted) {
          markNode(id, "cancelled", attempts);
          propagateStatus(id, "cancelled");
          return;
        }

        attempts += 1;

        const task = node.run({
          results,
          context,
          signal,
        });

        const taskPromise = Promise.resolve(task).then(
          (result) => ({ type: "completed" as const, result }),
          (error) => ({ type: "failed" as const, error: asError(error) })
        );

        const race = await Promise.race([
          taskPromise,
          createAbortPromise(signal).then(() => ({ type: "aborted" as const })),
        ]);

        if (race.type === "aborted") {
          taskPromise.catch(() => undefined);
          markNode(id, "cancelled", attempts);
          propagateStatus(id, "cancelled");
          return;
        }

        if (race.type === "completed") {
          results.set(id, race.result);

          const report: NodeExecutionReport = {
            id,
            status: "completed",
            attempts,
            durationMs: Date.now() - startedAt,
            result: race.result,
          };

          reported.add(id);
          reports.set(id, report);

          const dependents = adjacency.get(id) ?? [];

          for (const dependent of dependents) {
            const remaining = indegree.get(dependent) ?? 0;

            if (remaining > 0) {
              indegree.set(dependent, remaining - 1);

              if (indegree.get(dependent) === 0 && !reported.has(dependent)) {
                ready.push(dependent);
              }
            }
          }

          return;
        }

        const failedAttempt = attempts;

        if (failedAttempt < maxAttempts) {
          const delayMs = node.retryDelayMs * (2 ** (failedAttempt - 1));

          if (delayMs > 0) {
            const delayed = await delay(delayMs, signal);

            if (delayed === "aborted" || signal.aborted) {
              markNode(id, "cancelled", attempts);
              propagateStatus(id, "cancelled");
              return;
            }
          }

          continue;
        }

        const error = race.error;

        const report: NodeExecutionReport = {
          id,
          status: "failed",
          attempts,
          durationMs: Date.now() - startedAt,
          error,
        };

        reported.add(id);
        reports.set(id, report);
        propagateStatus(id, "skipped", error);
        return;
      }
    }

    while (!stopped && (ready.size > 0 || activeCount > 0)) {
      if (signal.aborted) {
        stopOnAbort();
        break;
      }

      while (ready.size > 0 && activeCount < (maxConcurrency ?? Number.POSITIVE_INFINITY)) {
        if (signal.aborted) {
          stopOnAbort();
          break;
        }

        const id = ready.pop();

        if (id === undefined) {
          break;
        }

        if (reported.has(id)) {
          continue;
        }

        activeCount += 1;

        void runNode(id).finally(() => {
          activeCount -= 1;
        });
      }

      if (ready.size === 0 && activeCount === 0) {
        break;
      }

      if (ready.size > 0 && activeCount >= (maxConcurrency ?? Number.POSITIVE_INFINITY)) {
        await Promise.resolve();
      }
    }

    if (signal.aborted) {
      stopOnAbort();
    }

    for (const id of ids) {
      if (!reported.has(id)) {
        markNode(id, "cancelled", 0);
      }
    }

    return reports;
  }

  private detectCycle(ids: readonly string[]): void {
    const color = new Map<string, 0 | 1 | 2>();
    const path: string[] = [];

    for (const startId of ids) {
      if ((color.get(startId) ?? 0) !== 0) {
        continue;
      }

      const stack: Frame[] = [];
      const node = this.nodes.get(startId);

      if (!node) {
        throw new DAGValidationError(`Internal error: missing node ${startId}`);
      }

      color.set(startId, 1);
      path.push(startId);
      stack.push({
        id: startId,
        deps: [...node.deps].sort(),
        depIndex: 0,
      });

      while (stack.length > 0) {
        const frame = stack[stack.length - 1];
        if (!frame) {
          break;
        }

        if (frame.depIndex < frame.deps.length) {
          const dep = frame.deps[frame.depIndex];
          frame.depIndex += 1;

          const depColor = color.get(dep) ?? 0;

          if (depColor === 1) {
            const index = path.lastIndexOf(dep);
            const cycle = [...path.slice(index), dep];
            throw new DAGCycleError(cycle);
          }

          if (depColor === 0) {
            const depNode = this.nodes.get(dep);

            if (!depNode) {
              throw new DAGValidationError(`Internal error: missing node ${dep}`);
            }

            color.set(dep, 1);
            path.push(dep);
            stack.push({
              id: dep,
              deps: [...depNode.deps].sort(),
              depIndex: 0,
            });
          }

          continue;
        }

        stack.pop();
        color.set(frame.id, 2);
        path.pop();
      }
    }
  }

  private topologicalOrder(ids: readonly string[]): string[] {
    const indegree = new Map<string, number>();
    const adjacency = new Map<string, string[]>();

    for (const id of ids) {
      indegree.set(id, 0);
      adjacency.set(id, []);
    }

    for (const id of ids) {
      const node = this.nodes.get(id);

      if (!node) {
        throw new DAGValidationError(`Internal error: missing node ${id}`);
      }

      indegree.set(id, node.deps.length);

      for (const dep of node.deps) {
        const dependents = adjacency.get(dep);

        if (!dependents) {
          throw new DAGValidationError(`Internal error: missing adjacency for ${dep}`);
        }

        dependents.push(id);
      }
    }

    const ready = new MinStringHeap(
      ids.filter((id) => (indegree.get(id) ?? 0) === 0)
    );

    const order: string[] = [];

    while (ready.size > 0) {
      const id = ready.pop();

      if (id === undefined) {
        break;
      }

      order.push(id);

      for (const dependent of adjacency.get(id) ?? []) {
        const remaining = indegree.get(dependent) ?? 0;

        if (remaining > 0) {
          indegree.set(dependent, remaining - 1);

          if (indegree.get(dependent) === 0) {
            ready.push(dependent);
          }
        }
      }
    }

    if (order.length !== ids.length) {
      const remaining = ids.filter((id) => !order.includes(id)).sort();
      throw new DAGCycleError(remaining.length > 0 ? [remaining[0], remaining[0]] : ["cycle"]);
    }

    return order;
  }
}
```