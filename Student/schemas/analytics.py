from typing import List, Dict, Any
from pydantic import BaseModel


class WeakArea(BaseModel):
    concept: str
    frequency: int


class StudentAnalytics(BaseModel):
    student_id: str
    overall_progress: float
    completed_modules: int
    total_modules: int
    weak_areas: List[str] # Changed to str for legacy compatibility
    weak_areas_map: Dict[str, Any] = {} # New detailed map
    average_score: float
    module_breakdown: List[Dict[str, Any]] = []
