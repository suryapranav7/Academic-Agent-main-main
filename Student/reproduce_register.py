import os
import sys
from dotenv import load_dotenv

# Setup path
sys.path.append(os.path.join(os.path.dirname(__file__)))

# Load env for Supabase
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'Teacher', '.env'))

from db.repositories.student_repo import StudentRepository

try:
    print("Attempting to register student_9 (again)...")
    StudentRepository.create_student("student_9", "Student Nine", "9")
    print("Success!")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Failed: {e}")
