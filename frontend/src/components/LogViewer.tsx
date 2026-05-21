// LogViewer — a lightweight stdout/stderr log pane for the run-detail page.
//
// Spec 06 §7 names a pd-ui `LogViewer`, but pd-ui exposes no such component
// yet (only `primitives` / `worklist` / `canvas`). Until pd-ui ships one this
// SPA-local viewer carries the spec-13 §4.4 testid contract; swapping in the
// pd-ui component later is a drop-in behind the same testids.

import { useEffect, useRef, useState } from "react";
import { Button } from "@concavetrillion/pd-ui/primitives";

export interface LogViewerProps {
  stdout: string[];
  stderr: string[];
}

export function LogViewer({ stdout, stderr }: LogViewerProps): JSX.Element {
  const [stream, setStream] = useState<"stdout" | "stderr">("stdout");
  const [autoScroll, setAutoScroll] = useState(true);
  const [wrap, setWrap] = useState(true);
  const [search, setSearch] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  const lines = stream === "stdout" ? stdout : stderr;
  const visible = search
    ? lines.filter((l) => l.toLowerCase().includes(search.toLowerCase()))
    : lines;

  useEffect(() => {
    // `scrollIntoView` is absent in jsdom — guard so tests stay green.
    if (autoScroll && typeof endRef.current?.scrollIntoView === "function") {
      endRef.current.scrollIntoView({ block: "end" });
    }
  }, [visible, autoScroll]);

  return (
    <div data-testid="run-detail-log-viewer">
      <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
        <Button
          data-testid="run-detail-log-stream-toggle"
          variant="ghost"
          size="sm"
          onClick={() => setStream((s) => (s === "stdout" ? "stderr" : "stdout"))}
        >
          {stream}
        </Button>
        <label>
          <input
            data-testid="run-detail-log-autoscroll-toggle"
            type="checkbox"
            checked={autoScroll}
            onChange={(e) => setAutoScroll(e.target.checked)}
          />
          Auto-scroll
        </label>
        <label>
          <input
            data-testid="run-detail-log-wrap-toggle"
            type="checkbox"
            checked={wrap}
            onChange={(e) => setWrap(e.target.checked)}
          />
          Wrap
        </label>
        <input
          data-testid="run-detail-log-search"
          placeholder="Find in log…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      <pre
        style={{
          whiteSpace: wrap ? "pre-wrap" : "pre",
          maxHeight: "20rem",
          overflow: "auto",
        }}
      >
        {visible.map((line, i) => (
          <div key={i} data-testid={`run-detail-log-line-${i}`}>
            {line}
          </div>
        ))}
        <div ref={endRef} />
      </pre>
    </div>
  );
}
