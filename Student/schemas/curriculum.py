from typing import List, Optional
from pydantic import BaseModel


class Topic(BaseModel):
    topic_id: str
    title: str
    description: Optional[str] = None
    learning_objectives: List[str]
    difficulty: Optional[str] = None


class Module(BaseModel):
    module_id: str
    title: str
    description: Optional[str] = None
    topics: List[Topic]
    prerequisites: List[str] = []


class Curriculum(BaseModel):
    course_id: str
    course_title: str
    modules: List[Module]
