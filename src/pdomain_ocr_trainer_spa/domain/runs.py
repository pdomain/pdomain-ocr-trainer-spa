"""Run lifecycle domain logic (spec 06-training-runs).

A run owns a ``runs/<id>/`` directory holding ``manifest.json`` (the serialized
:class:`~pdomain_ocr_trainer_spa.core.models.Run`), ``args.json`` (the resolved
worker args), ``stdout.log`` / ``stderr.log``, and ``progress.jsonl`` (one line
per progress / metric event for chart replay).

This module is torch-free: it builds typed config models via
``training/config_build.py`` only for validation and never imports DocTR.
Run *execution* happens in the worker subprocess supervised by the pdomain-ops
``LongJobRunner`` (D-T1, D-T20).
"""

from __future__ import annotations

import contextlib
import json
import shutil
import time
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pdomain_ocr_trainer_spa.core.enums import TaskEnum
from pdomain_ocr_trainer_spa.core.errors import AppError
from pdomain_ocr_trainer_spa.core.models import Run
from pdomain_ocr_trainer_spa.domain.profiles import get_profile, normalize_profile_name

if TYPE_CHECKING:
    from pathlib import Path

    from pdomain_ocr_trainer_spa.core.app_state import AppState
    from pdomain_ocr_trainer_spa.settings import Settings

# Cap on progress.jsonl size — older lines are GC'd oldest-first (spec 06 §4).
_PROGRESS_CAP = 50_000

_SUPPORTED_TASKS = frozenset({TaskEnum.detection, TaskEnum.recognition})


# ---------------------------------------------------------------------------
# on-disk layout
# ---------------------------------------------------------------------------


def run_dir(settings: Settings, run_id: str) -> Path:
    """Return the ``runs/<id>/`` directory for a run."""
    return settings.runs_dir / run_id


def _manifest_path(settings: Settings, run_id: str) -> Path:
    return run_dir(settings, run_id) / "manifest.json"


def _args_path(settings: Settings, run_id: str) -> Path:
    return run_dir(settings, run_id) / "args.json"


def _progress_path(settings: Settings, run_id: str) -> Path:
    return run_dir(settings, run_id) / "progress.jsonl"


def write_manifest(settings: Settings, run: Run) -> None:
    """Persist a run's ``manifest.json``."""
    path = _manifest_path(settings, run.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(run.model_dump_json(indent=2), encoding="utf-8")


def read_manifest(settings: Settings, run_id: str) -> Run | None:
    """Read a run's ``manifest.json`` back into a :class:`Run` (None if absent)."""
    path = _manifest_path(settings, run_id)
    if not path.exists():
        return None
    try:
        return Run.model_validate_json(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


# ---------------------------------------------------------------------------
# model-name derivation (spec 06 §6)
# ---------------------------------------------------------------------------

_TASK_SLUG: dict[TaskEnum, str] = {
    TaskEnum.detection: "detection",
    TaskEnum.recognition: "recognition",
    TaskEnum.typeface_classification: "typeface-classification",
    TaskEnum.glyph_classification: "glyph-classification",
}


def derive_model_name(
    settings: Settings,
    *,
    profile: str,
    task: TaskEnum,
    qualifier: str | None = None,
) -> str:
    """Derive ``pd-{language}-{typeface}-{task}-{date}[-{qualifier}]`` (spec 06 §6).

    Raises ``409 run.profile_incomplete`` when the profile lacks a language or
    typeface — the SPA surfaces this as an inline form error.
    """
    prof = get_profile(settings, profile)
    if not prof.language or not prof.typeface:
        raise AppError(
            code="run.profile_incomplete",
            message=(
                "Set language + typeface on this profile before training, "
                "or enter an explicit Model name override."
            ),
            status_code=409,
        )
    typeface = prof.typeface.value if hasattr(prof.typeface, "value") else str(prof.typeface)
    date = datetime.now(UTC).strftime("%Y-%m-%d")
    parts = ["pd", prof.language, typeface, _TASK_SLUG[task], date]
    name = "-".join(parts)
    if qualifier:
        name = f"{name}-{qualifier}"
    return name


# ---------------------------------------------------------------------------
# create / validate
# ---------------------------------------------------------------------------


def _new_run_id() -> str:
    """Return a sortable run id (timestamp-prefixed; stable across restarts)."""
    return f"{int(time.time() * 1000):013d}-{uuid.uuid4().hex[:8]}"


def _validate_task_supported(task: TaskEnum) -> None:
    if task not in _SUPPORTED_TASKS:
        raise AppError(
            code="run.task_unsupported",
            message=f"Training task {task.value!r} is not yet supported",
            status_code=422,
        )


def _validate_training_data(settings: Settings, profile: str, task: TaskEnum) -> None:
    """Ensure the profile+task has a non-empty ``labels.json`` (spec 06 §2)."""
    labels = settings.ml_training_dir / profile / task.value / "labels.json"
    entries: object = None
    if labels.exists():
        try:
            entries = json.loads(labels.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            entries = None
    if not isinstance(entries, dict) or not entries:
        raise AppError(
            code="run.no_training_data",
            message=(
                f"No training data for {profile!r} / {task.value} — "
                f"label at least one item before starting a run."
            ),
            status_code=409,
        )


def create_run(
    settings: Settings,
    *,
    profile: str,
    task: TaskEnum,
    args: dict[str, object],
    notes: str | None = None,
    device: int | None = None,
    seed: int | None = None,
    model_name: str | None = None,
    qualifier: str | None = None,
) -> Run:
    """Create a run: validate, derive the model name, write the run dir.

    Does not submit the worker job — :func:`prepare_worker_args` plus the
    ``LongJobRunner`` submission live in ``api/runs.py`` so the domain layer
    stays torch- and process-free.
    """
    normalized = normalize_profile_name(profile)
    _validate_task_supported(task)
    get_profile(settings, normalized)  # 404 if the profile is unknown
    _validate_training_data(settings, normalized, task)

    resolved_name = model_name or derive_model_name(
        settings, profile=normalized, task=task, qualifier=qualifier
    )

    run = Run(
        id=_new_run_id(),
        profile=normalized,
        task=task,
        kind="train",
        status="pending",
        model_name=resolved_name,
        args=dict(args),
        notes=notes,
        device=device,
        seed=seed,
        started_at=datetime.now(UTC),
    )

    rd = run_dir(settings, run.id)
    rd.mkdir(parents=True, exist_ok=True)
    write_manifest(settings, run)
    _args_path(settings, run.id).write_text(
        json.dumps(prepare_worker_args(settings, run), indent=2), encoding="utf-8"
    )
    (rd / "stdout.log").touch()
    (rd / "stderr.log").touch()
    _progress_path(settings, run.id).touch()
    return run


def prepare_worker_args(settings: Settings, run: Run) -> dict[str, object]:
    """Resolve the run's args dict for the worker (fills dataset + output paths)."""
    args = dict(run.args)
    args.setdefault(
        "train_path",
        str(settings.ml_training_dir / run.profile / run.task.value),
    )
    args.setdefault(
        "val_path",
        str(settings.ml_validation_dir / run.profile / run.task.value),
    )
    args.setdefault(
        "output_dir",
        str(run_dir(settings, run.id) / "artefacts"),
    )
    args.setdefault("name", run.model_name)
    # The worker writes the model sidecar under this dir on a successful run.
    args.setdefault(
        "shared_models_dir",
        str(settings.shared_models_dir / run.profile / run.task.value),
    )
    return args


# ---------------------------------------------------------------------------
# status transitions
# ---------------------------------------------------------------------------


def update_run(settings: Settings, run: Run, **changes: object) -> Run:
    """Apply changes to a run, persist the manifest, and return the new run."""
    updated = run.model_copy(update=changes)
    write_manifest(settings, updated)
    return updated


def mark_running(settings: Settings, run: Run, job_id: str) -> Run:
    """Transition a run to ``running`` and link its job id."""
    return update_run(settings, run, status="running", job_id=job_id)


def mark_terminal(
    settings: Settings,
    run: Run,
    *,
    status: str,
    exit_code: int | None = None,
) -> Run:
    """Transition a run to a terminal status with a finish timestamp."""
    return update_run(
        settings,
        run,
        status=status,
        exit_code=exit_code,
        finished_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# progress.jsonl (chart replay, spec 06 §4)
# ---------------------------------------------------------------------------


def append_progress(settings: Settings, run_id: str, record: dict[str, object]) -> None:
    """Append one ``progress.jsonl`` line, GC'ing oldest lines past the cap."""
    path = _progress_path(settings, run_id)
    if not path.parent.exists():
        return
    line = json.dumps({"t": time.time(), **record})
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    _gc_progress(path)


def _gc_progress(path: Path) -> None:
    """Trim ``progress.jsonl`` to the newest ``_PROGRESS_CAP`` lines."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    if len(lines) <= _PROGRESS_CAP:
        return
    path.write_text("\n".join(lines[-_PROGRESS_CAP:]) + "\n", encoding="utf-8")


def read_progress(settings: Settings, run_id: str) -> list[dict[str, object]]:
    """Read a run's ``progress.jsonl`` back into a list of records."""
    path = _progress_path(settings, run_id)
    if not path.exists():
        return []
    records: list[dict[str, object]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            parsed: object = json.loads(line)
        except ValueError:
            continue
        if isinstance(parsed, dict):
            records.append(parsed)
    return records


# ---------------------------------------------------------------------------
# discovery / listing
# ---------------------------------------------------------------------------


def list_runs(settings: Settings) -> list[Run]:
    """List every run discovered under ``runs/``, newest first."""
    runs_root = settings.runs_dir
    if not runs_root.exists():
        return []
    runs: list[Run] = []
    for child in runs_root.iterdir():
        if not child.is_dir():
            continue
        run = read_manifest(settings, child.name)
        if run is not None:
            runs.append(run)
    runs.sort(key=lambda r: r.started_at, reverse=True)
    return runs


def get_run(settings: Settings, run_id: str) -> Run:
    """Return one run by id (404 ``run.unknown`` if absent)."""
    run = read_manifest(settings, run_id)
    if run is None:
        raise AppError(
            code="run.unknown",
            message=f"No run with id {run_id!r}",
            status_code=404,
        )
    return run


def delete_run(settings: Settings, run_id: str) -> None:
    """Delete a terminal run's directory (409 if running or artefacts exist)."""
    run = get_run(settings, run_id)
    if run.status in {"pending", "running"}:
        raise AppError(
            code="run.not_terminal",
            message="Cannot delete a run that is still pending or running.",
            status_code=409,
        )
    artefacts = run_dir(settings, run_id) / "artefacts"
    if artefacts.exists() and any(artefacts.iterdir()):
        raise AppError(
            code="run.has_artefacts",
            message="Cannot delete a run that still has artefacts on disk.",
            status_code=409,
        )
    shutil.rmtree(run_dir(settings, run_id), ignore_errors=True)


# ---------------------------------------------------------------------------
# crash recovery (D-T3, spec 06 §3)
# ---------------------------------------------------------------------------


def hydrate_runs(state: AppState) -> None:
    """Reconcile on-disk runs at boot: a ``running`` run with no live job fails.

    Populates ``state.runs`` keyed by run id. Any run left ``running`` (or
    ``pending``) without a live ``LongJobRunner`` job is marked ``failed`` with
    ``exit_code = -1`` and a synthetic ``stderr.log`` line (D-T3).
    """
    settings = state.settings
    state.runs.clear()
    for disk_run in list_runs(settings):
        run = disk_run
        if run.status in {"pending", "running"} and not _job_is_live(state, run):
            run = mark_terminal(settings, run, status="failed", exit_code=-1)
            stderr = run_dir(settings, run.id) / "stderr.log"
            with contextlib.suppress(OSError), stderr.open("a", encoding="utf-8") as fh:
                fh.write("[trainer-spa] process gone before exit; marked failed at boot\n")
        state.runs[run.id] = run


def _job_is_live(state: AppState, run: Run) -> bool:
    """True when the run's job_id resolves to a non-terminal job in the runner.

    The job registry survives a restart but the worker process does not, so a
    job that still reports ``running`` after a crash is treated as dead unless
    the runner can prove a live process. The conservative default is *not
    live* — crash recovery fails the run rather than stranding it.
    """
    del state, run
    return False
