"""Unit tests for security utilities.

Tests for cryptographically secure job ID generation.
"""

from src.utils.security import generate_job_id


def test_generate_job_id_format():
    """Test that generated job ID is URL-safe base64 string."""
    job_id = generate_job_id()

    # Should be a string
    assert isinstance(job_id, str)

    # Should only contain URL-safe base64 characters
    # (alphanumeric, hyphen, underscore)
    valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
    assert all(c in valid_chars for c in job_id)


def test_generate_job_id_length():
    """Test that job ID has expected length.

    32 bytes of random data encoded as base64 produces 43 characters
    (without padding since token_urlsafe strips padding).
    """
    job_id = generate_job_id()

    # token_urlsafe(32) produces 43 characters
    assert len(job_id) == 43


def test_generate_job_id_uniqueness():
    """Test that multiple job IDs are unique."""
    # Generate 100 job IDs
    job_ids = [generate_job_id() for _ in range(100)]

    # All should be unique
    assert len(set(job_ids)) == 100


def test_generate_job_id_no_padding():
    """Test that job ID doesn't contain padding characters."""
    job_id = generate_job_id()

    # URL-safe base64 without padding should not contain '='
    assert "=" not in job_id


def test_generate_job_id_multiple_calls():
    """Test that multiple calls produce different IDs."""
    job_id1 = generate_job_id()
    job_id2 = generate_job_id()
    job_id3 = generate_job_id()

    assert job_id1 != job_id2
    assert job_id2 != job_id3
    assert job_id1 != job_id3


def test_generate_job_id_cryptographically_secure():
    """Test that job IDs use cryptographically secure random generator.

    This is a smoke test - we can't truly verify cryptographic security,
    but we can check that the function uses secrets module which is
    cryptographically secure.
    """

    # Verify the function uses secrets.token_urlsafe
    # by checking it's imported in the security module
    from src.utils import security

    assert hasattr(security, "secrets")


def test_generate_job_id_consistency():
    """Test that job ID format is consistent across multiple generations."""
    job_ids = [generate_job_id() for _ in range(10)]

    # All should have same length
    lengths = [len(job_id) for job_id in job_ids]
    assert len(set(lengths)) == 1
    assert lengths[0] == 43

    # All should match valid character set
    valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
    for job_id in job_ids:
        assert all(c in valid_chars for c in job_id)
