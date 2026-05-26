"""Build the argv handed to the LongJobRunner for a training run (spec 02-backend §5.1)."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pdomain_ocr_trainer_spa.settings import Settings


class RunIdLike(Protocol):
    """The minimal run surface ``build_worker_cmd`` reads."""

    id: str


def build_worker_cmd(run: RunIdLike, settings: Settings) -> list[str]:
    """Return the argv for the training worker subprocess.

    The worker reads runs/<id>/{manifest,args}.json — only the run-dir is
    passed on the command line.
    """
    run_dir = settings.runs_dir / run.id
    return [
        sys.executable,
        "-m",
        "pdomain_ocr_trainer_spa.worker.train",
        "--run-dir",
        str(run_dir),
    ]
