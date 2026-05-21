"""Torch-free stub training worker for slow subprocess tests (spec 14 §5.3).

A drop-in stand-in for ``pd_ocr_trainer_spa.worker.train`` that prints a
scripted ``@@PDEVENT@@`` sequence and exits — exercising the real
``LocalLongJobRunner.submit_with_process`` plumbing (env passing, line
buffering, signal handling, exit-code -> state) without CUDA or DocTR.

Run as::

    python tests/fixtures/stub_worker.py --run-dir runs/<id>
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

EVENT_PREFIX = "@@PDEVENT@@"


def _emit(event: dict[str, object]) -> None:
    """Print one ``@@PDEVENT@@`` line, flushed (line buffering matters)."""
    print(f"{EVENT_PREFIX} {json.dumps(event)}", flush=True)


def main(argv: list[str] | None = None) -> int:
    """Read the run dir's ``args.json`` and replay a scripted epoch sequence."""
    args = argv if argv is not None else sys.argv[1:]
    run_dir = Path(args[args.index("--run-dir") + 1])
    cfg = json.loads((run_dir / "args.json").read_text(encoding="utf-8"))
    epochs = int(cfg.get("epochs", 3))

    for i in range(epochs):
        _emit(
            {
                "kind": "epoch",
                "message": f"epoch {i + 1}/{epochs}",
                "progress": (i + 1) / epochs,
                "data": {"loss": round(1.0 / (i + 1), 4)},
            }
        )
        _emit(
            {
                "kind": "metric",
                "message": f"val batch {i + 1}/{epochs}",
                "data": {"val_cer": round(0.2 / (i + 1), 4)},
            }
        )
        time.sleep(0.02)

    _emit({"kind": "done", "message": "Training completed successfully."})
    return 0


if __name__ == "__main__":
    sys.exit(main())
