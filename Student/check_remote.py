import requests

URL = "https://academic-agent-cui.onrender.com"

print(f"--- Checking Connectivity to {URL} ---")

# 1. Check Health (GET)
try:
    print("Ping /health...")
    resp = requests.get(f"{URL}/health", timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:200]}")
except Exception as e:
    print(f"Health Check Failed: {e}")

# 2. Check Register (POST) - Dry run
try:
    print("\nTest /student/register (POST)...")
    payload = {"student_id": "test_connection", "subject_id": "test", "grade": "9"}
    resp = requests.post(f"{URL}/student/register", json=payload, timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:200]}")
except Exception as e:
    print(f"Register Check Failed: {e}")
