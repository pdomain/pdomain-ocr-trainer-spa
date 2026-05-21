"""Shared domain models used by the adapter Protocols (spec 01-data-models §5).

Only the subset the M1 adapter layer references is defined here; the full
Run / DatasetView / Job models land in their own milestones.
"""

from __future__ import annotations

from datetime import (
    datetime,  # noqa: TC003 — pydantic resolves the annotation at model-build time
)
from typing import Literal

from pydantic import BaseModel

from pd_ocr_trainer_spa.core.enums import (  # noqa: TC001 — pydantic resolves these at model-build time
    JobState,
    TaskEnum,
    TypefaceEnum,
)


class ProfileCounts(BaseModel):
    """Per-task page / crop counts for a profile (spec 01-data-models §1)."""

    detection_train_pages: int = 0
    detection_val_pages: int = 0
    recognition_train_crops: int = 0
    recognition_val_crops: int = 0
    typeface_train_crops: int = 0
    typeface_val_crops: int = 0
    glyph_train_crops: int = 0
    glyph_val_crops: int = 0


class Profile(BaseModel):
    """A training-data profile — the unit of isolation between runs (spec 01 §1)."""

    name: str
    display_name: str
    language: str | None = None
    typeface: TypefaceEnum | None = None
    is_base: bool = False
    has_training_data: bool = False
    has_validation_data: bool = False
    counts: ProfileCounts = ProfileCounts()


class ModelPaths(BaseModel):
    """Absolute on-disk paths for a trained model's artefacts."""

    weights: str
    sidecar: str
    config: str | None = None


class TrainedOnSource(BaseModel):
    """One source the model was trained on (sidecar ``trained_on`` entry, spec 08 §3)."""

    repo: str
    revision: str | None = None
    rows: int | None = None
    weight: float = 1.0
    source: str = "local"


class SidecarEvalSummary(BaseModel):
    """The optional ``eval`` block of a sidecar (spec 08 §3)."""

    best_run_id: str
    overall: dict[str, float] = {}


class ModelSidecar(BaseModel):
    """Trained-model metadata sidecar (spec 08 §3; append-only by convention, D-T16).

    ``language``/``typeface`` are optional so legacy models without those slots
    still round-trip; the registry back-fills them from the profile when it can.
    """

    name: str
    task: str
    language: str | None = None
    typeface: str | None = None
    doctr_arch: str | None = None
    trainer_version: str | None = None
    trained_at: datetime | None = None
    trained_on: list[TrainedOnSource] = []
    args: dict[str, object] = {}
    qualifier: str | None = None
    eval: SidecarEvalSummary | None = None


class ModelPublication(BaseModel):
    """A record of a model published to a remote hub."""

    repo: str
    url: str
    published_at: datetime


class TrainedModel(BaseModel):
    """A trained model artefact plus its sidecar."""

    name: str
    profile: str
    task: TaskEnum
    language: str | None = None
    typeface: str | None = None
    paths: ModelPaths
    sidecar: ModelSidecar
    published_to: list[ModelPublication] = []


KanbanColumnId = Literal["unassigned", "train", "val"]


class KanbanPageChip(BaseModel):
    """A single draggable item in the kanban — a page (detection) or crop (recognition).

    spec 05-dataset-kanban §2.
    """

    key: str
    page_name: str
    crop_name: str | None = None
    label_text: str | None = None
    is_changed: bool = False
    change_summary: str | None = None


class KanbanProjectRow(BaseModel):
    """A project's row within a kanban column (spec 05 §2)."""

    project_id: str
    source: Literal["pending", "on_disk"]
    page_count: int
    is_changed: bool = False
    style_tags: list[str] = []
    pages: list[KanbanPageChip] = []


class KanbanColumn(BaseModel):
    """One kanban column's ordered project rows (spec 05 §2)."""

    rows: list[KanbanProjectRow] = []


class KanbanView(BaseModel):
    """The committed server-truth kanban for one ``(profile, task)`` pair (spec 05 §2)."""

    profile: str
    task: TaskEnum
    columns: dict[KanbanColumnId, KanbanColumn]
    include_detection: bool = True
    include_recognition: bool = True


class AssignmentEntry(BaseModel):
    """One staged chip-to-split assignment (spec 05 §3)."""

    key: str
    target_split: KanbanColumnId


class ApplyAssignmentRequest(BaseModel):
    """The whole target-split assignment committed by ``apply`` (spec 05 §3)."""

    assignments: list[AssignmentEntry] = []


class IncludeTogglesRequest(BaseModel):
    """Body for ``POST .../include-toggles`` — the only persisted kanban state (spec 05 §5)."""

    include_detection: bool
    include_recognition: bool


RunKind = Literal["train", "eval", "publish-dataset", "publish-model"]
RunStatus = Literal["pending", "running", "succeeded", "failed", "cancelled"]


class Run(BaseModel):
    """A training/eval/publish run (spec 01-data-models §3, spec 06).

    ``id`` is the ULID and the directory name under ``runs/``. ``args`` is the
    resolved task-specific args dict; ``job_id`` links to the pd-ocr-ops
    ``LongJobRunner`` job that owns the worker subprocess.
    """

    id: str
    profile: str
    task: TaskEnum
    kind: RunKind = "train"
    status: RunStatus = "pending"
    model_name: str
    args: dict[str, object] = {}
    notes: str | None = None
    device: int | None = None
    seed: int | None = None
    started_at: datetime
    finished_at: datetime | None = None
    exit_code: int | None = None
    artefact_paths: list[str] = []
    job_id: str | None = None


class Job(BaseModel):
    """SPA projection of the pd-ocr-ops ``JobStatus`` (spec 01 §4 / 10 §3).

    The SPA does not own a job runner; ``api/jobs.py`` projects
    ``LongJobRunner.status(job_id)`` onto this model for the frontend and
    the OpenAPI export.
    """

    id: str
    run_id: str | None = None
    kind: str
    state: JobState
    progress: float
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


# ---------------------------------------------------------------------------
# Evaluation (spec 07-evaluation-and-metrics §3)
# ---------------------------------------------------------------------------


class ClassMetrics(BaseModel):
    """Per-class precision/recall/F1 (classification eval)."""

    n: int
    precision: float
    recall: float
    f1: float


class EvalMetrics(BaseModel):
    """Task-shaped metrics; only the fields relevant to ``task`` are populated."""

    # Recognition
    cer: float | None = None
    wer: float | None = None
    exact_match_rate: float | None = None
    # Detection
    precision: float | None = None
    recall: float | None = None
    f1: float | None = None
    iou_50: float | None = None
    iou_50_95: float | None = None
    # Classification
    accuracy: float | None = None
    f1_macro: float | None = None
    per_class: dict[str, ClassMetrics] | None = None


class EvalSlice(BaseModel):
    """One glyph-feature or per-class slice of an eval (spec 07 §3)."""

    feature: str
    n_pos: int
    n_neg: int
    n_excluded: int = 0
    cer_pos: float | None = None
    cer_neg: float | None = None
    wer_pos: float | None = None
    wer_neg: float | None = None
    delta_cer: float | None = None
    low_support: bool = False


class EvalResult(BaseModel):
    """The typed result of an eval run, persisted to ``runs/<id>/result.json``."""

    run_id: str
    profile: str
    task: TaskEnum
    model_name: str
    val_source: str
    overall: EvalMetrics
    slices: list[EvalSlice] = []
    sample_count: int = 0
    excluded_count: int = 0
    duration_seconds: float = 0.0
    finished_at: datetime
