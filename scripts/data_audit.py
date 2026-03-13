"""
Quick data audit script.

Loads both datasets, cleans them, engineers features,
and prints a comprehensive summary to the console.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.data.loader import load_dataset_1, load_dataset_2
from app.data.cleaning import clean_dataset_1, clean_dataset_2
from app.data.feature_engineering import compute_activity_features
from app.data.joiner import get_temporarily_joined_data


def main():
    print("=" * 60)
    print("DATA AUDIT")
    print("=" * 60)

    # Load
    raw1 = load_dataset_1()
    raw2 = load_dataset_2()
    print(f"\nRaw Dataset 1: {raw1.shape}")
    print(f"Raw Dataset 2: {raw2.shape}")

    # Clean
    df1, notes1 = clean_dataset_1(raw1)
    df2, notes2 = clean_dataset_2(raw2)
    print(f"\nCleaned Dataset 1: {df1.shape}")
    print(f"Cleaning notes: {notes1}")
    print(f"\nCleaned Dataset 2: {df2.shape}")
    print(f"Cleaning notes: {notes2}")

    # Missing values
    print("\n--- Missing values (Dataset 1) ---")
    print(df1.isnull().sum())
    print("\n--- Missing values (Dataset 2) ---")
    print(df2.isnull().sum())

    # Feature engineering
    features = compute_activity_features(df2)
    print(f"\nActivity Features: {features.shape}")
    print(features.head())

    # Join
    joined = get_temporarily_joined_data(df1, features)
    print(f"\nJoined DataFrame: {joined.shape}")
    print(joined.columns.tolist())

    print("\n" + "=" * 60)
    print("AUDIT COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
