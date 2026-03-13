"""
Query service — the structured analytics executor.

Executes the plan produced by the planner against the joined DataFrame
using deterministic Python/Pandas logic.  This is the analytics layer
that works regardless of LLM availability.
"""

from typing import Any

import pandas as pd
import numpy as np

from app.llm.planner import ALLOWED_FIELDS, ALLOWED_OPERATORS
from app.core.logging_config import logger
from app.data.dictionaries import label_for


# ── Filter application ───────────────────────────────────────────────
def _apply_filters(
    df: pd.DataFrame,
    filters: list[dict[str, Any]],
) -> pd.DataFrame:
    """Apply a list of filter clauses to a DataFrame."""
    for f in filters:
        field = f.get("field", "")
        op = f.get("operator", "")
        value = f.get("value")

        if field not in df.columns:
            logger.warning("Filter field '%s' not in DataFrame — skipping", field)
            continue
        if field not in ALLOWED_FIELDS:
            logger.warning("Filter field '%s' not allowed — skipping", field)
            continue
        if op not in ALLOWED_OPERATORS:
            logger.warning("Filter operator '%s' not allowed — skipping", op)
            continue

        col = df[field]
        if op == "==":
            df = df[col == value]
        elif op == "!=":
            df = df[col != value]
        elif op == ">":
            df = df[col > value]
        elif op == ">=":
            df = df[col >= value]
        elif op == "<":
            df = df[col < value]
        elif op == "<=":
            df = df[col <= value]
        elif op == "in":
            df = df[col.isin(value)]

    return df


# ── Group summary (for comparison / cohort intents) ──────────────────
def _group_summary(
    df: pd.DataFrame,
    group_by: list[str],
    metrics_cols: list[str],
) -> dict[str, Any]:
    """Compute mean for each metric grouped by the specified columns."""
    valid_groups = [g for g in group_by if g in df.columns and g in ALLOWED_FIELDS]
    valid_metrics = [m for m in metrics_cols if m in df.columns and m in ALLOWED_FIELDS]

    if not valid_groups or not valid_metrics:
        return _overall_summary(df, metrics_cols)

    grouped = df.groupby(valid_groups)[valid_metrics].agg(["mean", "count"])

    # Flatten to a serialisable dict
    result: dict[str, Any] = {}
    for group_vals, row in grouped.iterrows():
        key = str(group_vals)
        result[key] = {}
        for metric in valid_metrics:
            result[key][metric] = {
                "mean": round(float(row[(metric, "mean")]), 2) if pd.notna(row[(metric, "mean")]) else None,
                "count": int(row[(metric, "count")]),
            }
    return {"group_stats": result, "cohort_size": len(df)}


# ── Overall summary ─────────────────────────────────────────────────
def _overall_summary(
    df: pd.DataFrame,
    metrics_cols: list[str],
) -> dict[str, Any]:
    """Compute global descriptive statistics."""
    valid = [m for m in metrics_cols if m in df.columns]
    stats = {}
    for col in valid:
        series = df[col].dropna()
        stats[col] = {
            "mean": round(float(series.mean()), 2) if len(series) > 0 else None,
            "median": round(float(series.median()), 2) if len(series) > 0 else None,
            "std": round(float(series.std()), 2) if len(series) > 0 else None,
            "min": round(float(series.min()), 2) if len(series) > 0 else None,
            "max": round(float(series.max()), 2) if len(series) > 0 else None,
            "count": int(series.count()),
        }
    return {"overall_stats": stats, "cohort_size": len(df)}


# ── Patient detail ───────────────────────────────────────────────────
def _patient_detail(
    df: pd.DataFrame,
    patient_id: int,
) -> dict[str, Any]:
    """Return profile and activity features for a single patient."""
    patient_row = df[df["Patient_Number"] == patient_id]
    if patient_row.empty:
        return {"error": f"Patient {patient_id} not found"}

    row = patient_row.iloc[0]

    # Split into profile (dataset 1 fields) and activity features
    profile_cols = [
        "Patient_Number", "Blood_Pressure_Abnormality", "Level_of_Hemoglobin",
        "Genetic_Pedigree_Coefficient", "Age", "BMI", "Sex", "Pregnancy",
        "Smoking", "salt_content_in_the_diet", "alcohol_consumption_per_day",
        "Level_of_Stress", "Chronic_kidney_disease", "Adrenal_and_thyroid_disorders",
    ]
    activity_cols = [
        "total_activity_days", "days_with_activity_data",
        "days_with_missing_activity", "avg_physical_activity_10d",
        "min_physical_activity_10d", "max_physical_activity_10d",
        "std_physical_activity_10d", "first_3d_avg_physical_activity",
        "last_3d_avg_physical_activity", "activity_trend_delta",
        "activity_trend", "low_activity_flag",
    ]

    def _safe_val(v):
        if pd.isna(v):
            return "not available"
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.floating,)):
            return round(float(v), 2)
        return v

    profile = {c: _safe_val(row.get(c)) for c in profile_cols if c in row.index}
    activity = {c: _safe_val(row.get(c)) for c in activity_cols if c in row.index}

    return {
        "patient_profile": profile,
        "activity_features": activity,
        "cohort_size": 1,
    }


# ── Trend analysis ───────────────────────────────────────────────────
def _trend_analysis(
    df: pd.DataFrame,
    metrics_cols: list[str],
) -> dict[str, Any]:
    """Summarise activity trends across the dataset."""
    result: dict[str, Any] = {"cohort_size": len(df)}
    if "activity_trend" in df.columns:
        trend_counts = df["activity_trend"].value_counts().to_dict()
        result["activity_trend_distribution"] = trend_counts
    # Add metric summaries
    result.update(_overall_summary(df, metrics_cols))
    return result


# ── Main executor ────────────────────────────────────────────────────
def execute_plan(
    df: pd.DataFrame,
    plan: dict[str, Any],
) -> dict[str, Any]:
    """
    Execute a structured analysis plan against the joined DataFrame.

    This is the deterministic analytics layer — always correct
    regardless of LLM availability.
    """
    intent = plan.get("intent", "dataset_summary")
    patient_id = plan.get("patient_id")
    filters = plan.get("filters", [])
    group_by = plan.get("group_by", [])
    metrics_cols = plan.get("metrics", ["BMI", "avg_physical_activity_10d", "Blood_Pressure_Abnormality"])

    # Patient summary short-circuit
    if intent == "patient_summary" and patient_id is not None:
        return _patient_detail(df, patient_id)

    # Apply filters
    filtered = _apply_filters(df, filters)

    if intent in ("comparison",) and group_by:
        return _group_summary(filtered, group_by, metrics_cols)

    if intent == "cohort_analysis":
        return _overall_summary(filtered, metrics_cols)

    if intent == "trend_analysis":
        return _trend_analysis(filtered, metrics_cols)

    if intent == "risk_recommendation":
        return _overall_summary(filtered, metrics_cols)

    # Default: dataset_summary
    return _overall_summary(filtered, metrics_cols)
