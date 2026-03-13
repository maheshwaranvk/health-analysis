"""
Patient service.

Provides patient lookup and summary generation.
"""

from typing import Any, Optional

import pandas as pd
import numpy as np

from app.data.dictionaries import label_for
from app.core.security import DISCLAIMER


def get_patient_summary(
    df_joined: pd.DataFrame,
    patient_id: int,
) -> Optional[dict[str, Any]]:
    """
    Build a complete patient summary dict suitable for the API response.

    Returns None if the patient is not found.
    """
    row = df_joined[df_joined["Patient_Number"] == patient_id]
    if row.empty:
        return None

    r = row.iloc[0]

    def _val(v):
        if pd.isna(v):
            return "not available"
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.floating,)):
            return round(float(v), 2)
        return v

    profile: dict[str, Any] = {}
    for col in r.index:
        profile[col] = _val(r[col])

    # Build a human-readable one-liner summary
    age = _val(r.get("Age"))
    sex_label = label_for("Sex", r["Sex"]) if pd.notna(r.get("Sex")) else "not available"
    bmi = _val(r.get("BMI"))
    bp = label_for("Blood_Pressure_Abnormality", r["Blood_Pressure_Abnormality"]) if pd.notna(r.get("Blood_Pressure_Abnormality")) else "not available"
    avg_act = _val(r.get("avg_physical_activity_10d"))
    trend = _val(r.get("activity_trend"))

    summary = (
        f"Patient {patient_id}: {age}-year-old {sex_label}, "
        f"BMI {bmi}, blood pressure {bp}, "
        f"average activity level {avg_act}, trend {trend}."
    )

    return {
        "patient_id": patient_id,
        "profile": profile,
        "activity_features": {
            k: _val(r.get(k))
            for k in [
                "total_activity_days", "days_with_activity_data",
                "days_with_missing_activity", "avg_physical_activity_10d",
                "min_physical_activity_10d", "max_physical_activity_10d",
                "std_physical_activity_10d", "first_3d_avg_physical_activity",
                "last_3d_avg_physical_activity", "activity_trend_delta",
                "activity_trend", "low_activity_flag",
            ]
            if k in r.index
        },
        "summary": summary,
    }
