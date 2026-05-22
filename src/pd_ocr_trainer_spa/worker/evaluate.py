"""Evaluation-worker subprocess entry point (spec 07-evaluation-and-metrics).

Invoked as::

    python -m pd_ocr_trainer_spa.worker.evaluate --run-dir runs/<id>

The worker:

1. Reads ``runs/<id>/{manifest,args}.json``.
2. Runs model inference over the validation set and computes metrics.
3. Writes ``runs/<id>/result.json`` (the typed :class:`EvalResult`) and a
   pretty ``result.md``.
4. Emits ``@@PDEVENT@@`` progress lines, exits ``0`` on success.

``torch`` / DocTR are imported **only** via the real eval runner. The
``--runner`` seam (``run_worker(run_dir, runner=...)``) lets tests inject a
torch-free fake runner that scores a fixture; production builds the real
runner.

UPSTREAM STATE (M13 readiness, verified 2026-05-22):
``pd_ocr_training`` now exposes ``IEvalRunner`` + ``LocalEvalRunner`` and the
result models ``RecognitionEvalResult`` / ``EvalSlice``. However, glyph-feature
slicing (spec 07 §4) is still blocked upstream:

* ``evaluate_recognition_impl`` hard-codes ``slices=[]`` (see
  ``pd_ocr_training/_eval_backend.py`` — "Out of scope (issue #3 baseline)").
* ``RecognitionEvalConfig`` has no field to pass glyph annotations or a
  ``slice_glyph_features`` flag, so the runner cannot receive the per-word
  ``GlyphAnnotations`` it would need to compute positive/negative subsets.

The pd-book-tools ``GlyphAnnotations`` data model (the other M13 pre-condition)
has landed, but until ``pd_ocr_training`` accepts annotations as eval input and
populates ``slices``, the SPA cannot deliver M13. The production
``_build_runner`` path raises a clear error; the eval round-trip is exercised
end-to-end through the injectable stub runner.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from pd_ocr_trainer_spa.core.enums import TaskEnum
from pd_ocr_trainer_spa.core.models import EvalMetrics, EvalResult

if TYPE_CHECKING:
    from collections.abc import Mapping

EVENT_PREFIX = "@@PDEVENT@@"


class EvalRunner(Protocol):
    """The minimal eval surface the worker drives.

    ``evaluate`` scores ``model_name`` against ``val_source`` and returns the
    overall metrics plus the sample count. Tests inject a torch-free fake;
    production builds the real runner once one exists upstream.
    """

    def evaluate(
        self,
        *,
        task: str,
        profile: str,
        model_name: str,
        val_source: str,
        options: Mapping[str, object],
    ) -> tuple[EvalMetrics, int]:
        """Score the model and return ``(overall metrics, sample count)``."""
        ...


def emit_event(event: dict[str, object]) -> None:
    """Write one ``@@PDEVENT@@`` line to stdout."""
    sys.stdout.write(f"{EVENT_PREFIX} {json.dumps(event)}\n")
    sys.stdout.flush()


def _build_runner() -> EvalRunner:
    """Build the real eval runner.

    pd-ocr-training exposes ``LocalEvalRunner`` (``IEvalRunner``), but wiring it
    into this worker — including glyph-feature slicing (M13) — is not done yet.
    Until then the production path raises a clear error and the eval round-trip
    is exercised through the injectable stub runner.
    """
    raise RuntimeError(
        "Real model evaluation is not wired up yet. pd-ocr-training exposes "
        "LocalEvalRunner (IEvalRunner), but glyph-feature slicing (M13) is "
        "blocked: RecognitionEvalConfig has no glyph-annotation input and "
        "evaluate_recognition_impl hard-codes slices=[]. Track the upstream "
        "gap before running a non-stub eval."
    )


def run_worker(run_dir: Path, *, runner: EvalRunner | None = None) -> int:
    """Execute one eval run; write ``result.json``; return the exit code.

    ``runner`` is injectable so tests can pass a torch-free fake; production
    leaves it ``None`` and the real runner is built.
    """
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    args = json.loads((run_dir / "args.json").read_text(encoding="utf-8"))

    run_id = str(manifest.get("id", run_dir.name))
    task = str(manifest.get("task", ""))
    profile = str(manifest.get("profile", ""))
    model_name = str(args.get("model_name", ""))
    val_source = str(args.get("val_source", ""))

    if runner is None:
        runner = _build_runner()

    started = datetime.now(UTC)
    emit_event({"kind": "log", "message": f"Evaluating {model_name}…"})
    try:
        metrics, sample_count = runner.evaluate(
            task=task,
            profile=profile,
            model_name=model_name,
            val_source=val_source,
            options=args,
        )
    except Exception as exc:  # noqa: BLE001 — surface any worker crash as an error event
        emit_event(
            {
                "kind": "error",
                "message": f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
            }
        )
        return 1

    finished = datetime.now(UTC)
    result = EvalResult(
        run_id=run_id,
        profile=profile,
        task=TaskEnum(task),
        model_name=model_name,
        val_source=val_source,
        overall=metrics,
        sample_count=sample_count,
        duration_seconds=(finished - started).total_seconds(),
        finished_at=finished,
    )
    result_path = run_dir / "result.json"
    result_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    emit_event(
        {
            "kind": "done",
            "message": "Evaluation completed successfully.",
            "data": {"sample_count": sample_count},
        }
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point — parse ``--run-dir`` and execute the eval run."""
    parser = argparse.ArgumentParser(prog="pd_ocr_trainer_spa.worker.evaluate")
    parser.add_argument("--run-dir", required=True, type=Path)
    ns = parser.parse_args(argv)
    return run_worker(ns.run_dir)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
