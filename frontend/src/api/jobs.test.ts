// M2 — tests for the SSE job-subscription helper.
//
// Uses a FakeEventSource so the helper is exercised without a real
// network: scripted frames, reconnect overlap, terminal-state close.

import { describe, it, expect } from "vitest";
import { subscribeToJob, isTerminalState, type JobEvent } from "./jobs";

/** Minimal EventSource stand-in: tests push frames via `emit`. */
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

  /** Deliver one JobEvent as an SSE `MessageEvent` keyed by its `kind`. */
  emit(event: JobEvent): void {
    const msg = { data: JSON.stringify(event) } as MessageEvent;
    for (const fn of this.listeners.get(event.kind) ?? []) {
      fn(msg as unknown as Event);
    }
  }
}

function makeEvent(
  seq: number,
  kind: JobEvent["kind"],
  payload = {},
): JobEvent {
  return {
    job_id: "j-1",
    seq,
    at: "2026-05-21T10:00:00Z",
    kind,
    payload,
  };
}

describe("isTerminalState", () => {
  it("classifies terminal vs non-terminal states", () => {
    expect(isTerminalState("succeeded")).toBe(true);
    expect(isTerminalState("failed")).toBe(true);
    expect(isTerminalState("cancelled")).toBe(true);
    expect(isTerminalState("running")).toBe(false);
    expect(isTerminalState("queued")).toBe(false);
  });
});

describe("subscribeToJob", () => {
  it("delivers every event in order (acceptance 1)", () => {
    let source!: FakeEventSource;
    const received: JobEvent[] = [];
    subscribeToJob(
      "j-1",
      { onEvent: (e) => received.push(e) },
      {
        factory: (url) =>
          (source = new FakeEventSource(url)) as unknown as EventSource,
      },
    );

    expect(source.url).toBe("/api/jobs/j-1/events");
    source.emit(makeEvent(0, "log"));
    source.emit(makeEvent(1, "progress"));
    source.emit(makeEvent(2, "metric"));

    expect(received.map((e) => e.seq)).toEqual([0, 1, 2]);
    expect(received.map((e) => e.kind)).toEqual(["log", "progress", "metric"]);
  });

  it("suppresses duplicate seqs on reconnect overlap (acceptance 2)", () => {
    let source!: FakeEventSource;
    const received: JobEvent[] = [];
    subscribeToJob(
      "j-1",
      { onEvent: (e) => received.push(e) },
      {
        factory: (url) =>
          (source = new FakeEventSource(url)) as unknown as EventSource,
      },
    );

    source.emit(makeEvent(0, "log"));
    source.emit(makeEvent(1, "progress"));
    // Reconnect replays 1 again (overlap) then continues.
    source.emit(makeEvent(1, "progress"));
    source.emit(makeEvent(2, "metric"));

    expect(received.map((e) => e.seq)).toEqual([0, 1, 2]);
  });

  it("closes after the terminal state event (acceptance 3)", () => {
    let source!: FakeEventSource;
    const received: JobEvent[] = [];
    let closedWith: JobEvent | null = null;
    subscribeToJob(
      "j-1",
      {
        onEvent: (e) => received.push(e),
        onClose: (e) => {
          closedWith = e;
        },
      },
      {
        factory: (url) =>
          (source = new FakeEventSource(url)) as unknown as EventSource,
      },
    );

    source.emit(makeEvent(0, "progress"));
    source.emit(makeEvent(1, "state", { state: "succeeded" }));
    expect(source.closed).toBe(true);
    expect(closedWith).not.toBeNull();
    expect(closedWith!.seq).toBe(1);

    // Events after the terminal state are suppressed.
    source.emit(makeEvent(2, "log"));
    expect(received.map((e) => e.seq)).toEqual([0, 1]);
  });

  it("does not close on a non-terminal state event", () => {
    let source!: FakeEventSource;
    subscribeToJob(
      "j-1",
      { onEvent: () => {} },
      {
        factory: (url) =>
          (source = new FakeEventSource(url)) as unknown as EventSource,
      },
    );
    source.emit(makeEvent(0, "state", { state: "running" }));
    expect(source.closed).toBe(false);
  });

  it("close() unsubscribes and stops further delivery", () => {
    let source!: FakeEventSource;
    const received: JobEvent[] = [];
    const sub = subscribeToJob(
      "j-1",
      { onEvent: (e) => received.push(e) },
      {
        factory: (url) =>
          (source = new FakeEventSource(url)) as unknown as EventSource,
      },
    );
    source.emit(makeEvent(0, "log"));
    sub.close();
    source.emit(makeEvent(1, "log"));
    expect(received.map((e) => e.seq)).toEqual([0]);
    expect(source.closed).toBe(true);
  });

  it("ignores malformed frames", () => {
    let source!: FakeEventSource;
    const received: JobEvent[] = [];
    subscribeToJob(
      "j-1",
      { onEvent: (e) => received.push(e) },
      {
        factory: (url) =>
          (source = new FakeEventSource(url)) as unknown as EventSource,
      },
    );
    // Hand a non-JSON payload directly to a registered listener.
    (
      source as unknown as { listeners: Map<string, Set<EventListener>> }
    ).listeners
      .get("log")!
      .forEach((fn) => fn({ data: "not json" } as unknown as Event));
    expect(received).toEqual([]);
  });
});
