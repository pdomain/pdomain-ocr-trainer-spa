// RunArgsEditor tests — the reusable training-config args form (spec 04 §3.2).

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { RunArgsEditor } from "./RunArgsEditor";
import { fieldSpecForTask } from "./runArgsEditorConfig";
import type { TrainingArgs } from "../api/profiles";

function Harness({
  task,
  initial,
  onChangeSpy,
}: {
  task: string;
  initial: TrainingArgs;
  onChangeSpy?: (a: TrainingArgs) => void;
}): JSX.Element {
  const [args, setArgs] = useState<TrainingArgs>(initial);
  return (
    <RunArgsEditor
      task={task}
      value={args}
      onChange={(next) => {
        setArgs(next);
        onChangeSpy?.(next);
      }}
    />
  );
}

describe("RunArgsEditor", () => {
  it("renders the detection field set including rotation", () => {
    expect(fieldSpecForTask("detection").map((f) => f.key)).toContain(
      "rotation",
    );
    render(
      <Harness task="detection" initial={{ epochs: 100, rotation: false }} />,
    );
    expect(screen.getByTestId("run-args-field-rotation")).toBeTruthy();
    expect(screen.getByTestId("run-args-field-epochs")).toBeTruthy();
  });

  it("renders the recognition field set with the vocab-library list field", () => {
    expect(fieldSpecForTask("recognition").map((f) => f.key)).toContain(
      "vocab_library",
    );
    render(
      <Harness
        task="recognition"
        initial={{ epochs: 10, vocab_library: ["french"] }}
      />,
    );
    const vocab = screen.getByTestId(
      "run-args-field-vocab_library",
    ) as HTMLInputElement;
    expect(vocab.value).toBe("french");
    // detection-only fields are absent for recognition
    expect(screen.queryByTestId("run-args-field-rotation")).toBeNull();
  });

  it("edits a numeric field through onChange", async () => {
    const user = userEvent.setup();
    const spy = vi.fn();
    render(
      <Harness task="detection" initial={{ epochs: 100 }} onChangeSpy={spy} />,
    );
    const input = screen.getByTestId(
      "run-args-field-epochs",
    ) as HTMLInputElement;
    await user.clear(input);
    await user.type(input, "50");
    expect(spy).toHaveBeenLastCalledWith(
      expect.objectContaining({ epochs: 50 }),
    );
  });

  it("toggles a boolean field", async () => {
    const user = userEvent.setup();
    const spy = vi.fn();
    render(
      <Harness
        task="detection"
        initial={{ rotation: false }}
        onChangeSpy={spy}
      />,
    );
    await user.click(screen.getByTestId("run-args-field-rotation"));
    expect(spy).toHaveBeenLastCalledWith(
      expect.objectContaining({ rotation: true }),
    );
  });

  it("parses the string-list field into an array", async () => {
    const user = userEvent.setup();
    const spy = vi.fn();
    render(
      <Harness
        task="recognition"
        initial={{ vocab_library: [] }}
        onChangeSpy={spy}
      />,
    );
    await user.type(
      screen.getByTestId("run-args-field-vocab_library"),
      "french, latin",
    );
    expect(spy).toHaveBeenLastCalledWith(
      expect.objectContaining({ vocab_library: ["french", "latin"] }),
    );
  });
});
