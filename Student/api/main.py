import os
# Fix for CrewAI "Read-only file system" on Vercel/Render
if os.environ.get("VERCEL") == "1" or os.environ.get("RENDER") == "1":
    os.environ['HOME'] = '/tmp'
    os.environ['XDG_DATA_HOME'] = '/tmp'

# Fix for ChromaDB + SQLite on Linux
try:
    import pysqlite3
    import sys
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
    print("✅ pysqlite3 successfully monkey-patched.")
except (ImportError, KeyError) as e:
    print(f"⚠️ pysqlite3 patch skipped: {e}")

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Dict, List, Any
import os
import sys
import asyncio
import traceback

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from core.orchestrator import Orchestrator
from api.schemas import (
    StudentInitRequest, 
    LearningRequest, 
    LearningResponse,
    AssessmentRequest, 
    AssessmentResponse,
    AnalyticsResponse
)

import os
from dotenv import load_dotenv
load_dotenv()

from vector_store.chroma_store import ChromaVectorStore

# Global Orchestrator Instance
llm = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
# Lazy Load
vector_store = None
orchestrator = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print("🚀 Student Agent API Starting...")
    
    global vector_store, orchestrator
    print("⏳ Initializing Vector Store & Orchestrator...")
    vector_store = ChromaVectorStore()
    orchestrator = Orchestrator(llm=llm, vector_store_client=vector_store)
    print("✅ Initialization Complete.")
    
    yield
    # Shutdown logic
    print("🛑 Shutting down...")

app = FastAPI(
    title="Student Agent System API",
    description="Backend API for the Agentic Learning System",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependencies ---
def get_orchestrator():
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="System is initializing")
    return orchestrator

# --- Endpoints ---

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "student-agent-api"}

@app.post("/student/register")
def register_student(req: StudentInitRequest, orch: Orchestrator = Depends(get_orchestrator)):
    """
    Initialize or Load a Student Session.
    """
    try:
        orch.state_manager.initialize_student(
            student_id=req.student_id,
            subject_id=req.subject_id,
            grade=req.grade
        )
        return {"message": f"Student {req.student_id} initialized for Grade {req.grade}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/learn", response_model=LearningResponse)
def learning_chat(req: LearningRequest, orch: Orchestrator = Depends(get_orchestrator)):
    """
    Interact with the Learning Agent (RAG + Tutor).
    """
    try:
        # Orchestrator handles dispatch
        response_data = orch.handle_request(
            student_id=req.student_id,
            request_type="LEARN",
            payload={
                "module_id": req.context.get("module_id"),
                "query": req.message
            }
        )
        
        if response_data["status"] == "error":
            raise HTTPException(status_code=400, detail=response_data["message"])

        return LearningResponse(
            response=str(response_data["response"]),
            metadata={}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"CRITICAL ERROR IN LEARN ENDPOINT: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/assess", response_model=AssessmentResponse)
def generate_assessment(req: AssessmentRequest, orch: Orchestrator = Depends(get_orchestrator)):
    """
    Generate questions for a module.
    """
    try:
        response_data = orch.handle_request(
            student_id=req.student_id,
            request_type="ASSESS",
            payload={"module_id": req.module_id, "num_questions": req.num_questions}
        )
        
        if response_data["status"] == "error":
            raise HTTPException(status_code=400, detail=response_data["message"])

        # Orchestrator returns {'questions': [...]}
        return AssessmentResponse(questions=response_data["data"]["questions"])

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/student/analytics/{student_id}", response_model=AnalyticsResponse)
def get_analytics(student_id: str, subject_id: str = None, orch: Orchestrator = Depends(get_orchestrator)):
    """
    Get Student Analytics Report.
    """
    try:
        response_data = orch.handle_request(
            student_id=student_id,
            request_type="ANALYTICS",
            payload={"subject_id": subject_id} # PASS SUBJECT ID
        )
        
        if response_data["status"] == "error":
            raise HTTPException(status_code=400, detail=response_data["message"])

        data = response_data["data"]
        return AnalyticsResponse(
            student_id=student_id,
            analytics=data["analytics"],
            explanation=data["explanation"]
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"CRITICAL ERROR IN GET ANALYTICS: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "ok", "service": "student-agent-api"}



# --- UI Support Endpoints ---

from db.repositories.curriculum_repo import CurriculumRepository
from db.repositories.student_repo import StudentRepository
from db.repositories.assessment_repo import AssessmentRepository
from api.schemas import (
    ModuleSchema, 
    ProgressSchema, 
    QuestionRequest, 
    QuestionResponse,
    EvaluationRequest, 
    EvaluationResponse,
    AssessmentRecordRequest
)

@app.get("/student/assessment/final-questions/{module_id}", response_model=List[QuestionResponse])
def get_final_questions(module_id: str):
    """
    Batch retrieve ALL questions for a Final Assessment module.
    """
    try:
        # 1. Verify Module & Get Subject
        module_data = CurriculumRepository.get_module(module_id)
        if not module_data:
            raise HTTPException(status_code=404, detail="Module not found")
            
        # 2. Fetch Questions (Limit=None for ALL)
        db_questions = AssessmentRepository.get_final_questions(module_data["subject_id"], limit=None)
        
        # 3. Map to Response Schema
        response_list = []
        for q in db_questions:
            # Helper to parse options if string
            opts = q["options"]
            if isinstance(opts, str):
                import json
                try:
                    opts = json.loads(opts)
                except:
                    opts = []
                    
            response_list.append(
                QuestionResponse(
                    question_id=q["question_id"],
                    question=q["question_text"],
                    difficulty=q["difficulty"],
                    topic_id=q.get("topic_id"),
                    options=opts 
                    # Note: QuestionResponse schema in api/schemas.py might need 'options' field if not present. 
                    # Let's check schemas next. If strictly typed, might need update.
                    # Assuming standard Pydantic model usage.
                )
            )
        return response_list

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/curriculum/grade/{grade}/subjects")
def get_subjects_by_grade(grade: str):
    """
    Fetch all subjects for a specific grade level.
    """
    try:
        subjects = CurriculumRepository.get_subjects_by_grade(grade)
        return subjects 
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/curriculum/topic/{topic_id}")
def get_topic(topic_id: str):
    try:
        topic = CurriculumRepository.get_topic(topic_id)
        if not topic:
             raise HTTPException(status_code=404, detail="Topic not found")
        return topic
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/curriculum/{subject_id}/modules", response_model=List[ModuleSchema])
def get_modules(subject_id: str):
    try:
        modules_data = CurriculumRepository.get_modules_for_subject(subject_id)
        # Transform DB columns to Schema fields
        return [
            ModuleSchema(
                module_id=m["module_id"],
                module_name=m["module_name"],
                description=m["description"],
                order=m["module_order"],
                topics=[] # Topics not fetched in list view by default
            ) 
            for m in modules_data
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/student/{student_id}/progress", response_model=List[ProgressSchema])
def get_progress(student_id: str):
    try:
        progress = StudentRepository.get_module_progress(student_id)
        return progress
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/question/generate", response_model=QuestionResponse)
def generate_question(req: QuestionRequest, orch: Orchestrator = Depends(get_orchestrator)):
    """
    Generate a SINGLE question for adaptive loop.
    """
    try:
        response_data = orch.handle_request(
            student_id=req.student_id,
            request_type="GET_QUESTION",
            payload={"module_id": req.module_id, "difficulty": req.difficulty}
        )
        
        if response_data["status"] == "error":
            raise HTTPException(status_code=400, detail=response_data["message"])

        return QuestionResponse(
            question_id=response_data.get("question_id"),
            question=response_data["question"],
            difficulty=response_data["difficulty"],
            topic_id=response_data.get("topic_id")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/question/evaluate", response_model=EvaluationResponse)
def evaluate_answer(req: EvaluationRequest, orch: Orchestrator = Depends(get_orchestrator)):
    try:
        response_data = orch.handle_request(
            student_id=req.student_id,
            request_type="EVALUATE_ANSWER",
            payload={
                "question": req.question, 
                "answer": req.answer,
                "question_id": req.question_id
            }
        )
         
        # Check if Orchestra returned explicit boolean (from deterministic check)
        if "is_correct" in response_data:
            return EvaluationResponse(
                feedback=response_data["feedback"],
                is_correct=response_data["is_correct"]
            )
            
        feedback = response_data["feedback"]
        # Simple heuristic for boolean correctness from feedback string (Fallback)
        is_correct = "correct" in feedback.lower() and "incorrect" not in feedback.lower()
        
        return EvaluationResponse(
            feedback=feedback,
            is_correct=is_correct
        )

        return EvaluationResponse(
            feedback=feedback,
            is_correct=is_correct
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/student/assessment/record")
def record_assessment(req: AssessmentRecordRequest, orch: Orchestrator = Depends(get_orchestrator)):
    try:
        orch.state_manager.record_assessment(
            student_id=req.student_id,
            module_id=req.module_id,
            score=req.score,
            passed=req.passed,
            attempt_details=req.attempts
        )
        return {"status": "success", "message": "Assessment recorded."}
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"CRITICAL ERROR IN RECORD ASSESSMENT: {e}")
        raise HTTPException(status_code=500, detail=str(e))
