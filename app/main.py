"""
Health Data GenAI Analyzer — FastAPI application entry point.

Loads datasets once at startup (read-only shared reference data).
All per-request analysis is created fresh (stateless design).
"""

from contextlib import asynccontextmanager
from typing import Any

import pandas as pd
from fastapi import FastAPI

from app.core.config import settings, BASE_DIR
from app.core.logging_config import logger
from app.data.loader import load_dataset_1, load_dataset_2
from app.data.cleaning import clean_dataset_1, clean_dataset_2
from app.data.feature_engineering import compute_activity_features
from app.data.joiner import get_temporarily_joined_data

from app.api.routes_health import router as health_router
from app.api.routes_analysis import router as analysis_router
from app.api.routes_patient import router as patient_router
from app.api.routes_evaluation import router as evaluation_router


# ── Application state (read-only after startup) ─────────────────────
class AppState:
    """Immutable shared state loaded once at startup."""

    def __init__(self) -> None:
        self.df1_clean: pd.DataFrame | None = None
        self.df2_clean: pd.DataFrame | None = None
        self.activity_features: pd.DataFrame | None = None
        self.cleaning_notes_1: dict[str, Any] = {}
        self.cleaning_notes_2: dict[str, Any] = {}
        self.datasets_loaded: bool = False

    def get_joined(self) -> pd.DataFrame:
        """Return a fresh temporary join for each request."""
        if self.df1_clean is None or self.activity_features is None:
            raise RuntimeError("Datasets not loaded")
        return get_temporarily_joined_data(self.df1_clean, self.activity_features)


app_state = AppState()


# ── Lifespan: load and clean datasets once at startup ────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Health Data GenAI Analyzer …")

    try:
        # Load raw data
        raw_df1 = load_dataset_1()
        raw_df2 = load_dataset_2()

        # Clean data
        app_state.df1_clean, app_state.cleaning_notes_1 = clean_dataset_1(raw_df1)
        app_state.df2_clean, app_state.cleaning_notes_2 = clean_dataset_2(raw_df2)

        # Feature engineering
        app_state.activity_features = compute_activity_features(
            app_state.df2_clean
        )

        app_state.datasets_loaded = True
        logger.info(
            "Datasets ready — %d patients, %d activity rows",
            len(app_state.df1_clean),
            len(app_state.df2_clean),
        )
    except Exception as exc:
        logger.error("Failed to load datasets: %s", exc)

    yield

    logger.info("Shutting down.")


# ── Create FastAPI app ──────────────────────────────────────────────
app = FastAPI(
    title="Health Data GenAI Analyzer",
    version="1.0.0",
    description="Analytics-first GenAI solution for health data analysis",
    lifespan=lifespan,
)

# Register routers
app.include_router(health_router)
app.include_router(analysis_router, prefix="/api/v1")
app.include_router(patient_router, prefix="/api/v1")
app.include_router(evaluation_router, prefix="/api/v1")
