#!/usr/bin/env python3
"""Quick test to verify languages parameter parsing works correctly."""

from pathlib import Path

import requests

# Test with the actual server (needs to be running)
BASE_URL = "http://localhost:8000"


def test_languages_param_formats():
    """Test that languages parameter works in new array format."""

    # Create a small test image
    test_file = Path("samples/numbers_gs150.jpg")
    if not test_file.exists():
        print(f"Test file not found: {test_file}")
        return

    print("Testing /sync/tesseract (baseline - still uses string format)...")
    with open(test_file, "rb") as f:
        # Tesseract uses '+' separator format (unchanged)
        response = requests.post(
            f"{BASE_URL}/sync/tesseract", files={"file": f}, data={"lang": "eng"}
        )
    print(f"  Status: {response.status_code}")
    if response.status_code != 200:
        print(f"  Error: {response.json()}")

    print("\nTesting /sync/easyocr with new array format...")
    with open(test_file, "rb") as f:
        # New format: multiple -F parameters
        files = {"file": f}
        data = [("languages", "en")]  # This simulates -F 'languages=en'
        response = requests.post(f"{BASE_URL}/sync/easyocr", files=files, data=data)
    print(f"  Status: {response.status_code}")
    if response.status_code != 200:
        print(f"  Error: {response.json()}")

    print("\nTesting /sync/easyocr with multiple languages...")
    with open(test_file, "rb") as f:
        files = {"file": f}
        # Multiple languages: -F 'languages=en' -F 'languages=ch_sim'
        data = [("languages", "en"), ("languages", "ch_sim")]
        response = requests.post(f"{BASE_URL}/sync/easyocr", files=files, data=data)
    print(f"  Status: {response.status_code}")
    if response.status_code != 200:
        print(f"  Error: {response.json()}")

    print("\nTesting /sync/ocrmac with new array format...")
    with open(test_file, "rb") as f:
        files = {"file": f}
        data = [("languages", "en-US")]  # This simulates -F 'languages=en-US'
        response = requests.post(f"{BASE_URL}/sync/ocrmac", files=files, data=data)
    print(f"  Status: {response.status_code}")
    if response.status_code != 200:
        print(f"  Error: {response.json()}")

    print("\nTesting /sync/ocrmac with multiple languages...")
    with open(test_file, "rb") as f:
        files = {"file": f}
        # Multiple languages: -F 'languages=en-US' -F 'languages=de-DE'
        data = [("languages", "en-US"), ("languages", "de-DE")]
        response = requests.post(f"{BASE_URL}/sync/ocrmac", files=files, data=data)
    print(f"  Status: {response.status_code}")
    if response.status_code != 200:
        print(f"  Error: {response.json()}")


if __name__ == "__main__":
    print("=" * 60)
    print("Parameter Format Verification Test")
    print("=" * 60)
    print("\nNOTE: This test requires the server to be running:")
    print("  uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000")
    print("\n" + "=" * 60 + "\n")

    try:
        test_languages_param_formats()
        print("\n" + "=" * 60)
        print("Test completed!")
        print("=" * 60)
    except requests.exceptions.ConnectionError:
        print("\nERROR: Cannot connect to server. Please start it first:")
        print("  uv run uvicorn src.main:app --reload")
