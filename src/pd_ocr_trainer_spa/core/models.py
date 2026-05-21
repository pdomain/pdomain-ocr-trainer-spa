"""Shared domain models used by the adapter Protocols (spec 01-data-models §5).

Only the subset the M1 adapter layer references is defined here; the full
Run / DatasetView / Job models land in their own milestones.
"""

from __future__ import annotations

from datetime import (
    datetime,  # noqa: TC003 — pydantic resolves the annotation at model-build time
)

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


class ModelSidecar(BaseModel):
    """Trained-model metadata sidecar (verbatim port of the legacy roadmap shape)."""

    name: str
    task: str
    language: str
    typeface: str
    doctr_arch: str | None = None


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
