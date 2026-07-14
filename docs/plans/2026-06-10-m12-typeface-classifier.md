---
Status: partial
Owner: CT
Created: 2026-06-10
Last verified: 2026-07-14
Kind: plan
repo: pdomain/pdomain-ocr-trainer-spa
milestone: M12
track: E
spec: specs/16-milestones.md §M12
---

# M12 — Typeface Classifier Implementation Plan

## Agent Index

- **Kind:** plan
- **Status:** partial
- **Read when:** working on unfinished production typeface training or
  evaluation.
- **Search terms:** M12, typeface classifier, train_typeface, upstream gate.

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

## Goal

Ship typeface-classification training, evaluation, and publishing inside the
SPA, gated on `pdomain-ocr-training` growing a `TypefaceConfig` and
`train_typeface` method behind `ITrainingRunner`.

## Architecture

The SPA side mirrors the existing detection and recognition pattern exactly: a
typed `TypefaceConfig` config model (torch-free), a `train_typeface` method on
`ITrainingRunner`, a worker dispatch path in `worker/train.py`, a typeface
kanban in `domain/datasets.py`, an eval branch for per-class slicing, and a
`run_form` + `eval_form` frontend variant. The training/inference engine belongs
entirely in `pdomain-ocr-training`. This plan defines the exact Protocol surface
this SPA requires, marks it as a cross-repo gate, and plans only the SPA-side
work. The dataset API and browser seam shipped before the production runner and
real evaluation path.

## Tech Stack

The planned stack is Python 3.13, FastAPI, Pydantic v2, `pdomain-ocr-training`
(`TypefaceConfig`, `ITrainingRunner.train_typeface`, `TypefaceEvalConfig`,
`TypefaceEvalResult` — cross-repo gate), `pdomain-ui` `KanbanBoard` (crop
thumbnail strip mode for classifier kanbans), React 18 + TypeScript, Vite,
Vitest, and `pytest-playwright` for browser verification. The current frontend
uses React 19 and `@pdomain/pdomain-ui ^0.11.0`; older versions in execution
steps are historical projections.

## Global Constraints

The FastAPI process must remain Torch-free. Production typeface work must wait
for upstream typed configuration, runner, and evaluation contracts. Seam tests
must not be treated as evidence that real training or evaluation works.

## Adversarial Review

- **Stage:** migration-time review of a partially implemented plan.
- **Source:** 2026-07-14 comparison of this plan with current source and tests.
- **Accepted finding:** SPA route, kanban API, and browser tests prove the seam,
  but not production training or evaluation.
- **Change to result:** the plan remains partial; completed UI work moved into
  current architecture while upstream work remains blocked.
- **Implementation deviations:** dependencies advanced and the dataset/UI seam
  shipped before the upstream training round-trip.
- **Residual risks:** `TypefaceConfig`, `train_typeface`, and real evaluation
  may differ from this projected interface when implemented.

---

## Cross-repo gate: required `pdomain-ocr-training` additions

**This plan cannot be implemented until `pdomain-ocr-training` ships the
following surface.** Do not begin Task 1 until that library's version satisfying
these contracts is available on `pdomain-index-pip`. File a cross-repo
recommendation issue (see §below) to track the upstream work.

### Required Protocol extension in `pdomain_ocr_training/protocols.py`

```python
# New config model — torch-free, added to protocols.py
class TypefaceConfig(BaseModel):
    """Configuration for typeface-classification training.

    Reads <ml_training_dir>/<profile>/typeface/metadata.jsonl as the
    dataset (image-classification/v1 layout: images/ + metadata.jsonl
    with a `typeface` column per row).
    """
    train_path: str | Path                  #
        <ml_training_dir>/<profile>/typeface/
    val_path: str | Path                    #
        <ml_validation_dir>/<profile>/typeface/
    arch: str = "resnet18"                  # small classification arch
    epochs: int = 20
    batch_size: int = 64
    lr: float = 1e-3
    weight_decay: float = 1e-4
    optimizer: str = "adamw"
    scheduler: str = "cosine"
    input_size: int = 64                    # small square crop
    num_classes: int | None = None          # inferred from dataset if None
    workers: int = 4
    amp: bool = False
    early_stop: bool = False
    early_stop_epochs: int = 5
    early_stop_delta: float = 0.001
    output_dir: str | Path = Field(default=".")
    device: int | None = None
    pretrained: bool = True
    name: str | None = None


# Extended ITrainingRunner — add alongside train_detection / train_recognition
class ITrainingRunner(Protocol):
    def train_detection(self, profile: str,
        config: DetectionConfig) -> Iterator[TrainingEvent]: ...
    def train_recognition(self, profile: str,
        config: RecognitionConfig) -> Iterator[TrainingEvent]: ...
    def train_typeface(self, profile: str,
        config: TypefaceConfig) -> Iterator[TrainingEvent]: ...
    # metric events carry: accuracy (float), f1_macro (float),
    # per_class (dict[str, float]) in data


# New eval config model
class TypefaceEvalConfig(BaseModel):
    """Configuration for a typeface-classification evaluation pass."""
    val_path: str | Path
    model_path: str | Path
    arch: str = "resnet18"
    batch_size: int = 64
    input_size: int = 64
    workers: int = 4
    amp: bool = False
    device: int | None = None


# New eval result model
class TypefaceEvalResult(BaseModel):
    """Evaluation result for a typeface classifier model."""
    accuracy: float
    f1_macro: float
    per_class: dict[str, ClassMetrics]
    slices: list[EvalSlice] = Field(default_factory=list)   #
        feature="class:<value>"
    sample_count: int
    excluded_count: int
    duration_seconds: float


# Extended IEvalRunner
class IEvalRunner(Protocol):
    def evaluate_detection(self, profile: str,
        config: DetectionEvalConfig) -> DetectionEvalResult: ...
    def evaluate_recognition(self, profile: str,
        config: RecognitionEvalConfig) -> RecognitionEvalResult: ...
    def evaluate_typeface(self, profile: str,
        config: TypefaceEvalConfig) -> TypefaceEvalResult: ...
```

### Cross-repo recommendation

```text
Cross-repo recommendation
  Target: pdomain-ocr-training
  Reason: M12 typeface-classifier SPA milestone requires TypefaceConfig,
          ITrainingRunner.train_typeface, TypefaceEvalConfig, TypefaceEvalResult,
          and IEvalRunner.evaluate_typeface in protocols.py.
  gh issue create -R pdomain/pdomain-ocr-training \
    -l kind:feature-request -l status:backlog \
    --title "M12 gate: TypefaceConfig + train_typeface + evaluate_typeface" \
    --body "Tracks: (none yet)\nContext: trainer-spa M12\n\nSee plan doc \
§Cross-repo gate for Protocol surface details."
  → Run this? CT can edit before executing.
```

---

## File map

| Action | Path                                                           |
| ------ | -------------------------------------------------------------- |
| Modify | `src/pdomain_ocr_trainer_spa/core/enums.py` (no change needed) |
| Modify | `src/pdomain_ocr_trainer_spa/training/config_build.py`         |
| Modify | `src/pdomain_ocr_trainer_spa/training/fake_runner.py`          |
| Modify | `src/pdomain_ocr_trainer_spa/worker/train.py`                  |
| Modify | `src/pdomain_ocr_trainer_spa/worker/evaluate.py`               |
| Modify | `src/pdomain_ocr_trainer_spa/domain/datasets.py`               |
| Modify | `src/pdomain_ocr_trainer_spa/domain/eval.py`                   |
| Modify | `src/pdomain_ocr_trainer_spa/api/runs.py`                      |
| Modify | `src/pdomain_ocr_trainer_spa/api/eval.py`                      |
| Modify | `src/pdomain_ocr_trainer_spa/api/datasets.py`                  |
| Create | `frontend/src/pages/TypefaceKanbanPage.tsx`                    |
| Create | `frontend/src/pages/TypefaceKanbanPage.test.tsx`               |
| Modify | `frontend/src/App.tsx` (add route)                             |
| Modify | `tests/unit/training/test_config_build.py` (create if absent)  |
| Modify | `tests/unit/domain/test_datasets.py`                           |
| Modify | `tests/unit/domain/test_eval.py`                               |
| Create | `tests/e2e/test_m12_typeface.py`                               |

---

## Task 1: `TypefaceConfig` + `build_typeface_config` (torch-free config build)

**Pre-condition:** `pdomain-ocr-training` has published `TypefaceConfig` in
`protocols.py` and the installed wheel exports it. Verify:

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
uv run python -c "from pdomain_ocr_training.protocols import TypefaceConfig; \
  print('OK')"
```

If this fails, stop. The upstream gate is not satisfied.

**Files:**

- Modify: `src/pdomain_ocr_trainer_spa/training/config_build.py`
- Create: `tests/unit/training/test_config_build.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/training/test_config_build.py
"""Tests for training/config_build.py — TypefaceConfig path."""
from __future__ import annotations
from pathlib import Path
import pytest
from pdomain_ocr_trainer_spa.training.config_build import build_typeface_config
from pdomain_ocr_trainer_spa.core.enums import TaskEnum


class _RunView:
    def __init__(self) -> None:
        self.profile = "clogaelach"
        self.task = TaskEnum.typeface_classification
        self.args: dict[str, object] = {
            "train_path": "/ml-training/clogaelach/typeface",
            "val_path": "/ml-validation/clogaelach/typeface",
            "output_dir": "/runs/123",
            "epochs": 15,
        }


def test_build_typeface_config_basic() -> None:
    view = _RunView()
    cfg = build_typeface_config(view)
    assert cfg.train_path == Path("/ml-training/clogaelach/typeface")
        or str(cfg.train_path) == "/ml-training/clogaelach/typeface"
    assert cfg.val_path == Path("/ml-validation/clogaelach/typeface")
        or str(cfg.val_path) == "/ml-validation/clogaelach/typeface"
    assert cfg.epochs == 15


def test_build_typeface_config_defaults() -> None:
    view = _RunView()
    view.args = {
        "train_path": "/ml-training/clogaelach/typeface",
        "val_path": "/ml-validation/clogaelach/typeface",
        "output_dir": "/runs/123",
    }
    cfg = build_typeface_config(view)
    assert cfg.epochs == 20           # TypefaceConfig default
    assert cfg.arch == "resnet18"     # TypefaceConfig default
```

- [ ] **Step 2: Run the failing test**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
uv run pytest tests/unit/training/test_config_build.py -v 2>&1 | tail -10
```

Expected: `ImportError: cannot import name 'build_typeface_config'`

- [ ] **Step 3: Implement `build_typeface_config` in `config_build.py`**

```python
# Add to src/pdomain_ocr_trainer_spa/training/config_build.py

from pdomain_ocr_training.protocols import TypefaceConfig  # noqa: TC002 — used
    at runtime

_TYPEFACE_FIELDS = frozenset(TypefaceConfig.model_fields)


def build_typeface_config(run: RunLike) -> TypefaceConfig:
    """Build a torch-free TypefaceConfig from the run's args dict."""
    args = run.args
    payload = _selected(args, _TYPEFACE_FIELDS)
    payload.setdefault("train_path", str(args.get("train_path", "")))
    payload.setdefault("val_path", str(args.get("val_path", "")))
    payload.setdefault("output_dir", str(args.get("output_dir", ".")))
    return TypefaceConfig.model_validate(payload)
```

- [ ] **Step 4: Run the tests**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
uv run pytest tests/unit/training/test_config_build.py -v 2>&1 | tail -10
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git add src/pdomain_ocr_trainer_spa/training/config_build.py \
        tests/unit/training/
git commit -m "feat(m12): build_typeface_config — torch-free TypefaceConfig \
  builder"
```

---

## Task 2: Fake runner + worker dispatch — `train_typeface`

**Files:**

- Modify: `src/pdomain_ocr_trainer_spa/training/fake_runner.py`
- Modify: `src/pdomain_ocr_trainer_spa/worker/train.py`
- Modify: `tests/unit/training/` or `tests/integration/`

- [ ] **Step 1: Read the existing fake runner**

```bash
cat \
  /workspaces/ocr-container/pdomain-ocr-trainer-spa/src/pdomain_ocr_trainer_spa/training/fake_runner.py
```

The fake runner must implement `train_typeface` returning a scripted event
stream so tests can drive the full job lifecycle without torch.

- [ ] **Step 2: Write the failing test for the worker dispatch**

```python
# Add to tests/unit/training/test_config_build.py or create
# tests/unit/training/test_worker_dispatch.py

from pdomain_ocr_trainer_spa.core.enums import TaskEnum


def test_iter_events_typeface_calls_train_typeface(tmp_path) -> None:
    """Worker _iter_events routes typeface-classification to train_typeface."""
    from pdomain_ocr_trainer_spa.training.fake_runner import FakeTrainingRunner
    from pdomain_ocr_trainer_spa.worker.train import _iter_events
    runner = FakeTrainingRunner()
    args: dict = {
        "train_path": str(tmp_path / "train"),
        "val_path": str(tmp_path / "val"),
        "output_dir": str(tmp_path / "out"),
    }
    events = list(_iter_events(runner, task="typeface-classification",
        profile="test", args=args))
    kinds = [e.kind if hasattr(e, "kind") else e.get("kind") for e in events]
    assert "done" in kinds
```

- [ ] **Step 3: Run the failing test**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
uv run pytest tests/unit/training/test_worker_dispatch.py -v 2>&1 | tail -10
```

Expected: FAIL — `_iter_events` doesn't handle `typeface-classification` yet

- [ ] **Step 4: Add `train_typeface` to `FakeTrainingRunner`**

Read the existing `FakeTrainingRunner` implementation, then add:

```python
# In training/fake_runner.py — add train_typeface alongside existing methods

def train_typeface(
    self, profile: str, config: "TypefaceConfig"
) -> "Iterator[TrainingEvent]":
    """Fake typeface training: emits progress then done, no torch required."""
    from pdomain_ocr_training.protocols import TrainingEvent
    for epoch in range(1, 4):
        yield TrainingEvent(
            kind="metric",
            message=f"epoch {epoch}",
            progress=epoch / 3,
            data={"accuracy": 0.80 + epoch * 0.05, "f1_macro": 0.78 + epoch *
                0.05},
        )
    yield TrainingEvent(kind="done", message="training complete", progress=1.0)
```

- [ ] **Step 5: Extend `_iter_events` in `worker/train.py`**

```python
# In worker/train.py — extend _iter_events

def _iter_events(
    runner: _TrainingRunner, *, task: str, profile: str, args: dict[str, object]
) -> Iterator[object]:
    from pdomain_ocr_trainer_spa.core.enums import TaskEnum
    from pdomain_ocr_trainer_spa.training.config_build import (
        build_detection_config,
        build_recognition_config,
        build_typeface_config,
    )

    class _RunView:
        def __init__(self) -> None:
            self.profile = profile
            self.task = TaskEnum(task)
            self.args = args

    view = _RunView()
    if task == "detection":
        det_cfg = build_detection_config(view)
        return runner.train_detection(profile, det_cfg)
    if task == "typeface-classification":
        tc_cfg = build_typeface_config(view)
        return runner.train_typeface(profile, tc_cfg)
    rec_cfg = build_recognition_config(view)
    return runner.train_recognition(profile, rec_cfg)
```

The `_TrainingRunner` Protocol stub in `worker/train.py` also needs
`train_typeface`:

```python
class _TrainingRunner(Protocol):
    def train_detection(self, profile: str,
        config: DetectionConfig) -> Iterator[object]: ...
    def train_recognition(self, profile: str,
        config: RecognitionConfig) -> Iterator[object]: ...
    def train_typeface(self, profile: str,
        config: "TypefaceConfig") -> Iterator[object]: ...
```

Add `TypefaceConfig` to the `TYPE_CHECKING` block imports:

```python
if TYPE_CHECKING:
    from collections.abc import Iterator
    from pdomain_ocr_training.protocols import DetectionConfig,
        RecognitionConfig, TypefaceConfig
```

- [ ] **Step 6: Run the dispatch test**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
uv run pytest tests/unit/training/test_worker_dispatch.py -v 2>&1 | tail -10
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git add src/pdomain_ocr_trainer_spa/training/fake_runner.py \
        src/pdomain_ocr_trainer_spa/worker/train.py \
        tests/unit/training/test_worker_dispatch.py
git commit -m "feat(m12): fake runner + worker dispatch for train_typeface"
```

---

## Task 3: Typeface kanban — lift the `task_unsupported` guard

The `domain/datasets.py` `_require_supported` guard currently rejects
`typeface-classification`. This task lifts that guard and adds the crop-based
kanban for the typeface task (spec 05 §10).

**Files:**

- Modify: `src/pdomain_ocr_trainer_spa/domain/datasets.py`
- Modify: `tests/unit/domain/test_datasets.py`

The typeface dataset layout on disk:

```text
<ml_training_dir>/<profile>/typeface/
    metadata.jsonl      # rows: {file_name, typeface}
    images/
        <crop_name>.png
```

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/unit/domain/test_datasets.py

def test_typeface_kanban_builds(tmp_path: Path, settings: Settings) -> None:
    """Typeface kanban assembles from metadata.jsonl crop rows."""
    import json
    from pdomain_ocr_trainer_spa.core.enums import TaskEnum
    from pdomain_ocr_trainer_spa.domain import datasets as dom

    task_dir = settings.ml_training_dir / "all" / "typeface"
    task_dir.mkdir(parents=True)
    (task_dir / "images").mkdir()
    for i, tf in enumerate(["roman", "italic"]):
        crop_name = f"crop_{i:04d}.png"
        (task_dir / "images" / crop_name).write_bytes(b"png")
        with (task_dir / "metadata.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"file_name": crop_name,
                "typeface": tf}) + "\n")

    view = dom.build_kanban(settings, profile="all",
        task=TaskEnum.typeface_classification)
    train_rows = view.columns["train"].rows
    assert len(train_rows) >= 1


def test_typeface_kanban_no_longer_raises_501(tmp_path: Path,
    settings: Settings) -> None:
    """typeface-classification must not raise AppError 501 any more."""
    from pdomain_ocr_trainer_spa.core.enums import TaskEnum
    from pdomain_ocr_trainer_spa.domain import datasets as dom
    # Should not raise
    view = dom.build_kanban(settings, profile="all",
        task=TaskEnum.typeface_classification)
    assert view.task == TaskEnum.typeface_classification
```

- [ ] **Step 2: Run the failing tests**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
T=tests/unit/domain/test_datasets.py
uv run pytest \
  "$T::test_typeface_kanban_builds" \
  "$T::test_typeface_kanban_no_longer_raises_501" \
  -v 2>&1 | tail -15
```

Expected: FAIL with
`AppError: Task 'typeface-classification' kanban is not implemented yet`

- [ ] **Step 3: Implement typeface kanban in `domain/datasets.py`**

Extend `_SUPPORTED_TASKS` and add the `metadata.jsonl` reader:

```python
# In domain/datasets.py

_SUPPORTED_TASKS = (
    TaskEnum.recognition,
    TaskEnum.detection,
    TaskEnum.typeface_classification,   # M12
)


def _read_metadata_jsonl(task_dir: Path) -> LabelMap:
    """Read a metadata.jsonl file (typeface/glyph classifier layout).

    Yields {file_name: typeface_value} pairs. Missing file → empty dict.
    """
    path = task_dir / "metadata.jsonl"
    if not path.exists():
        return {}
    result: LabelMap = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if isinstance(row, dict) and "file_name" in row:
                result[row["file_name"]] = row.get("typeface", "")
    except (ValueError, OSError):
        return {}
    return result


def _read_task_labels(task_dir: Path, task: TaskEnum) -> LabelMap:
    """Read labels for any supported task layout."""
    if task in (TaskEnum.typeface_classification,
        TaskEnum.glyph_classification):
        return _read_metadata_jsonl(task_dir)
    return _read_labels(task_dir)
```

Replace calls to `_read_labels` within `_on_disk_labels`:

```python
def _on_disk_labels(settings: Settings, split: str, profile: str,
    task: TaskEnum) -> LabelMap:
    return _read_task_labels(_task_dir(settings, split, profile, task), task)
```

Also update `_chip_label` and `_values_equal` to handle
`typeface_classification`:

```python
def _chip_label(task: TaskEnum, value: object) -> str:
    if task is TaskEnum.recognition:
        return str(value)
    if task is TaskEnum.typeface_classification:
        return str(value)   # the typeface enum value string
    count = _bbox_count(value)
    return f"{count} bbox" if count == 1 else f"{count} bboxes"


def _values_equal(task: TaskEnum, left: object, right: object) -> bool:
    if task in (TaskEnum.recognition, TaskEnum.typeface_classification):
        return str(left) == str(right)
    return left == right
```

- [ ] **Step 4: Run the tests**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
uv run pytest tests/unit/domain/test_datasets.py -v 2>&1 | tail -20
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git add src/pdomain_ocr_trainer_spa/domain/datasets.py \
        tests/unit/domain/test_datasets.py
git commit -m "feat(m12): typeface kanban — lift 501 guard, add metadata.jsonl \
  reader"
```

---

## Task 4: Run form — `POST /api/runs` for typeface-classification

**Files:**

- Modify: `src/pdomain_ocr_trainer_spa/api/runs.py`
- Modify: `src/pdomain_ocr_trainer_spa/domain/runs.py`
- Modify: `tests/unit/domain/test_runs.py` (add typeface test)

The existing `POST /api/runs` route handles task validation with a flag check
(`Settings.enable_typeface_training`). This is already present per
`settings.py`. What needs adding is the `train_path` / `val_path` resolution for
the typeface task.

- [ ] **Step 1: Read `domain/runs.py` and understand how train/val paths are
      resolved**

```bash
cat \
  /workspaces/ocr-container/pdomain-ocr-trainer-spa/src/pdomain_ocr_trainer_spa/domain/runs.py
```

- [ ] **Step 2: Write the failing test**

```python
# Add to tests/unit/domain/test_runs.py

def test_create_run_typeface(settings, client) -> None:
    """POST /api/runs with task=typeface-classification is accepted when flag
        is on."""
    import pytest
    from pdomain_ocr_trainer_spa.domain.profiles import create_profile
    from pdomain_ocr_trainer_spa.core.enums import TypefaceEnum
    create_profile(settings, name="clogaelach", language="ga",
        typeface=TypefaceEnum.clogaelach)
    # Create typeface training dir
    typeface_train = settings.ml_training_dir / "clogaelach" / "typeface"
    typeface_train.mkdir(parents=True)
    (typeface_train / "metadata.jsonl").write_text('{"file_name":"c.png",
     "typeface":"roman"}\n', encoding="utf-8")
    resp = client.post(
        "/api/runs",
        json={
            "profile": "clogaelach",
            "task": "typeface-classification",
            "args": {},
        },
    )
    assert resp.status_code == 202
    data = resp.json()
    assert "run_id" in data
    assert "job_id" in data
```

- [ ] **Step 3: Run the failing test**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
uv run pytest tests/unit/domain/test_runs.py::test_create_run_typeface -v \
  2>&1 | tail -15
```

Expected: FAIL (the runs domain likely doesn't resolve typeface paths yet)

- [ ] **Step 4: Extend `domain/runs.py` path resolution for typeface**

Read `domain/runs.py` first. The path-resolution logic sets `args["train_path"]`
and `args["val_path"]` from settings. Add the typeface case:

```python
# In domain/runs.py — extend the path-resolution block

if task is TaskEnum.typeface_classification:
    args.setdefault(
        "train_path",
        str(settings.ml_training_dir / profile / "typeface"),
    )
    args.setdefault(
        "val_path",
        str(settings.ml_validation_dir / profile / "typeface"),
    )
```

- [ ] **Step 5: Run the test**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
uv run pytest tests/unit/domain/test_runs.py -v 2>&1 | tail -15
```

Expected: all PASS

- [ ] **Step 6: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git add src/pdomain_ocr_trainer_spa/domain/runs.py \
        tests/unit/domain/test_runs.py
git commit -m "feat(m12): typeface-classification path resolution in runs \
  domain"
```

---

## Task 5: Eval — typeface per-class slicing

**Pre-condition:** `pdomain-ocr-training` has published `TypefaceEvalConfig`,
`TypefaceEvalResult`, and `IEvalRunner.evaluate_typeface`. Verify:

```bash
uv run python -c "from pdomain_ocr_training.protocols import \
  TypefaceEvalConfig, TypefaceEvalResult; print('OK')"
```

**Files:**

- Modify: `src/pdomain_ocr_trainer_spa/worker/evaluate.py`
- Modify: `src/pdomain_ocr_trainer_spa/domain/eval.py`
- Modify: `tests/unit/domain/test_eval.py`

- [ ] **Step 1: Read the existing `worker/evaluate.py`**

```bash
cat \
  /workspaces/ocr-container/pdomain-ocr-trainer-spa/src/pdomain_ocr_trainer_spa/worker/evaluate.py
```

Understand how the existing detection/recognition eval dispatches.

- [ ] **Step 2: Write the failing eval test**

```python
# Add to tests/unit/domain/test_eval.py

def test_eval_typeface_returns_accuracy(tmp_path, settings, client) -> None:
    """POST /api/eval with task=typeface-classification returns 202."""
    from pdomain_ocr_trainer_spa.domain.profiles import create_profile
    from pdomain_ocr_trainer_spa.core.enums import TypefaceEnum
    create_profile(settings, name="roman-test", language="en",
        typeface=TypefaceEnum.roman)
    val_dir = settings.ml_validation_dir / "roman-test" / "typeface"
    val_dir.mkdir(parents=True)
    (val_dir / "metadata.jsonl").write_text('{"file_name":"c.png",
     "typeface":"roman"}\n', encoding="utf-8")
    resp = client.post(
        "/api/eval",
        json={
            "profile": "roman-test",
            "task": "typeface-classification",
            "model_name": "pd-en-roman-typeface-classification-2026-06-10",
            "args": {},
        },
    )
    assert resp.status_code == 202
```

- [ ] **Step 3: Run the failing test**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
uv run pytest \
  tests/unit/domain/test_eval.py::test_eval_typeface_returns_accuracy -v \
    2>&1 | tail -15
```

Expected: FAIL

- [ ] **Step 4: Extend `worker/evaluate.py` for typeface**

Following the existing pattern, add a `TypefaceEvalConfig` build path and a
`TypefaceEvalResult` → `EvalResult` adapter in the worker. Mirror
`build_detection_eval_config` / `build_recognition_eval_config` with:

```python
# In worker/evaluate.py

def _iter_eval_events(
    runner: _EvalRunner, *, task: str, profile: str, args: dict[str, object]
) -> Iterator[object]:
    from pdomain_ocr_trainer_spa.core.enums import TaskEnum

    if task == "typeface-classification":
        from pdomain_ocr_training.protocols import TypefaceEvalConfig
        cfg = TypefaceEvalConfig.model_validate({
            "val_path": args.get("val_path", ""),
            "model_path": args.get("model_path", ""),
            **{k: v for k, v in args.items()
                if k in frozenset(TypefaceEvalConfig.model_fields)},
        })
        result = runner.evaluate_typeface(profile, cfg)
        yield _typeface_result_to_event(result)
        return
    # ... existing detection/recognition dispatch ...
```

Implement `_typeface_result_to_event` that serialises `TypefaceEvalResult` to
the same `EvalResult` JSON shape the frontend expects (using `accuracy`,
`f1_macro`, `per_class`, `slices`).

- [ ] **Step 5: Run the eval tests**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
uv run pytest tests/unit/domain/test_eval.py -v 2>&1 | tail -15
```

Expected: all PASS

- [ ] **Step 6: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git add src/pdomain_ocr_trainer_spa/worker/evaluate.py \
        src/pdomain_ocr_trainer_spa/domain/eval.py \
        tests/unit/domain/test_eval.py
git commit -m "feat(m12): typeface eval dispatch + per-class slicing"
```

---

## Task 6: Frontend — TypefaceKanbanPage + route

**Files:**

- Create: `frontend/src/pages/TypefaceKanbanPage.tsx`
- Create: `frontend/src/pages/TypefaceKanbanPage.test.tsx`
- Modify: `frontend/src/App.tsx`

The typeface kanban page is a thin wrapper that sets
`task="typeface-classification"` on the existing `DatasetsPage` or renders an
equivalent component. Per spec 05 §10, the `KanbanBoard` uses thumbnail-strip
mode for classifier tasks; the SPA passes `thumbnailMode` to `pdomain-ui`'s
`KanbanBoard`. Check the current `pdomain-ui` version for whether
`thumbnailMode` is available; if not, use the list mode fallback.

- [ ] **Step 1: Write the failing component test**

```tsx
// frontend/src/pages/TypefaceKanbanPage.test.tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, it, expect, vi } from "vitest";
import { TypefaceKanbanPage } from "./TypefaceKanbanPage";

vi.mock("../stores/datasetsStore", () => ({
  useDatasetsStore: () => ({
    view: null,
    loading: false,
    applying: false,
    error: null,
  }),
}));

describe("TypefaceKanbanPage", () => {
  it("renders with typeface-classification task", () => {
    render(
      <MemoryRouter
        initialEntries={[
          "/profiles/clogaelach/datasets/typeface-classification",
        ]}
      >
        <Routes>
          <Route
            path="/profiles/:name/datasets/typeface-classification"
            element={<TypefaceKanbanPage />}
          />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("typeface-kanban-page")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the failing test**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend
pnpm test --run src/pages/TypefaceKanbanPage.test.tsx 2>&1 | tail -15
```

Expected: `Cannot find module './TypefaceKanbanPage'`

- [ ] **Step 3: Implement `TypefaceKanbanPage.tsx`**

```tsx
// frontend/src/pages/TypefaceKanbanPage.tsx
import { useParams } from "react-router-dom";
import { DatasetsPage } from "./DatasetsPage";

export function TypefaceKanbanPage(): JSX.Element {
  // Forces task to typeface-classification for the common datasets page.
  // The route path /:name/datasets/typeface-classification sets params.task.
  return (
    <div data-testid="typeface-kanban-page">
      <DatasetsPage />
    </div>
  );
}
```

- [ ] **Step 4: Add the route to `App.tsx`**

Read `App.tsx` first, then add alongside the existing
`/profiles/:name/datasets/:task` route:

```tsx
<Route
  path="/profiles/:name/datasets/typeface-classification"
  element={<TypefaceKanbanPage />}
/>
```

- [ ] **Step 5: Run the frontend tests**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend
pnpm test --run 2>&1 | tail -20
```

Expected: all PASS

- [ ] **Step 6: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git add frontend/src/pages/TypefaceKanbanPage.tsx \
        frontend/src/pages/TypefaceKanbanPage.test.tsx \
        frontend/src/App.tsx
git commit -m "feat(m12): TypefaceKanbanPage + React Router route"
```

---

## Task 7: Run form data-testid contract

**Files:**

- Modify: `frontend/src/pages/NewRunPage.tsx`

The browser verification test needs `data-testid` attributes on the run-form
elements for typeface-classification. Verify the existing `NewRunPage.tsx` has
`data-testid="new-run-form"` and `data-testid="task-select"` (or equivalent)
already; add them if absent.

- [ ] **Step 1: Grep for existing testids**

```bash
SRC=/workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend/src
grep -n "data-testid" "$SRC/pages/NewRunPage.tsx" | head -20
```

- [ ] **Step 2: Add missing `data-testid` attributes**

Ensure these are present:

- `data-testid="new-run-form"` on the form root element
- `data-testid="task-select"` on the task dropdown
- `data-testid="submit-run"` on the submit button

Add them to `NewRunPage.tsx` where absent without changing logic.

- [ ] **Step 3: Run frontend tests**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend
pnpm test --run src/pages/NewRunPage.test.tsx 2>&1 | tail -10
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git add frontend/src/pages/NewRunPage.tsx
git commit -m "chore(m12): add data-testid contract to NewRunPage for e2e tests"
```

---

## Task 8: Run `make ci` green + full integration

- [ ] **Step 1: Run full CI**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
make ci 2>&1 | tail -40
```

Fix any lint/typecheck issues before proceeding. Common issues:

- basedpyright: `TypefaceConfig` may need
  `# pyright: ignore[reportMissingTypeStubs]` if the installed wheel doesn't
  ship a `py.typed` marker. Check `pyproject.toml`'s `[tool.basedpyright]` —
  `reportMissingTypeStubs = "none"` is already set per the M11 packaging notes.
- ruff: ensure any `TYPE_CHECKING` import of `TypefaceConfig` is under
  `if TYPE_CHECKING:` properly.

- [ ] **Step 2: Commit the CI-green state**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git add -u
git commit -m "chore(m12): lint + typecheck fixes for typeface-classification"
```

---

## Task 9: Browser Verification (Mandatory)

**Files:**

- Create: `tests/e2e/test_m12_typeface.py`
- Modify: `Makefile` (add `e2e-browser` if not already present from Track D)

This task assumes `pytest-playwright` is already in the
`[dependency-groups] e2e` group (added by Track D Task 5). If Track D has not
landed, add it here.

- [ ] **Step 1: Write the e2e test**

```python
# tests/e2e/test_m12_typeface.py
"""Browser verification for M12 typeface-classifier round-trip.

Exercises: kanban page loads, run form accepts typeface-classification,
React Router sub-path renders correctly.
"""
from __future__ import annotations
import json
import threading
import time
from pathlib import Path
import pytest
import uvicorn
from pdomain_ocr_trainer_spa.bootstrap import build_app
from pdomain_ocr_trainer_spa.settings import Settings
from pdomain_ocr_trainer_spa.domain.profiles import create_profile
from pdomain_ocr_trainer_spa.core.enums import TypefaceEnum


@pytest.fixture(scope="module")
def typeface_server(tmp_path_factory: pytest.TempPathFactory):
    """Start a live server with a seeded typeface profile."""
    tmp = tmp_path_factory.mktemp("m12")
    s = Settings(
        app_data_root=tmp / "app",  # type: ignore[arg-type]
        ml_training_dir=tmp / "train",  # type: ignore[arg-type]
        ml_validation_dir=tmp / "val",  # type: ignore[arg-type]
        runs_dir=tmp / "runs",  # type: ignore[arg-type]
        jobs_db_path=tmp / "jobs.db",  # type: ignore[arg-type]
        job_runner_kind="fake",
        model_registry_kind="fake",
        host="127.0.0.1",
        port=8092,
        enable_typeface_training=True,
    )
    # Seed profile + typeface data
    create_profile(s, name="testprofile", language="en",
        typeface=TypefaceEnum.roman)
    tc_dir = s.ml_training_dir / "testprofile" / "typeface"
    tc_dir.mkdir(parents=True)
    (tc_dir / "metadata.jsonl").write_text(
        '{"file_name":"c001.png","typeface":"roman"}\n', encoding="utf-8"
    )
    (tc_dir / "images").mkdir()
    (tc_dir / "images" / "c001.png").write_bytes(b"\x89PNG")
    # Fake index.html
    static_dir = Path(__file__).parent.parent.parent / "src" /
        "pdomain_ocr_trainer_spa" / "static"
    static_dir.mkdir(exist_ok=True)
    (static_dir / "index.html").write_text(
        '<html><body data-testid="home-page">OCR Trainer M12</body></html>',
        encoding="utf-8",
    )
    app = build_app(s)
    config = uvicorn.Config(app, host="127.0.0.1", port=8092,
        log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    import socket
    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", 8092), timeout=0.2):
                break
        except OSError:
            time.sleep(0.1)
    yield "http://127.0.0.1:8092"
    server.should_exit = True


def test_home_page_loads(page, typeface_server: str) -> None:
    """SPA serves index.html; no console errors."""
    errors: list[str] = []
    page.on("console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.goto(typeface_server)
    page.wait_for_selector('[data-testid="home-page"]', timeout=5000)
    assert not errors


def test_typeface_kanban_api_returns_200(typeface_server: str) -> None:
    """GET /api/profiles/testprofile/datasets/typeface-classification/kanban
        returns 200."""
    import requests
    resp = requests.get(
        f"{typeface_server}/api/profiles/testprofile/datasets/typeface-classification/kanban",
        timeout=5,
    )
    assert resp.status_code == 200
    view = resp.json()
    assert view["task"] == "typeface-classification"


def test_run_form_accepts_typeface_classification(typeface_server: str) -> None:
    """POST /api/runs with typeface-classification task returns 202."""
    import requests
    resp = requests.post(
        f"{typeface_server}/api/runs",
        json={
            "profile": "testprofile",
            "task": "typeface-classification",
            "model_name": "pd-en-roman-typeface-classification-2026-06-10",
            "args": {},
        },
        timeout=5,
    )
    assert resp.status_code == 202
    data = resp.json()
    assert "run_id" in data


def test_typeface_kanban_subpath_renders(page, typeface_server: str) -> None:
    """React Router route
        /profiles/testprofile/datasets/typeface-classification renders."""
    page.goto(f"{typeface_server}/profiles/testprofile/datasets/typeface-classification")
    page.wait_for_selector('[data-testid="home-page"]', timeout=5000)
    assert "typeface-classification" in page.url
```

- [ ] **Step 2: Run the e2e tests**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
make e2e-browser 2>&1 | tail -30
```

Expected: all 4 tests PASS

- [ ] **Step 3: Run full CI**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
make ci 2>&1 | tail -20
```

Expected: GREEN

- [ ] **Step 4: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git add tests/e2e/test_m12_typeface.py
git commit -m "feat(m12): Playwright browser verification for \
  typeface-classifier round-trip"
```

---

## Acceptance criteria (from spec 16-milestones.md §M12)

- [ ] Round-trip: ingest `typeface-classification/v1` dataset, train, eval,
      publish.
- [ ] `GET /api/profiles/{p}/datasets/typeface-classification/kanban` → 200 with
      crop rows.
- [ ] `POST /api/runs` with `task=typeface-classification` → 202; run appears in
      `/runs`.
- [ ] `POST /api/eval` with `task=typeface-classification` → 202;
      `GET /api/eval/{id}/result` → per-class accuracy/F1.
- [ ] Typeface kanban route renders in browser.
- [ ] `make ci` green.

---

## Self-review checklist

**Spec coverage:**

- [x] New typeface training task behind `ITrainingRunner.train_typeface` — Tasks
      1–2 (gated on upstream)
- [x] Typeface kanban view — Task 3
- [x] Run form acceptance — Task 4
- [x] Eval per-class slicing (`class:<value>` slices) — Task 5
- [x] Frontend route — Task 6
- [x] `data-testid` contract for e2e — Task 7
- [x] Browser Verification milestone — Task 9

**Cross-repo gate items:**

- `TypefaceConfig` in `pdomain_ocr_training.protocols`
- `ITrainingRunner.train_typeface`
- `TypefaceEvalConfig`, `TypefaceEvalResult`
- `IEvalRunner.evaluate_typeface`

**Open questions for implementer:**

1. `TypefaceConfig.arch`: the ROADMAP says "small image-classification model,
   architecture TBD." The plan defaults to `resnet18`. Confirm with CT before
   shipping to `pdomain-ocr-training`.
2. `metadata.jsonl` format: the plan assumes `{file_name, typeface}` rows
   consistent with the HF `imagefolder` layout. Verify this matches what
   `pdomain-ocr-labeler-spa` exports.
3. `pdomain-ui` `KanbanBoard` thumbnail-strip mode: the spec calls for it but
   the prop may not exist yet in the installed version. Fall back to list mode
   if absent; file a cross-repo recommendation for `pdomain-ui`.
4. `evaluate_typeface` in `IEvalRunner`: the existing `IEvalRunner` stub does
   not have this method. The cross-repo recommendation above covers adding it;
   do not add it to the SPA-local `_EvalRunner` protocol stub without confirming
   the upstream shape first.
