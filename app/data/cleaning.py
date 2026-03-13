"""
Data cleaning module.

Applies cleaning rules to both datasets while preserving raw nulls
where appropriate and tracking what was changed.
"""

from typing import Any

import pandas as pd

from app.core.logging_config import logger


def clean_dataset_1(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Clean patient-level dataset.

    Returns:
        (cleaned_df, cleaning_notes) — cleaning_notes explains what was done.
    """
    df = df.copy()
    notes: dict[str, Any] = {}

    # ── 1. Genetic_Pedigree_Coefficient — impute median ──────────────
    if "Genetic_Pedigree_Coefficient" in df.columns:
        n_missing = int(df["Genetic_Pedigree_Coefficient"].isnull().sum())
        if n_missing > 0:
            median_val = df["Genetic_Pedigree_Coefficient"].median()
            df["Genetic_Pedigree_Coefficient"] = df["Genetic_Pedigree_Coefficient"].fillna(median_val)
            notes["Genetic_Pedigree_Coefficient"] = (
                f"Imputed {n_missing} missing values with median ({median_val:.4f})"
            )

    # ── 2. alcohol_consumption_per_day — impute median ───────────────
    if "alcohol_consumption_per_day" in df.columns:
        n_missing = int(df["alcohol_consumption_per_day"].isnull().sum())
        if n_missing > 0:
            median_val = df["alcohol_consumption_per_day"].median()
            df["alcohol_consumption_per_day"] = df["alcohol_consumption_per_day"].fillna(median_val)
            notes["alcohol_consumption_per_day"] = (
                f"Imputed {n_missing} missing values with median ({median_val:.1f})"
            )

    # ── 3. Pregnancy — sex-conditional handling ──────────────────────
    #   Sex == 0 (Male) and missing → -1 (Not_Applicable)
    #   Sex == 1 (Female) and missing → -2 (Unknown)
    #   Do NOT blindly set all nulls to 0.
    if "Pregnancy" in df.columns and "Sex" in df.columns:
        preg_null = df["Pregnancy"].isnull()
        n_male_fill = int((preg_null & (df["Sex"] == 0)).sum())
        n_female_fill = int((preg_null & (df["Sex"] == 1)).sum())

        df.loc[preg_null & (df["Sex"] == 0), "Pregnancy"] = -1
        df.loc[preg_null & (df["Sex"] == 1), "Pregnancy"] = -2

        notes["Pregnancy"] = (
            f"Males with missing Pregnancy set to -1 (Not_Applicable): {n_male_fill}; "
            f"Females with missing Pregnancy set to -2 (Unknown): {n_female_fill}"
        )

    logger.info("Dataset 1 cleaning complete. Notes: %s", notes)
    return df, notes


def clean_dataset_2(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Clean daily activity history dataset.

    Physical_activity is treated as unit-neutral.
    Missing values are preserved — never imputed to 0.

    Returns:
        (cleaned_df, cleaning_notes)
    """
    df = df.copy()
    notes: dict[str, Any] = {}

    # Ensure numeric types (already done in loader, but defensive)
    for col in ["Patient_Number", "Day_Number", "Physical_activity"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Sort for consistent ordering
    df = df.sort_values(["Patient_Number", "Day_Number"]).reset_index(drop=True)

    # Track missingness
    n_missing_activity = int(df["Physical_activity"].isnull().sum())
    notes["Physical_activity"] = (
        f"{n_missing_activity} missing values preserved (not imputed)"
    )

    # Validate day range
    if "Day_Number" in df.columns:
        day_min = int(df["Day_Number"].min())
        day_max = int(df["Day_Number"].max())
        notes["Day_range"] = f"{day_min} to {day_max}"
        if day_max > 366:
            logger.warning("Dataset 2: Day_Number max (%d) seems unusually high", day_max)

    logger.info("Dataset 2 cleaning complete. Notes: %s", notes)
    return df, notes
