"""Torch-free stub eval worker for slow subprocess tests (spec 14 §5).

A drop-in stand-in for ``pdomain_ocr_trainer_spa.worker.evaluate`` that writes a
scripted ``result.json`` and prints a ``@@PDEVENT@@`` sequence — exercising
the real ``LocalLongJobRunner.submit_with_process`` plumbing without CUDA or
DocTR.

Run as::

    python tests/fixtures/stub_eval_worker.py --run-dir runs/<id>
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

EVENT_PREFIX = "@@PDEVENT@@"


def _emit(event: dict[str, object]) -> None:
    """Print one ``@@PDEVENT@@`` line, flushed."""
    print(f"{EVENT_PREFIX} {json.dumps(event)}", flush=True)


def main(argv: list[str] | None = None) -> int:
    """Read the run dir's manifest/args and write a scripted ``result.json``."""
    args = argv if argv is not None else sys.argv[1:]
    run_dir = Path(args[args.index("--run-dir") + 1])
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    run_args = json.loads((run_dir / "args.json").read_text(encoding="utf-8"))

    _emit({"kind": "log", "message": "stub eval starting"})
    result = {
        "run_id": str(manifest.get("id", run_dir.name)),
        "profile": str(manifest.get("profile", "")),
        "task": str(manifest.get("task", "recognition")),
        "model_name": str(run_args.get("model_name", "")),
        "val_source": str(run_args.get("val_source", "")),
        "overall": {"cer": 0.034, "wer": 0.092},
        "slices": [],
        "sample_count": 1842,
        "excluded_count": 0,
        "duration_seconds": 0.1,
        "finished_at": datetime.now(UTC).isoformat(),
    }
    (run_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    _emit({"kind": "done", "message": "stub eval completed"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
