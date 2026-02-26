import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__)))
# Load Teacher env for credentials
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'Teacher', '.env'))

from core.state_manager import StateManager
from db.repositories.student_repo import StudentRepository

# Demo Config
STUDENTS = [
    {"id": "student_9", "grade": "9", "subject": "263a46ad-617d-4c12-bf4b-636d2f2cc54e"}, # Grade 9 Math (Verified)
    {"id": "student_8", "grade": "8", "subject": "8240fd4b-d70f-4f59-9710-42483ec4a8fc"}, # Grade 8 Math
    {"id": "student_7", "grade": "7", "subject": "b20d1e3a-5f82-4c6e-9844-3d7123958afb"}, # Grade 7 Math
]

mgr = StateManager()

print("--- 🚀 STARTING EMERGENCY SEEDING ---")

for s in STUDENTS:
    try:
        print(f"\nProcessing {s['id']} (Grade {s['grade']})...")
        
        # 1. Initialize (creates Student + Module Status)
        mgr.initialize_student(s['id'], s['subject'], grade=s['grade'])
        print(f"✅ Initialization complete.")
        
    except Exception as e:
        print(f"❌ Failed: {e}")

print("\n--- SEEDING COMPLETE ---")
