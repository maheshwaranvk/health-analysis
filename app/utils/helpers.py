"""
Shared helper utilities.
"""

import uuid


def generate_request_id() -> str:
    """Generate a unique request identifier."""
    return str(uuid.uuid4())[:12]
