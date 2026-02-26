from pydantic import BaseModel
from typing import List, Optional, Any

class StudentInitRequest(BaseModel):
    student_id: str
    subject_id: str = "ib_math_gr9"
    grade: str = "9"

class LearningRequest(BaseModel):
    student_id: str
    message: str
    context: Optional[dict] = {}

class AssessmentRequest(BaseModel):
    student_id: str
    module_id: str
    num_questions: int = 6

class AssessmentResponse(BaseModel):
    questions: List[dict]

class LearningResponse(BaseModel):
    response: str
    metadata: Optional[dict] = None

class AnalyticsResponse(BaseModel):
    student_id: str
    analytics: dict
    explanation: str

# --- Extended Schemas for UI Integration ---

class ModuleSchema(BaseModel):
    module_id: str
    module_name: str
    description: str
    order: int
    topics: List[dict]

class ProgressSchema(BaseModel):
    module_id: str
    status: str
    score: Optional[float] = None

class QuestionRequest(BaseModel):
    student_id: str
    module_id: str
    difficulty: str = "medium"


class QuestionResponse(BaseModel):
    question_id: Optional[str] = None
    question: Any # Can be dict or str
    difficulty: str
    topic_id: Optional[str] = None
    options: Optional[List[str]] = None

class EvaluationRequest(BaseModel):
    student_id: str
    question_id: Optional[str] = None
    question: str
    answer: str

class EvaluationResponse(BaseModel):
    feedback: str
    is_correct: bool

class AssessmentRecordRequest(BaseModel):
    student_id: str
    module_id: str
    score: float
    passed: bool
    attempts: Optional[List[dict]] = None

