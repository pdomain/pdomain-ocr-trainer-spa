// runArgsEditorConfig — field-spec data for RunArgsEditor (spec 04 §3.2).
//
// Lives in a separate file so RunArgsEditor.tsx only exports React
// components (react-refresh/only-export-components constraint).

export type FieldKind = "number" | "boolean" | "text" | "string-list";

export interface FieldSpec {
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
