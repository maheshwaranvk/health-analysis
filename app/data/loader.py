"""
Data loader module.

Reads both health datasets (CSV primary, Excel optional),
preserves raw nulls, validates columns, and normalizes into DataFrames.
"""

from pathlib import Path

import pandas as pd

from app.core.config import settings, BASE_DIR
from app.core.logging_config import logger

# ── Critical columns: loader will FAIL if these are missing ──────────
CRITICAL_COLS_DS1 = {"Patient_Number", "Blood_Pressure_Abnormality", "Age", "BMI", "Sex"}
CRITICAL_COLS_DS2 = {"Patient_Number", "Day_Number", "Physical_activity"}

# ── Optional columns: loader will WARN if these are missing ─────────
OPTIONAL_COLS_DS1 = {
    "Level_of_Hemoglobin",
    "Genetic_Pedigree_Coefficient",
    "Pregnancy",
    "Smoking",
    "salt_content_in_the_diet",
    "alcohol_consumption_per_day",
    "Level_of_Stress",
    "Chronic_kidney_disease",
    "Adrenal_and_thyroid_disorders",
}


def _resolve_path(relative_path: str) -> Path:
    """Turn a config-relative path into an absolute path."""
    p = Path(relative_path)
    if not p.is_absolute():
        p = BASE_DIR / p
    return p


def _read_file(path: Path) -> pd.DataFrame:
    """Read a CSV or Excel file into a DataFrame, preserving nulls."""
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    elif suffix in (".xlsx", ".xlsm", ".xls"):
        return pd.read_excel(path, engine="openpyxl")
    else:
        raise ValueError(f"Unsupported file format: {suffix}")


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace from column names."""
    df.columns = df.columns.str.strip()
    return df


def _validate_columns(
    df: pd.DataFrame,
    critical: set[str],
    optional: set[str],
    dataset_label: str,
) -> None:
    """Fail on missing critical columns, warn on missing optional columns."""
    present = set(df.columns)

    missing_critical = critical - present
    if missing_critical:
        raise ValueError(
            f"{dataset_label}: missing critical columns: {sorted(missing_critical)}"
        )

    missing_optional = optional - present
    if missing_optional:
        logger.warning(
            "%s: optional columns not found (continuing): %s",
            dataset_label,
            sorted(missing_optional),
        )


def _log_shape_and_nulls(df: pd.DataFrame, label: str) -> None:
    """Log dataset shape and per-column missing-value counts."""
    logger.info("%s shape: %d rows × %d columns", label, df.shape[0], df.shape[1])
    null_counts = df.isnull().sum()
    cols_with_nulls = null_counts[null_counts > 0]
    if not cols_with_nulls.empty:
        logger.info("%s missing values:\n%s", label, cols_with_nulls.to_string())
    else:
        logger.info("%s: no missing values detected", label)


def load_dataset_1() -> pd.DataFrame:
    """Load the patient-level dataset (dataset 1)."""
    path = _resolve_path(settings.dataset_1_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset 1 not found: {path}")

    df = _read_file(path)
    df = _normalize_columns(df)
    _validate_columns(df, CRITICAL_COLS_DS1, OPTIONAL_COLS_DS1, "Dataset 1")

    # Convert numeric columns safely — preserve nulls
    numeric_cols = [
        "Patient_Number", "Blood_Pressure_Abnormality", "Level_of_Hemoglobin",
        "Genetic_Pedigree_Coefficient", "Age", "BMI", "Sex", "Pregnancy",
        "Smoking", "salt_content_in_the_diet", "alcohol_consumption_per_day",
        "Level_of_Stress", "Chronic_kidney_disease", "Adrenal_and_thyroid_disorders",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    _log_shape_and_nulls(df, "Dataset 1")
    return df


def load_dataset_2() -> pd.DataFrame:
    """Load the daily activity history dataset (dataset 2)."""
    path = _resolve_path(settings.dataset_2_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset 2 not found: {path}")

    df = _read_file(path)
    df = _normalize_columns(df)
    _validate_columns(df, CRITICAL_COLS_DS2, set(), "Dataset 2")

    # Convert numeric columns safely — preserve nulls
    for col in ["Patient_Number", "Day_Number", "Physical_activity"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    _log_shape_and_nulls(df, "Dataset 2")
    return df
