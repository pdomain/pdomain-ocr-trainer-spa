// useNotificationStream — top-level hook that toasts terminal job
// transitions (spec 11-notifications §5).
//
// Mounted once in App.tsx. Given a set of job ids to watch it subscribes
// to each job's SSE event stream and fires exactly one toast per
// `(job_id, terminal-state)` pair per session. Toasts are emitted
// through an injectable `emit` callback so the hook stays decoupled
// from the sonner runtime (and unit-testable).

import { useEffect, useRef } from "react";
import type { JobEvent, JobState } from "../api/jobs";
import { subscribeToJob } from "../api/jobs";
import type { EventSourceFactory } from "../api/jobs";
import type { Toast } from "../lib/toast";

/** Describes a watched job — id plus enough run metadata for toast text. */
export interface WatchedJob {
  jobId: string;
  /** Run kind: "train" | "eval" | "publish-dataset" | ... */
  kind: string;
  /** Model name (training) or repo (publish) for the success toast. */
  label?: string;
}

export interface UseNotificationStreamOptions {
  /** Jobs to watch for terminal transitions. */
  jobs: WatchedJob[];
  /** Emits a toast — wired to the sonner adapter in App.tsx. */
  emit: (toast: Toast) => void;
  /** Optional EventSource factory override (tests inject a fake). */
  eventSourceFactory?: EventSourceFactory;
}

/** Build the toast for a terminal job event (spec 11 §5 table). */
export function terminalToast(job: WatchedJob, event: JobEvent): Toast {
  const state = event.payload.state as JobState;
  const label = job.label ?? job.jobId;
  if (state === "cancelled") {
    return { kind: "info", title: "Run cancelled.", durationMs: 5000 };
  }
  if (state === "failed") {
    const error = (event.payload.error as string | undefined) ?? undefined;
    return {
      kind: "error",
      title: "Run failed",
      description: error ?? "The run did not finish successfully.",
      durationMs: 0,
    };
  }
  // succeeded — kind-specific copy.
  if (job.kind === "eval") {
    const cerRaw = event.payload.cer;
    const werRaw = event.payload.wer;
    const cer = typeof cerRaw === "number" ? cerRaw : undefined;
    const wer = typeof werRaw === "number" ? werRaw : undefined;
    const metrics =
      cer !== undefined && wer !== undefined
        ? `CER ${cer.toFixed(3)}, WER ${wer.toFixed(3)}`
        : label;
    return { kind: "success", title: `Eval done — ${metrics}` };
  }
  if (job.kind === "publish-dataset" || job.kind === "publish-model") {
    return { kind: "success", title: `Published ${label}` };
  }
  return { kind: "success", title: `Training finished — ${label}` };
}

/**
 * Watch `jobs` and toast each one's terminal transition exactly once.
 *
 * De-duplication key is `${jobId}:${terminalState}` and persists for the
 * lifetime of the hook (i.e. the session), so re-subscribes on a fast
 * job-list refresh never re-toast.
 */
export function useNotificationStream(
  options: UseNotificationStreamOptions,
): void {
  const { jobs, emit, eventSourceFactory } = options;
  const seenRef = useRef<Set<string>>(new Set());
  // Keep `emit` current without re-subscribing every render.
  const emitRef = useRef(emit);
  emitRef.current = emit;

  // Stable signature so we only re-subscribe when the watched set changes.
  const signature = jobs
    .map((j) => `${j.jobId}|${j.kind}|${j.label ?? ""}`)
    .sort()
    .join(",");

  useEffect(() => {
    const subscriptions = jobs.map((job) =>
      subscribeToJob(
        job.jobId,
        {
          onEvent: () => {
            /* progress/log/metric events are surfaced elsewhere */
          },
          onClose: (terminal) => {
            const state = terminal.payload.state as JobState | undefined;
            if (state === undefined) return;
            const dedupeKey = `${job.jobId}:${state}`;
            if (seenRef.current.has(dedupeKey)) return;
            seenRef.current.add(dedupeKey);
            emitRef.current(terminalToast(job, terminal));
          },
        },
        eventSourceFactory ? { factory: eventSourceFactory } : {},
      ),
    );
    return () => {
      for (const sub of subscriptions) sub.close();
    };
    // `signature` captures the meaningful contents of `jobs`.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature, eventSourceFactory]);
}
