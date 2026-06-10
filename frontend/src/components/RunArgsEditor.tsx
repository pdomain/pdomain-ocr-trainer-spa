// RunArgsEditor — the reusable training-config args form (spec 04 §3.2).
//
// Renders the per-task training-args dict (DetectionConfig / RecognitionConfig
// tunable subset) as a set of typed fields. The Defaults tab of
// ProfileDetailPage (M5) and the run-creation form (M6) both compose it.
//
// The field set is task-driven: number / boolean / text / string-list fields,
// each declared once below. Unknown keys present in `value` but not in the
// field spec are preserved verbatim on change (forward-compatible).

import { useEffect, useState } from "react";
import { Input } from "@pdomain/pdomain-ui/primitives";
import type { TrainingArgs } from "../api/profiles";

type FieldKind = "number" | "boolean" | "text" | "string-list";

interface FieldSpec {
  key: string;
  label: string;
  kind: FieldKind;
}

// spec 04 §3.2 — DetectionConfig tunable subset.
const DETECTION_FIELDS: FieldSpec[] = [
  { key: "arch", label: "Architecture", kind: "text" },
  { key: "epochs", label: "Epochs", kind: "number" },
  { key: "batch_size", label: "Batch size", kind: "number" },
  { key: "workers", label: "Workers", kind: "number" },
  { key: "lr", label: "Learning rate", kind: "number" },
  { key: "weight_decay", label: "Weight decay", kind: "number" },
  { key: "optimizer", label: "Optimizer", kind: "text" },
  { key: "scheduler", label: "Scheduler", kind: "text" },
  { key: "input_size", label: "Input size", kind: "number" },
  { key: "rotation", label: "Rotation", kind: "boolean" },
  { key: "amp", label: "Mixed precision (AMP)", kind: "boolean" },
  { key: "pretrained", label: "Pretrained", kind: "boolean" },
  { key: "early_stop", label: "Early stop", kind: "boolean" },
  { key: "early_stop_epochs", label: "Early-stop epochs", kind: "number" },
  { key: "early_stop_delta", label: "Early-stop delta", kind: "number" },
];

// spec 04 §3.2 — RecognitionConfig tunable subset (vocab presented as the two
// form fields vocab_library + custom_characters).
const RECOGNITION_FIELDS: FieldSpec[] = [
  { key: "arch", label: "Architecture", kind: "text" },
  { key: "epochs", label: "Epochs", kind: "number" },
  { key: "batch_size", label: "Batch size", kind: "number" },
  { key: "workers", label: "Workers", kind: "number" },
  { key: "lr", label: "Learning rate", kind: "number" },
  { key: "weight_decay", label: "Weight decay", kind: "number" },
  { key: "optimizer", label: "Optimizer", kind: "text" },
  { key: "scheduler", label: "Scheduler", kind: "text" },
  { key: "input_size", label: "Input size", kind: "number" },
  { key: "amp", label: "Mixed precision (AMP)", kind: "boolean" },
  { key: "pretrained", label: "Pretrained", kind: "boolean" },
  { key: "early_stop", label: "Early stop", kind: "boolean" },
  { key: "early_stop_epochs", label: "Early-stop epochs", kind: "number" },
  { key: "early_stop_delta", label: "Early-stop delta", kind: "number" },
  { key: "vocab_library", label: "Vocab library", kind: "string-list" },
  { key: "custom_characters", label: "Custom characters", kind: "text" },
];

export function fieldSpecForTask(task: string): FieldSpec[] {
  return task === "detection" ? DETECTION_FIELDS : RECOGNITION_FIELDS;
}

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
                current === undefined || current === null ? "" : String(current)
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
