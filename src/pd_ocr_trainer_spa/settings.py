"""Settings for pd-ocr-trainer-spa (env prefix: PD_OCR_TRAINER_SPA_)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_app_data_root() -> Path:
    """Return OS-aware default app-data root."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "pd-ocr-trainer-spa"
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Local"
        return base / "pd-ocr-trainer-spa"
    return Path.home() / ".local" / "share" / "pd-ocr-trainer-spa"


class Settings(BaseSettings):
    """Application settings, driven by environment variables."""

    model_config = SettingsConfigDict(env_prefix="PD_OCR_TRAINER_SPA_", env_file=None)

    # Paths
    ml_training_dir: Path = Path.home() / "ml-training"
    ml_validation_dir: Path = Path.home() / "ml-validation"
    matched_ocr_dir: Path = Path.home() / "matched-ocr"
    app_data_root: Path = _default_app_data_root()
    shared_models_dir: Path = Path.home() / "shared-models"
    runs_dir: Path = _default_app_data_root() / "runs"
    labeler_export_root: Path | None = None

    # Adapters
    storage_kind: Literal["filesystem", "s3"] = "filesystem"
    auth_kind: Literal["none"] = "none"
    job_runner_kind: Literal["local", "modal", "shared_container", "fake"] = "local"
    model_registry_kind: Literal["filesystem", "huggingface_hub", "fake"] = "filesystem"

    # Jobs / GPU
    jobs_db_path: Path | None = None

    # HF
    hf_token_path: Path | None = None
    hf_default_owner: str | None = None
    hf_cache_dir: Path | None = None

    # Server
    host: str = "127.0.0.1"
    port: int = 8081
    cors_allow_origins: list[str] = ["http://localhost:5174"]
    log_level: str = "INFO"

    # Feature flags
    enable_typeface_training: bool = True
    enable_glyph_training: bool = True
    enable_hf_publish: bool = False

    @model_validator(mode="after")
    def _resolve_paths(self) -> Settings:
        """Ensure runs_dir defaults to app_data_root/runs when not overridden."""
        if self.runs_dir == _default_app_data_root() / "runs":
            self.runs_dir = self.app_data_root / "runs"
        return self
