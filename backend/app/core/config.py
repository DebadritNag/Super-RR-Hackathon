"""Application settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SUPERR_", env_file=".env", extra="ignore")

    data_root: Path = Path("d:/Data")
    cricsheet_root: Path = Path("d:/Data")
    squad_csv: Path = Path("d:/Data/ipl squad.csv")
    problem_statement_pdf: Path | None = None
    backend_root: Path = BACKEND_ROOT
    duckdb_path: Path = Field(default=BACKEND_ROOT / "data" / "database" / "superr.duckdb")
    audit_dir: Path = Field(default=BACKEND_ROOT / "data" / "audit")
    reports_dir: Path = Field(default=BACKEND_ROOT / "reports")
    staging_dir: Path = Field(default=BACKEND_ROOT / "data" / "staging")
    processed_dir: Path = Field(default=BACKEND_ROOT / "data" / "processed")
    config_dir: Path = Field(default=BACKEND_ROOT / "config")
    phase25_reports_dir: Path = Field(default=BACKEND_ROOT / "data" / "reports")
    cricsheet_dirs: tuple[str, ...] = (
        "2026_male_json",
        "bbl_male_json",
        "cpl_male_json",
        "india_male_json",
        "ipl_male_json",
        "it20s_male_json",
        "mlc_male_json",
        "t20s_male_json",
    )
    log_level: str = "INFO"
    # Provisional IPL/T20I weighting (decision 4). Stored in model_versions; not used in Phase 2.
    ipl_weight: float = 0.70
    t20i_weight: float = 0.30

    @model_validator(mode="after")
    def _check_weights(self) -> "Settings":
        for name in ("ipl_weight", "t20i_weight"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within [0, 1], got {value}")
        if abs(self.ipl_weight + self.t20i_weight - 1.0) > 1e-9:
            raise ValueError("ipl_weight + t20i_weight must equal 1.0")
        return self

    @property
    def format_weights_config(self) -> Path:
        return self.config_dir / "format_weights_v1.json"

    @property
    def ingestion_errors_csv(self) -> Path:
        return self.audit_dir / "ingestion_errors.csv"

    @property
    def validation_report_json(self) -> Path:
        return self.audit_dir / "phase2_validation_report.json"

    @property
    def validation_report_md(self) -> Path:
        return self.audit_dir / "phase2_validation_report.md"


@lru_cache
def get_settings() -> Settings:
    return Settings()
