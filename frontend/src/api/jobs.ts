// M2 — TypeScript types + SSE subscription helper for the jobs API.
//
// Mirrors the backend `api/jobs.py` projection (spec 10-jobs-and-sse).
// The full pdomain-ui `useLongJob` hook wraps this in a later milestone; this
// module is the framework-agnostic transport seam underneath it.

export type JobState =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled";

/** SPA projection of the pdomain-ops `JobStatus` (GET /api/jobs/{id}). */
export interface Job {
  id: string;
  run_id: string | null;
  kind: string;
  state: JobState;
  progress: number;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export type JobEventKind = "progress" | "log" | "state" | "metric";

/** One item in the SSE event stream (GET /api/jobs/{id}/events). */
export interface JobEvent {
  job_id: string;
  seq: number;
  at: string;
  kind: JobEventKind;
  payload: Record<string, unknown>;
}

/** The header `JobsBadge` payload (GET /api/jobs/active-count). */
export interface ActiveJobCount {
  count: number;
  by_kind: Record<string, number>;
}

const TERMINAL_STATES: ReadonlySet<JobState> = new Set<JobState>([
  "succeeded",
  "failed",
  "cancelled",
]);

/** True when `state` is a terminal job state (no further events expected). */
export function isTerminalState(state: JobState): boolean {
  return TERMINAL_STATES.has(state);
}

export interface JobSubscriptionCallbacks {
  /** Called once per JobEvent, in `seq` order. */
  onEvent: (event: JobEvent) => void;
  /** Called when the stream closes after a terminal `state` event. */
  onClose?: (terminal: JobEvent) => void;
  /** Called on a transport error (the browser auto-reconnects after this). */
  onError?: (error: Event) => void;
}

/** Handle returned by {@link subscribeToJob}; call `close()` to unsubscribe. */
export interface JobSubscription {
  close: () => void;
}

/**
 * EventSource factory — overridable so tests can inject a fake.
 * Defaults to the platform `EventSource`.
 */
export type EventSourceFactory = (url: string) => EventSource;

const defaultEventSourceFactory: EventSourceFactory = (url) =>
  new EventSource(url);

/**
 * Subscribe to a job's SSE event stream.
 *
 * The browser's native `EventSource` already replays from `Last-Event-ID`
 * on reconnect — it remembers the last `id:` it saw and the backend route
 * skips events with `seq <=` that value (spec 10 §5). This helper adds:
 *
 *  - typed `JobEvent` parsing per `event:` name,
 *  - de-duplication so a reconnect mid-stream never re-delivers a `seq`
 *    the caller already saw,
 *  - automatic close after the terminal `state` event.
 */
export function subscribeToJob(
  jobId: string,
  callbacks: JobSubscriptionCallbacks,
  options: { factory?: EventSourceFactory; basePath?: string } = {},
): JobSubscription {
  const factory = options.factory ?? defaultEventSourceFactory;
  const basePath = options.basePath ?? "";
  const source = factory(
    `${basePath}/api/jobs/${encodeURIComponent(jobId)}/events`,
  );

  let lastSeq = -Infinity;
  let closed = false;

  const close = (): void => {
    if (closed) return;
    closed = true;
    source.close();
  };

  const handle = (raw: MessageEvent): void => {
    if (closed) return;
    let event: JobEvent;
    try {
      event = JSON.parse(raw.data as string) as JobEvent;
    } catch {
      return; // malformed frame — ignore
    }
    // Suppress any event already delivered (reconnect overlap).
    if (event.seq <= lastSeq) return;
    lastSeq = event.seq;
    callbacks.onEvent(event);
    if (event.kind === "state") {
      const state = event.payload.state as JobState | undefined;
      if (state !== undefined && isTerminalState(state)) {
        close();
        callbacks.onClose?.(event);
      }
    }
  };

  for (const kind of ["progress", "log", "state", "metric"] as const) {
    source.addEventListener(kind, handle as EventListener);
  }

  source.onerror = (err): void => {
    callbacks.onError?.(err);
  };

  return { close };
}
