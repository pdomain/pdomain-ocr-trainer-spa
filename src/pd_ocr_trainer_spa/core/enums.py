"""Shared enums (spec 01-data-models §2)."""

from __future__ import annotations

from enum import Enum


class TaskEnum(str, Enum):
    """A training task kind."""

    detection = "detection"
    recognition = "recognition"
    typeface_classification = "typeface-classification"
    glyph_classification = "glyph-classification"


class SplitEnum(str, Enum):
    """Which dataset split a row belongs to."""

    unassigned = "unassigned"
    train = "train"
    val = "val"
