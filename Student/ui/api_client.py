import requests
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/")

class APIClient:
    def __init__(self, base_url=None):
        self.base_url = (base_url or API_BASE_URL).rstrip("/")

    def _post(self, endpoint, data):
        response = requests.post(f"{self.base_url}/{endpoint.lstrip('/')}", json=data)
        response.raise_for_status()
        return response.json()

    def _get(self, endpoint):
        response = requests.get(f"{self.base_url}/{endpoint.lstrip('/')}")
        response.raise_for_status()
        return response.json()

    def register_student(self, student_id, subject_id, grade):
        return self._post("/student/register", {
            "student_id": student_id,
            "subject_id": subject_id,
            "grade": grade
        })

    def get_modules(self, subject_id):
        return self._get(f"/curriculum/{subject_id}/modules")

    def get_progress(self, student_id):
        return self._get(f"/student/{student_id}/progress")

    def learn(self, student_id, message, context={}):
        return self._post("/agent/learn", {
            "student_id": student_id,
            "message": message,
            "context": context
        })

    # Assessment Flow
    def generate_question(self, student_id, module_id, difficulty="medium"):
        return self._post("/agent/question/generate", {
            "student_id": student_id,
            "module_id": module_id,
            "difficulty": difficulty
        })

    def evaluate_answer(self, student_id, question, answer, question_id=None):
        payload = {
            "student_id": student_id,
            "question": question,
            "answer": answer
        }
        if question_id:
            payload["question_id"] = question_id
            
        return self._post("/agent/question/evaluate", payload)

    def record_assessment(self, student_id, module_id, score, passed, attempts=None):
        payload = {
            "student_id": student_id,
            "module_id": module_id,
            "score": score,
            "passed": passed
        }
        if attempts:
             payload["attempts"] = attempts
             
        return self._post("/student/assessment/record", payload)

    # Analytics
    def get_analytics(self, student_id: str, subject_id: str = None) -> dict: # Added subject_id
        url = f"{self.base_url}/student/analytics/{student_id}"
        params = {}
        if subject_id:
             params["subject_id"] = subject_id
        resp = requests.get(url, params=params)
        if resp.status_code == 200:
            return resp.json()
        raise Exception(f"Failed to fetch analytics: {resp.text}")

    # Restored Methods
    def get_final_questions(self, module_id):
        """
        Fetch all questions for a final assessment module.
        """
        response = requests.get(f"{self.base_url}/student/assessment/final-questions/{module_id}")
        response.raise_for_status()
        return response.json()

    def get_subjects_by_grade(self, grade: str):
        """Fetch subjects for a grade level."""
        return self._get(f"/curriculum/grade/{grade}/subjects")

    def get_topic(self, topic_id: str):
        return self._get(f"/curriculum/topic/{topic_id}")
