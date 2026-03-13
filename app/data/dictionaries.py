"""
Data dictionaries module.

Provides human-readable label lookups for categorical fields
using the mappings loaded from config/field_mappings.yaml.
"""

from app.core.config import settings


def label_for(field: str, code: int | float) -> str:
    """
    Return a human-readable label for a categorical code.

    Falls back to str(code) if no mapping exists.
    """
    mapping = settings.field_mappings.get(field, {})
    return str(mapping.get(int(code), code))
