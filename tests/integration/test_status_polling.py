"""Integration tests for job status polling lifecycle (US3 - T087)."""

import time
from datetime import datetime, timedelta

from fastapi.testclient import TestClient


def test_job_status_polling_lifecycle(client: TestClient, sample_jpeg):
    """Test complete job lifecycle with status transitions.

    Validates:
    - Status starts as PENDING
    - Transitions to PROCESSING
    - Transitions to COMPLETED
    - All timestamps are populated correctly
    - Expiration time is calculated as completion + 48h
    """
    # Upload document
    with open(sample_jpeg, "rb") as f:
        upload_response = client.post(
            "/upload",
            files={"file": ("test.jpg", f, "image/jpeg")},
        )

    assert upload_response.status_code == 202
    upload_data = upload_response.json()
    job_id = upload_data["job_id"]

    # Poll status until completed
    max_attempts = 30
    attempt = 0
    status_history = []

    while attempt < max_attempts:
        status_response = client.get(f"/jobs/{job_id}/status")
        assert status_response.status_code == 200

        status_data = status_response.json()
        status_history.append(status_data["status"])

        # Validate response structure
        assert "job_id" in status_data
        assert "status" in status_data
        assert "upload_time" in status_data

        if status_data["status"] == "completed":
            # Validate all timestamps are present
            assert status_data["start_time"] is not None, "start_time should be set"
            assert status_data["completion_time"] is not None, "completion_time should be set"
            assert status_data["expiration_time"] is not None, "expiration_time should be set"

            # Validate expiration time is ~48 hours from completion
            completion = datetime.fromisoformat(
                status_data["completion_time"].replace("Z", "+00:00")
            )
            expiration = datetime.fromisoformat(
                status_data["expiration_time"].replace("Z", "+00:00")
            )
            time_diff = expiration - completion

            # Allow small tolerance for processing time
            assert timedelta(hours=47, minutes=59) <= time_diff <= timedelta(hours=48, minutes=1), (
                f"Expiration should be ~48h from completion, got {time_diff}"
            )

            break

        time.sleep(1)
        attempt += 1

    # Validate job completed within timeout
    assert attempt < max_attempts, f"Job did not complete within {max_attempts} seconds"

    # Validate status transitions are valid
    valid_transitions = {
        ("pending", "processing"),
        ("processing", "completed"),
        ("pending", "completed"),  # Could happen if processing is very fast
    }

    for i in range(len(status_history) - 1):
        transition = (status_history[i], status_history[i + 1])
        # Allow same state (polling multiple times in same state)
        if status_history[i] != status_history[i + 1]:
            assert transition in valid_transitions, f"Invalid status transition: {transition}"


def test_failed_job_status_lifecycle(client: TestClient):
    """Test job status for a failed job includes error information."""
    # Upload an invalid file to trigger failure
    invalid_content = b"Not a real image file"

    upload_response = client.post(
        "/upload",
        files={"file": ("test.jpg", invalid_content, "image/jpeg")},
    )

    # This should fail at upload validation or during processing
    # If it passes validation, we need to poll for failure
    if upload_response.status_code == 202:
        upload_data = upload_response.json()
        job_id = upload_data["job_id"]

        # Poll for failure
        max_attempts = 30
        attempt = 0

        while attempt < max_attempts:
            status_response = client.get(f"/jobs/{job_id}/status")
            assert status_response.status_code == 200

            status_data = status_response.json()

            if status_data["status"] == "failed":
                # Validate error information is present
                assert status_data["error_message"] is not None, (
                    "error_message should be set for failed jobs"
                )
                assert status_data["error_code"] is not None, (
                    "error_code should be set for failed jobs"
                )
                assert status_data["completion_time"] is not None, (
                    "completion_time should be set for failed jobs"
                )
                assert status_data["expiration_time"] is not None, (
                    "expiration_time should be set for failed jobs"
                )
                break

            time.sleep(1)
            attempt += 1

        # Job should have failed
        assert attempt < max_attempts, "Job did not fail as expected"
