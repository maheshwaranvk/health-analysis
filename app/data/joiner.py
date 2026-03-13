"""
Temporary data joiner.

Merges cleaned patient data (dataset 1) with derived activity features
(from dataset 2) on the fly.  Returns a fresh copy every time —
the joined result is never persisted as the system of record.
"""

import pandas as pd

from app.core.logging_config import logger


def get_temporarily_joined_data(
    df_patients: pd.DataFrame,
    df_activity_features: pd.DataFrame,
) -> pd.DataFrame:
    """
    Merge patient master data with derived activity features.

    Uses a LEFT join so every patient appears even if activity data
    is missing.  Returns a fresh DataFrame copy for each call.
    """
    joined = pd.merge(
        df_patients,
        df_activity_features,
        on="Patient_Number",
        how="left",
    )

    logger.debug(
        "Temporary join: %d patient rows × %d activity feature rows → %d joined rows",
        len(df_patients),
        len(df_activity_features),
        len(joined),
    )
    return joined.copy()
