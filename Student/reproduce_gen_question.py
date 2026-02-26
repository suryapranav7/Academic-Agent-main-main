import requests
import json

URL = "http://127.0.0.1:8000/agent/question/generate"

# Payload matching the user's manual request
PAYLOAD = {
    "student_id": "student_9",
    "module_id": "bc0b83e8-90bf-4535-982e-5281aba0f91d", # Maths Module from log
    "difficulty": "medium"
}

print(f"Sending request to {URL}...")
try:
    resp = requests.post(URL, json=PAYLOAD)
    print(f"Status: {resp.status_code}")
    print("Response Text:")
    print(resp.text)
except Exception as e:
    print(f"Error: {e}")
