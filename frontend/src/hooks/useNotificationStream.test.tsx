// useNotificationStream tests — terminal-job toasts (spec 11 §5, §8).

import { useRef } from "react";
import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import type { JobEvent } from "../api/jobs";
import type { Toast } from "../lib/toast";
import {
  terminalToast,
  useNotificationStream,
  type WatchedJob,
} from "./useNotificationStream";

/** Minimal scriptable EventSource (mirrors api/jobs.test.ts). */
class FakeEventSource {
  url: string;
  closed = false;
  onerror: ((e: Event) => void) | null = null;
  private listeners = new Map<string, Set<EventListener>>();

  constructor(url: string) {
    this.url = url;
  }

  addEventListener(type: string, fn: EventListener): void {
    if (!this.listeners.has(type)) this.listeners.set(type, new Set());
    this.listeners.get(type)!.add(fn);
  }

  close(): void {
    this.closed = true;
  }

  emit(event: JobEvent): void {
    const msg = { data: JSON.stringify(event) } as MessageEvent;
    for (const fn of this.listeners.get(event.kind) ?? []) {
      fn(msg as unknown as Event);
    }
  }
}

let seqCounter = 0;

function stateEvent(jobId: string, state: string, payload = {}): JobEvent {
  seqCounter += 1;
  return {
    job_id: jobId,
    seq: seqCounter,
    at: "2026-05-21T10:00:00Z",
    kind: "state",
    payload: { state, ...payload },
  };
}

describe("terminalToast", () => {
  const trainJob: WatchedJob = { jobId: "j1", kind: "train", label: "pd-ga-x" };

  it("builds a success toast for a finished training run", () => {
    const toast = terminalToast(trainJob, stateEvent("j1", "succeeded"));
    expect(toast.kind).toBe("success");
    expect(toast.title).toContain("pd-ga-x");
  });

  it("builds an eval toast with CER/WER metrics", () => {
    const evalJob: WatchedJob = { jobId: "j2", kind: "eval" };
    const toast = terminalToast(
      evalJob,
      stateEvent("j2", "succeeded", { cer: 0.04, wer: 0.11 }),
    );
    expect(toast.title).toContain("CER 0.04");
  });

  it("builds a persistent error toast for a failed run", () => {
    const toast = terminalToast(
      trainJob,
      stateEvent("j1", "failed", { error: "CUDA OOM" }),
    );
    expect(toast.kind).toBe("error");
    expect(toast.durationMs).toBe(0);
    expect(toast.description).toBe("CUDA OOM");
  });

  it("builds a quiet auto-dismiss toast for a cancelled run", () => {
    const toast = terminalToast(trainJob, stateEvent("j1", "cancelled"));
    expect(toast.kind).toBe("info");
    expect(toast.durationMs).toBe(5000);
  });
});

describe("useNotificationStream", () => {
  function Harness(props: {
    jobs: WatchedJob[];
    emit: (t: Toast) => void;
    sources: FakeEventSource[];
  }): JSX.Element {
    // Memoise the factory so re-renders never re-subscribe.
    const factory = useRef((url: string) => {
      const src = new FakeEventSource(url);
      props.sources.push(src);
      return src as unknown as EventSource;
    });
    useNotificationStream({
      jobs: props.jobs,
      emit: props.emit,
      eventSourceFactory: factory.current,
    });
    return <div />;
  }

  it("emits exactly one toast per terminal transition (spec §8 scenario 2)", () => {
    const toasts: Toast[] = [];
    const sources: FakeEventSource[] = [];
    render(
      <Harness
        jobs={[{ jobId: "j1", kind: "train", label: "pd-ga-x" }]}
        emit={(t) => toasts.push(t)}
        sources={sources}
      />,
    );

    sources[0]!.emit(stateEvent("j1", "running"));
    expect(toasts).toHaveLength(0);

    sources[0]!.emit(stateEvent("j1", "succeeded"));
    expect(toasts).toHaveLength(1);
    expect(toasts[0]!.kind).toBe("success");
  });

  it("deduplicates a repeated terminal event for the same job", () => {
    const toasts: Toast[] = [];
    const sources: FakeEventSource[] = [];
    render(
      <Harness
        jobs={[{ jobId: "j1", kind: "train", label: "m" }]}
        emit={(t) => toasts.push(t)}
        sources={sources}
      />,
    );
    sources[0]!.emit(stateEvent("j1", "succeeded"));
    sources[0]!.emit(stateEvent("j1", "succeeded"));
    expect(toasts).toHaveLength(1);
  });
});
