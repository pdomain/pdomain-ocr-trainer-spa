"""Banner-synthesis domain logic (spec 11-notifications §3).

A *banner* is a session-persistent, top-of-page strip surfacing an
environment problem the user should resolve. The backend never stores
banner state — it re-derives the list from environment checks on every
``GET /api/banners`` request. The SPA owns per-tab dismissal.

Three causes are synthesised in v1:

* ``hf-token-missing`` — ``Settings.hf_token_path`` does not exist on disk
  while ``enable_hf_publish`` is true.
* ``disk-low`` — the ``shared_models_dir`` partition has < 5% free.
* ``app-version-mismatch`` — handled entirely client-side (the frontend
  bundle compares ``__APP_ENV__.version`` to the served ``_version``);
  the backend contributes nothing for this cause.

This module is torch-free and does no I/O beyond ``Path.exists`` and a
``shutil.disk_usage`` stat.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel

if TYPE_CHECKING:
    from pdomain_ocr_trainer_spa.settings import Settings

#: Free-space fraction below which the ``disk-low`` banner fires.
DISK_LOW_THRESHOLD = 0.05

BannerSeverity = Literal["info", "warn", "error"]


class BannerAction(BaseModel):
    """A call-to-action link rendered inside a banner."""

    label: str
    href: str


class Banner(BaseModel):
    """One environment banner (spec 11 §3).

    ``id`` is stable per cause so the SPA can key dismissals against it.
    """

    id: str
    severity: BannerSeverity
    title: str
    description: str
    action: BannerAction | None = None
    dismissible: bool = True


def _hf_token_banner(settings: Settings) -> Banner | None:
    """Return the ``hf-token-missing`` banner when HF is configured without a token.

    M10 extends this beyond the publish path: whenever ``hf_token_path`` is
    explicitly set (not ``None``) but the referenced file does not exist, the
    banner fires — the token is needed for both the read path (dataset fetch)
    and the publish path.

    No banner is emitted when ``hf_token_path`` is ``None`` (HF not configured
    at all) or when the file is present and readable.
    """
    token_path = settings.hf_token_path
    if token_path is None:
        return None
    if token_path.exists():
        return None
    return Banner(
        id="hf-token-missing",
        severity="warn",
        title="Hugging Face token missing",
        description=(
            f"No HF token file found at {token_path}. "
            "Set hf_token_path to a readable file to fetch HF datasets or "
            "publish datasets and models."
        ),
        action=BannerAction(label="Open settings", href="/settings"),
        dismissible=True,
    )


def _disk_low_banner(settings: Settings) -> Banner | None:
    """Return the ``disk-low`` banner when the models partition is nearly full."""
    models_dir = settings.shared_models_dir
    # Walk up to the nearest existing ancestor so a not-yet-created
    # shared-models dir still resolves to a real partition.
    probe = models_dir
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    if not probe.exists():
        return None
    try:
        usage = shutil.disk_usage(probe)
    except OSError:
        return None
    if usage.total == 0:
        return None
    free_fraction = usage.free / usage.total
    if free_fraction >= DISK_LOW_THRESHOLD:
        return None
    pct = round(free_fraction * 100, 1)
    return Banner(
        id="disk-low",
        severity="error",
        title="Disk almost full",
        description=(
            f"The shared-models partition has only {pct}% free. Training runs may fail to write checkpoints."
        ),
        dismissible=False,
    )


def synthesize_banners(settings: Settings) -> list[Banner]:
    """Return the active banner list derived from the current environment.

    The order is deterministic: ``hf-token-missing`` then ``disk-low``.
    ``app-version-mismatch`` is omitted — that banner is client-only.
    """
    banners: list[Banner] = []
    for builder in (_hf_token_banner, _disk_low_banner):
        banner = builder(settings)
        if banner is not None:
            banners.append(banner)
    return banners
