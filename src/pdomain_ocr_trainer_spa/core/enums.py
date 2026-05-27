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


class JobState(str, Enum):
    """Mirrors the pdomain-ops ``JobStatus.state`` literal exactly (spec 01 §4)."""

    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class TypefaceEnum(str, Enum):
    """Closed typeface enum (spec 01-data-models §1.1)."""

    roman = "roman"
    italic = "italic"
    smallcaps = "smallcaps"
    blackletter = "blackletter"
    fraktur = "fraktur"
    clogaelach = "clogaelach"
    greek = "greek"
    greek_classical = "greek-classical"
    typeface = "typeface"
