from typing import List, Optional, Literal
from pydantic import BaseModel
from datetime import datetime


class DifficultyReasoning(BaseModel):
    cognitive_level: Literal["recall", "understanding", "application", "analysis", "synthesis"]
    steps_required: int
    uses_formula: bool
    requires_prior_concept_linking: bool
    justification: str


class Question(BaseModel):
    question_id: str
    question_text: str
    difficulty: str
    topic_id: Optional[str] = None
    expected_concepts: List[str]
    correct_answer: str = None
    options: List[str] = []


class AnswerEvaluation(BaseModel):
    score: float
    correct: bool
    feedback: str
    missing_concepts: List[str] = []


class AssessmentAttempt(BaseModel):
    student_id: str
    module_id: str
    questions: List[Question]
    answers: List[str]
    evaluation: List[AnswerEvaluation]
    total_score: float
    attempt_number: int
    timestamp: datetime
