"""Shared domain models used by the adapter Protocols (spec 01-data-models §5).

Only the subset the M1 adapter layer references is defined here; the full
Run / DatasetView / Job models land in their own milestones.
"""

from __future__ import annotations

from datetime import (
    datetime,  # noqa: TC003 — pydantic resolves the annotation at model-build time
)

from pydantic import BaseModel

from pd_ocr_trainer_spa.core.enums import (
    TaskEnum,  # noqa: TC001 — pydantic resolves the annotation at model-build time
)


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
