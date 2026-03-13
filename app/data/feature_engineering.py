"""
Feature engineering module for dataset 2 (daily activity history).

All derived feature names are unit-neutral — we do NOT assume
Physical_activity represents steps or any specific unit.

Aggregates are computed from available values only (skipna=True).
Missing daily values are never replaced with 0.
"""

import pandas as pd

from app.core.config import settings
from app.core.logging_config import logger


def compute_activity_features(df_activity: pd.DataFrame) -> pd.DataFrame:
    """
    Derive per-patient activity summary features from daily records.

    Args:
        df_activity: Cleaned dataset 2 with columns
                     [Patient_Number, Day_Number, Physical_activity].

    Returns:
        DataFrame indexed by Patient_Number with derived columns.
    """
    grouped = df_activity.groupby("Patient_Number")

    features = pd.DataFrame()
    features["total_activity_days"] = grouped["Day_Number"].count()
    features["days_with_activity_data"] = grouped["Physical_activity"].count()
    features["days_with_missing_activity"] = (
        features["total_activity_days"] - features["days_with_activity_data"]
    )

    # Aggregates — computed from available values only
    features["avg_physical_activity_10d"] = grouped["Physical_activity"].mean()
    features["min_physical_activity_10d"] = grouped["Physical_activity"].min()
    features["max_physical_activity_10d"] = grouped["Physical_activity"].max()
    features["std_physical_activity_10d"] = grouped["Physical_activity"].std()

    # ── First-3-day and last-3-day averages (for trend detection) ────
    first_3d = (
        df_activity[df_activity["Day_Number"] <= 3]
        .groupby("Patient_Number")["Physical_activity"]
        .mean()
    )
    last_3d = (
        df_activity[df_activity["Day_Number"] >= 8]
        .groupby("Patient_Number")["Physical_activity"]
        .mean()
    )

    features["first_3d_avg_physical_activity"] = first_3d
    features["last_3d_avg_physical_activity"] = last_3d

    # ── Trend delta and label ────────────────────────────────────────
    features["activity_trend_delta"] = (
        features["last_3d_avg_physical_activity"]
        - features["first_3d_avg_physical_activity"]
    )

    delta_threshold = settings.stable_activity_trend_delta
    features["activity_trend"] = "stable"
    features.loc[
        features["activity_trend_delta"] > delta_threshold, "activity_trend"
    ] = "increasing"
    features.loc[
        features["activity_trend_delta"] < -delta_threshold, "activity_trend"
    ] = "decreasing"

    # ── Optional: low activity flag ──────────────────────────────────
    low_thresh = settings.low_activity_threshold
    features["low_activity_flag"] = (
        features["avg_physical_activity_10d"] < low_thresh
    ).astype(int)

    # Reset index so Patient_Number becomes a regular column
    features = features.reset_index()

    logger.info(
        "Activity features computed for %d patients. Columns: %s",
        len(features),
        list(features.columns),
    )
    return features
