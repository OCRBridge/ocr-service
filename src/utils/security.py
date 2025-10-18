"""Security utilities for job ID generation."""

import secrets


def generate_job_id() -> str:
    """
    Generate a cryptographically secure job ID.

    Returns 43-character URL-safe base64 string from 32 random bytes.
    """
    return secrets.token_urlsafe(32)
