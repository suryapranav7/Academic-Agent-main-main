import requests

URL = "https://academic-agent-vnhi.onrender.com"

print(f"--- Checking Connectivity to OLD API {URL} ---")

try:
    print("Ping /health...")
    resp = requests.get(f"{URL}/health", timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Health Check Failed: {e}")
