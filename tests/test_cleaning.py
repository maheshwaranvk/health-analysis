"""
Tests for data cleaning logic.
"""

import pytest
import pandas as pd
import numpy as np

from app.data.cleaning import clean_dataset_1, clean_dataset_2


def _make_raw_df1():
    """Create a minimal synthetic dataset 1."""
    return pd.DataFrame({
        "Patient_Number": [1, 2, 3, 4],
        "Blood_Pressure_Abnormality": [1, 0, 1, 0],
        "Level_of_Hemoglobin": [12.5, 14.0, 11.0, 13.5],
        "Genetic_Pedigree_Coefficient": [0.3, None, 0.5, 0.4],
        "Age": [45, 30, 55, 40],
        "BMI": [28.5, 22.0, 31.0, 25.0],
        "Sex": [1, 0, 1, 0],
        "Pregnancy": [1, None, None, None],
        "Smoking": [0, 1, 0, 1],
        "salt_content_in_the_diet": [5, 8, 6, 7],
        "alcohol_consumption_per_day": [2, None, 3, None],
        "Level_of_Stress": [2, 3, 1, 2],
        "Chronic_kidney_disease": [0, 1, 0, 0],
        "Adrenal_and_thyroid_disorders": [0, 0, 1, 0],
    })


def _make_raw_df2():
    """Create a minimal synthetic dataset 2."""
    return pd.DataFrame({
        "Patient_Number": [1, 1, 1, 2, 2, 2],
        "Day_Number": [1, 2, 3, 1, 2, 3],
        "Physical_activity": [5000, None, 6000, 3000, 4000, None],
    })


def test_clean_dataset_1_preserves_rows():
    raw = _make_raw_df1()
    cleaned, notes = clean_dataset_1(raw)
    assert len(cleaned) == len(raw)


def test_clean_dataset_1_imputes_gpc_median():
    raw = _make_raw_df1()
    cleaned, notes = clean_dataset_1(raw)
    assert cleaned["Genetic_Pedigree_Coefficient"].isnull().sum() == 0


def test_clean_dataset_1_pregnancy_male_is_not_applicable():
    raw = _make_raw_df1()
    cleaned, notes = clean_dataset_1(raw)
    males = cleaned[cleaned["Sex"] == 0]
    # Males with missing pregnancy should be -1 (Not_Applicable)
    assert (males["Pregnancy"] == -1).all()


def test_clean_dataset_1_pregnancy_female_unknown():
    raw = _make_raw_df1()
    cleaned, notes = clean_dataset_1(raw)
    # Patient 3 is female (Sex=1) with missing pregnancy → should be -2 (Unknown)
    patient3 = cleaned[cleaned["Patient_Number"] == 3]
    assert patient3["Pregnancy"].values[0] == -2


def test_clean_dataset_2_preserves_nulls():
    raw = _make_raw_df2()
    cleaned, notes = clean_dataset_2(raw)
    # Should NOT impute missing Physical_activity to 0
    assert cleaned["Physical_activity"].isnull().sum() > 0


def test_clean_dataset_2_sorted():
    raw = _make_raw_df2()
    cleaned, notes = clean_dataset_2(raw)
    assert list(cleaned["Patient_Number"]) == sorted(cleaned["Patient_Number"])
