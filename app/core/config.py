"""
Application configuration loader.

Reads settings from config/settings.yaml and environment variables.
Provides a single Settings object used across the app.
"""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

# ── Paths ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # project root
CONFIG_PATH = BASE_DIR / "config" / "settings.yaml"
FIELD_MAPPINGS_PATH = BASE_DIR / "config" / "field_mappings.yaml"
PROMPTS_DIR = BASE_DIR / "prompts"


def _load_yaml(path: Path) -> dict:
    """Read a YAML file and return its content as a dict."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class Settings:
    """Central configuration object for the application."""

    def __init__(self) -> None:
        raw: dict[str, Any] = _load_yaml(CONFIG_PATH) if CONFIG_PATH.exists() else {}

        # ── App metadata ─────────────────────────────────────────────
        app_cfg = raw.get("app", {})
        self.app_name: str = app_cfg.get("name", "Health Data GenAI Analyzer")
        self.app_version: str = app_cfg.get("version", "v1")

        # ── Dataset paths (env overrides config) ─────────────────────
        data_cfg = raw.get("data", {})
        self.dataset_1_path: str = os.getenv(
            "DATASET_1_PATH",
            data_cfg.get("dataset_1_path", "data/raw/health_dataset_1.csv"),
        )
        self.dataset_2_path: str = os.getenv(
            "DATASET_2_PATH",
            data_cfg.get("dataset_2_path", "data/raw/health_dataset_2.csv"),
        )

        # ── Model / LLM ─────────────────────────────────────────────
        model_cfg = raw.get("model", {})
        self.openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
        self.openai_model: str = os.getenv(
            "OPENAI_MODEL", model_cfg.get("model_name", "gpt-4o-mini")
        )
        self.llm_temperature: float = model_cfg.get("temperature", 0.2)
        self.llm_max_tokens: int = model_cfg.get("max_tokens", 700)

        # ── Thresholds ───────────────────────────────────────────────
        thresh = raw.get("thresholds", {})
        self.low_activity_threshold: int = thresh.get("low_activity_threshold", 4000)
        self.stable_activity_trend_delta: int = thresh.get("stable_activity_trend_delta", 500)

        # ── Safety ───────────────────────────────────────────────────
        safety = raw.get("safety", {})
        self.enable_output_validation: bool = safety.get("enable_output_validation", True)
        self.enable_pii_redaction: bool = safety.get("enable_pii_redaction", True)
        self.enable_medical_guardrails: bool = safety.get("enable_medical_guardrails", True)

        # ── Observability ────────────────────────────────────────────
        obs = raw.get("observability", {})
        self.enable_metrics: bool = obs.get("enable_metrics", True)
        self.enable_request_logging: bool = obs.get("enable_request_logging", True)

        # ── Field mappings (loaded once) ─────────────────────────────
        self.field_mappings: dict = (
            _load_yaml(FIELD_MAPPINGS_PATH) if FIELD_MAPPINGS_PATH.exists() else {}
        )

    # Convenience helpers ─────────────────────────────────────────────
    @property
    def has_openai_key(self) -> bool:
        """Return True when a non-empty OpenAI key is configured."""
        return bool(self.openai_api_key and self.openai_api_key.strip()
                     and self.openai_api_key != "your_openai_api_key_here")

    def get_prompt(self, filename: str) -> str:
        """Read a prompt text file from the prompts/ directory."""
        path = PROMPTS_DIR / filename
        return path.read_text(encoding="utf-8") if path.exists() else ""


# Module-level singleton so other modules can do: from app.core.config import settings
settings = Settings()
