// RunArgsEditor — the reusable training-config args form (spec 04 §3.2).
//
// Renders the per-task training-args dict (DetectionConfig / RecognitionConfig
// tunable subset) as a set of typed fields. The Defaults tab of
// ProfileDetailPage (M5) and the run-creation form (M6) both compose it.
//
// The field set is task-driven: number / boolean / text / string-list fields,
// each declared once in runArgsEditorConfig.ts. Unknown keys present in
// `value` but not in the field spec are preserved verbatim on change
// (forward-compatible).

import { useEffect, useState } from "react";
import { Input } from "@pdomain/pdomain-ui/primitives";
import type { TrainingArgs } from "../api/profiles";
import { fieldSpecForTask } from "./runArgsEditorConfig";

// A comma-separated string-list field. Keeps the raw text in local state so
// in-progress separators (a trailing ", ") survive while the user types; the
// committed value is always the parsed string array.
function StringListField({
  id,
  label,
  value,
  disabled,
  onChange,
}: {
  id: string;
  label: string;
  value: unknown;
  disabled: boolean;
  onChange: (next: string[]) => void;
}): React.JSX.Element {
  const committed = Array.isArray(value) ? (value as string[]).join(", ") : "";
  const [text, setText] = useState(committed);
  // Re-sync when the committed value changes from outside (task switch, reset).
  useEffect(() => {
    setText(committed);
  }, [committed]);
  return (
    <label style={{ display: "block" }}>
      {label}
      <Input
        data-testid={id}
        disabled={disabled}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          onChange(
            e.target.value
              .split(",")
              .map((s) => s.trim())
              .filter((s) => s.length > 0),
          );
        }}
      />
    </label>
  );
}

export interface RunArgsEditorProps {
  task: string;
  value: TrainingArgs;
  onChange: (next: TrainingArgs) => void;
  /** testid prefix — defaults to `run-args`; ProfileDetailPage scopes it. */
  testIdPrefix?: string;
  disabled?: boolean;
}

export function RunArgsEditor({
  task,
  value,
  onChange,
  testIdPrefix = "run-args",
  disabled = false,
}: RunArgsEditorProps): React.JSX.Element {
  const fields = fieldSpecForTask(task);

  const setField = (key: string, next: unknown) => {
    onChange({ ...value, [key]: next });
  };

  return (
    <div data-testid={`${testIdPrefix}-editor`}>
      {fields.map((field) => {
        const id = `${testIdPrefix}-field-${field.key}`;
        const current = value[field.key];
        if (field.kind === "boolean") {
          return (
            <label key={field.key} style={{ display: "block" }}>
              <input
                data-testid={id}
                type="checkbox"
                disabled={disabled}
                checked={Boolean(current)}
                onChange={(e) => setField(field.key, e.target.checked)}
              />{" "}
              {field.label}
            </label>
          );
        }
        if (field.kind === "string-list") {
          return (
            <StringListField
              key={field.key}
              id={id}
              label={field.label}
              value={current}
              disabled={disabled}
              onChange={(next) => setField(field.key, next)}
            />
          );
        }
        // number / text
        return (
          <label key={field.key} style={{ display: "block" }}>
            {field.label}
            <Input
              data-testid={id}
              type={field.kind === "number" ? "number" : "text"}
              disabled={disabled}
              value={
                typeof current === "number" || typeof current === "string"
                  ? String(current)
                  : ""
              }
              onChange={(e) => {
                if (field.kind === "number") {
                  const raw = e.target.value;
                  setField(field.key, raw === "" ? "" : Number(raw));
                } else {
                  setField(field.key, e.target.value);
                }
              }}
            />
          </label>
        );
      })}
    </div>
  );
}
