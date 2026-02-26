from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime


class ModuleProgress(BaseModel):
    module_id: str
    status: str  # locked | in_progress | completed
    attempts: int = 0
    best_score: Optional[float] = None
    last_attempted: Optional[datetime] = None


class StudentState(BaseModel):
    student_id: str
    current_module_id: Optional[str]
    modules: Dict[str, ModuleProgress]
    completed_modules: List[str] = []
