from typing import Dict, Any

def infer_difficulty(student_history: Dict[str, Any]) -> str:
    """
    Mock implementation of difficulty inference.
    """
    # Simple logic: if last score > 0.8, increase difficulty
    last_score = student_history.get("last_score", 0.5)
    
    if last_score > 0.8:
        return "hard"
    elif last_score < 0.4:
        return "easy"
    else:
        return "medium"
