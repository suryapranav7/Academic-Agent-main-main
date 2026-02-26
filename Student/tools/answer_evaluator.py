from typing import Dict, Any

def evaluate_answer(student_answer: str, correct_answer: str) -> Dict[str, Any]:
    """
    Mock implementation of answer evaluation.
    """
    is_correct = student_answer.strip().lower() == correct_answer.strip().lower()
    return {
        "is_correct": is_correct,
        "score": 1.0 if is_correct else 0.0,
        "feedback": "Correct!" if is_correct else f"Incorrect. The correct answer was: {correct_answer}"
    }
