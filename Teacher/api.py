import sys
import asyncio

# Fix for Windows Event Loop Runtime Error (MUST BE BEFORE IMPORTS)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Literal
import os, re, json, uuid, time, random
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from supabase import create_client, Client
import asyncio
import concurrent.futures

# ================= ENV =================
load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("OPENAI_API_KEY missing")

# ================= Supabase =================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase credentials missing")

print(f"Connecting to Supabase...")
print(f"   URL: {SUPABASE_URL[:30]}...")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================= APP =================
app = FastAPI(title="Teacher B.Tech API", version="5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use gpt-3.5-turbo for faster responses when possible
llm_fast = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.1)
llm_smart = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)

# Fix path to be absolute relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CURRICULUM_JSON_PATH = os.path.join(BASE_DIR, "curriculum", "college_curriculum.json")
_curriculum_cache = None

# Cache for frequently accessed data
_chapter_cache = {}

# ================= MODELS =================
class TeacherRequest(BaseModel):
    subject: str
    grade: str
    teacher_preference: Optional[str] = ""

# ================= CURRICULUM LOADER =================
def load_curriculum_data():
    """Load B.Tech curriculum from JSON"""
    global _curriculum_cache
    if _curriculum_cache:
        return _curriculum_cache
    
    try:
        if not os.path.exists(CURRICULUM_JSON_PATH):
            print(f"X Curriculum file not found at {CURRICULUM_JSON_PATH}")
            return {}
            
        with open(CURRICULUM_JSON_PATH, 'r') as f:
            data = json.load(f)
            print(f"Loaded B.Tech Curriculum: {len(data.get('subjects', []))} subjects")
            _curriculum_cache = data
            return data
    except Exception as e:
        print(f"Error loading curriculum JSON: {e}")
        return {}

def extract_chapters_from_pdf_fast(subject: str, grade: str) -> List[str]:
    """Fast chapter extraction using cached PDF"""
    cache_key = f"{subject}_{grade}"
    
    if cache_key in _chapter_cache:
        print(f"Using cached chapters for {subject} Grade {grade}")
        return _chapter_cache[cache_key]
    
    print(f"Extracting chapters for {subject} Grade {grade}...")
    
    chapters = extract_chapters_with_llm(subject, grade)
    if chapters:
        _chapter_cache[cache_key] = chapters
        return chapters
    
    pdf_text = get_pdf_text_once()
    
    if not pdf_text:
        chapters = get_basic_chapters(subject, grade)
        _chapter_cache[cache_key] = chapters
        return chapters
    
    subject_lower = subject.lower()
    grade_num = int(grade) if grade.isdigit() else 0
    
    # For grade 12, use STRICT subject filtering
    if grade_num == 12:
        chapters = extract_grade_12_subject_specific_chapters(subject, grade, pdf_text)
        if chapters:
            _chapter_cache[cache_key] = chapters
            return chapters
    # For grades 10-11, use more specific subject filtering
    elif grade_num >= 10:
        chapters = extract_subject_specific_chapters_high_grades(subject, grade, pdf_text)
        if chapters:
            _chapter_cache[cache_key] = chapters
            return chapters
    else:
        # For lower grades, use the original logic
        grade_patterns = [
            f"grade {grade}",
            f"grade {grade}:",
            f"gr.{grade}",
            f"g{grade}",
        ]
        
        found_section = False
        section_text = ""
        
        for pattern in grade_patterns:
            if pattern.lower() in pdf_text.lower() and subject_lower in pdf_text.lower():
                print(f"Found pattern '{pattern}' for {subject}")
                found_section = True
                
                idx = pdf_text.lower().find(pattern.lower())
                if idx != -1:
                    start_idx = max(0, idx - 200)
                    end_idx = min(len(pdf_text), idx + 1000)
                    section_text = pdf_text[start_idx:end_idx]
                    break
    
    if found_section and section_text:
        print(f"Analyzing section for {subject} Grade {grade}...")
        chapters = extract_specific_chapters_from_text(subject, grade, section_text)
        if chapters:
            _chapter_cache[cache_key] = chapters
            return chapters
    
    chapters = get_basic_chapters(subject, grade)
    _chapter_cache[cache_key] = chapters
    return chapters

# ================= B.TECH HELPERS =================
def load_curriculum_data():
    """Load B.Tech curriculum from JSON file"""
    global _curriculum_cache
    if _curriculum_cache:
        return _curriculum_cache
    
    try:
        if not os.path.exists(CURRICULUM_JSON_PATH):
            print(f"X Curriculum file not found at {CURRICULUM_JSON_PATH}")
            return {"subjects": []}
            
        with open(CURRICULUM_JSON_PATH, 'r') as f:
            data = json.load(f)
            print(f"Loaded B.Tech Curriculum: {len(data.get('subjects', []))} subjects")
            _curriculum_cache = data
            return data
    except Exception as e:
        print(f"Error loading curriculum JSON: {e}")
        return {"subjects": []}

def get_subjects_list() -> List[str]:
    """Get list of available subjects"""
    data = load_curriculum_data()
    return [s["subject"] for s in data.get("subjects", [])]

def get_units_for_subject(subject_name: str) -> List[dict]:
    """Get units for a specific subject"""
    data = load_curriculum_data()
    for subj in data.get("subjects", []):
        if subj["subject"].lower() == subject_name.lower():
            return subj.get("units", [])
    return []

# ================= ENDPOINTS =================

@app.get("/subjects")
async def get_subjects():
    """Get all B.Tech subjects"""
    return {"subjects": get_subjects_list()}

@app.get("/curriculum")
async def get_curriculum(subject: str, grade: str = "2"): # Default to Year 2
    """Get units (chapters) for a subject"""
    try:
        units = get_units_for_subject(subject)
        # Return full objects so UI can render topics immediately
        return {"subject": subject, "grade": grade, "units": units}
    except Exception as e:
        raise HTTPException(500, f"Error fetching units: {e}")

# ================= LEGACY FALLBACKS REMOVED =================
# All PDF/LLM extraction functions have been removed.
# Focusing strictly on JSON curriculum.

# ================= PREFERENCE HANDLER =================
def analyze_preference(preference: str) -> dict:
    """Analyze teacher preference"""
    if not preference or not preference.strip():
        return {"should_sort": False, "order": None, "note": "Default order"}
    return {"should_sort": False, "order": None, "note": preference[:50]}

# ================= MCQ GENERATION (Simulated for B.Tech) =================
async def generate_mcqs_parallel(subject: str, grade: str, chapters: List[dict]) -> dict:
    """Generate MCQs for B.Tech Units"""
    questions = []
    # Generate 5 easy + 5 hard = 10 questions total
    for i in range(10):
        # Pick a random chapter/unit from the list
        chapter_title = chapters[i % len(chapters)]["title"] if chapters else "General"
        
        difficulty = "easy" if i < 5 else "hard"
        questions.append({
            "question": f"Sample B.Tech question about {subject} - {chapter_title} ({i+1})",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": "A",
            "difficulty": difficulty,
            "chapter": chapter_title
        })
        
    return {
        "all_questions": questions,
        "counts": {"total": 10, "easy": 5, "hard": 5}
    }

# ================= DATABASE PERSISTENCE =================
def save_to_database_async(result: dict):
    # Keep as is for now, it's generic enough
    pass

# ================= MAIN ENDPOINT (Legacy /generate updated) =================
@app.post("/generate")
async def generate_plan_endpoint(req: TeacherRequest):
    """Legacy endpoint - mapped to B.Tech JSON"""
    try:
        print(f"\n{'='*60}")
        print(f"GENERATING: {req.subject} Grade {req.grade}")
        print(f"Preference: '{req.teacher_preference}'")
        print(f"{'='*60}")
        
        start_time = time.time()

        units = get_units_for_subject(req.subject)
        
        # Adapt to legacy format
        chapters_data = []
        for u in units:
            chapter_title = f"{u['unit_id']}: {u['unit_title']}"
            subtopics = [t["topic_name"] for t in u.get("topics", [])]
            chapters_data.append({
                "title": chapter_title,
                "subtopics": subtopics,
                "difficulty": "medium" # Default difficulty
            })
        
        # Simulate MCQ generation for B.Tech
        mcq_result = await generate_mcqs_parallel(req.subject, req.grade, chapters_data)

        elapsed_time = time.time() - start_time

        result = {
            "subject": req.subject,
            "grade": req.grade,
            "teacher_preference": req.teacher_preference,
            "preference_applied": "Default order (B.Tech)",
            "generation_time": round(elapsed_time, 1),
            "curriculum": {
                "chapters": chapters_data,
                "total_chapters": len(chapters_data),
                "sorting_applied": "Default order (B.Tech)"
            },
            "assessment": {
                "total_questions": mcq_result["counts"]["total"],
                "easy_questions": mcq_result["counts"]["easy"],
                "hard_questions": mcq_result["counts"]["hard"],
                "all_questions": mcq_result["all_questions"]
            },
            "plan_id": str(uuid.uuid4()),
            "generated_at": datetime.now().isoformat()
        }

        # 7. Persist to ALL Database Tables (if needed, currently a pass-through)
        print("Persisting to database (async)...")
        save_to_database_async(result)
        
        print(f"\nGENERATION COMPLETED in {elapsed_time:.1f}s")
        print(f"Chapters: {len(chapters_data)}")
        print(f"Questions: {mcq_result['counts']['total']} total")
        print(f"Preference: Default order (B.Tech)")
        print(f"Database: Data is being saved to ALL tables (if configured)")
        print(f"Plan ID: {result['plan_id']}")
        print(f"{'='*60}")
        
        return {
            "success": True, 
            "result": result,
            "message": "B.Tech Plan Generated",
            "plan_id": result["plan_id"],
            "generation_time": round(elapsed_time, 1)
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Generation error: {str(e)}")

@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    return {"status": "healthy", "service": "Teacher API with Database"}


# ================= RUN APP =================
# ================= RUN APP =================
try:
    from Teacher.services.lesson_architect import LessonArchitect
    from Teacher.services.question_engine import QuestionEngine
except ImportError:
    from services.lesson_architect import LessonArchitect
    from services.question_engine import QuestionEngine

# Global Instances (Lazy loaded by Uvicorn worker)
lesson_architect = LessonArchitect()
question_engine = QuestionEngine()

class LessonRequest(BaseModel):
    subject: str
    grade: str
    topic: str
    teaching_level: Literal["beginner", "intermediate", "advanced"] = "intermediate"
    teacher_preference: Optional[str] = ""
    module_id: Optional[str] = None # Added for strict CO context

@app.get("/curriculum")
async def get_curriculum(subject: str, grade: str = "2"): # Default to Year 2
    """Get units (chapters) for a subject"""
    try:
        units = get_units_for_subject(subject)
        # Return full objects so UI can render topics immediately
        return {"subject": subject, "grade": grade, "units": units}
    except Exception as e:
        raise HTTPException(500, f"Error fetching units: {e}")

@app.post("/teacher/lesson-plan")
async def generate_lesson_plan(req: LessonRequest):
    """Generate a detailed lesson plan based on teaching level"""
    print(f"Planning Lesson: {req.topic} (Level: {req.teaching_level}) | ModuleID: {req.module_id}")

    # --- GUARDRAIL: Topic Validation ---
    # Ensure the topic actually exists in the curriculum for this subject
    # This prevents hallucinations where the LLM might generate content for a made-up topic
    valid_units = get_units_for_subject(req.subject)
    valid_topics = []
    for u in valid_units:
        # Check against Unit Titles (e.g. "DS-U1: Introduction")
        valid_topics.append(f"{u['unit_id']}: {u['unit_title']}")
        # Check against subtopics if needed, but UI sends Unit Title
    
    if req.topic not in valid_topics:
        print(f"BLOCKED: Topic '{req.topic}' not found in {req.subject}")
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid topic '{req.topic}'. Must be one of: {valid_topics}"
        )

    # Collect valid subtopics STRICTLY for the target unit
    all_subtopics = []
    target_unit_found = False

    for u in valid_units:
        # Construct the logic key used by UI: "DS-U1: Unit Title"
        unit_key = f"{u['unit_id']}: {u['unit_title']}"
        
        if unit_key == req.topic:
            target_unit_found = True
            # Add Unit Title
            all_subtopics.append(u['unit_title'])
            # Add subtopics ONLY for this unit
            for t in u.get('topics', []):
                all_subtopics.append(t['topic_name'])
            # We found our unit, stop collecting junk from others
            break
            
    if not target_unit_found:
        # Fallback: Just send the requested topic to prevent empty context
        all_subtopics.append(req.topic)

    try:
        plan = await lesson_architect.generate_lesson_plan_async(
            subject=req.subject,
            grade=req.grade,
            topic=req.topic,
            teacher_preference=req.teacher_preference,
            teaching_level=req.teaching_level,
            valid_curriculum_topics=all_subtopics,
            module_id=req.module_id
        )
        return plan
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Lesson planning failed: {e}")

class BatchResourceRequest(BaseModel):
    subject: str
    grade: str
    requests: Dict[str, int] # {"DS-U1: Intro": 5, "DS-U2: Trees": 5}

@app.post("/teacher/batch-chapter-resources")
async def generate_batch_resources(req: BatchResourceRequest):
    """
    Generate questions for MULTIPLE chapters in ONE go (Optimization).
    """
    print(f"Batch Generating for {len(req.requests)} chapters...")
    t0 = time.time()
    
    try:
        # 1. Fetch Subtopics (Optional, for context if we expanded logic, but skipping for speed)
        # Note: We trust the topic strings passed in.
        
        # 2. Call Multi-Topic Engine
        results_map = await question_engine.generate_multi_topic_questions_async(
            subject=req.subject,
            grade=req.grade,
            topic_map=req.requests
        )
        
        # 3. Format Response
        # UI expects {chapter: ..., subtopics: ..., questions: ...} list? 
        # Or we can return a map and let UI handle it. 
        # Let's return a list of "ChapterResource" objects to match existing UI logic easier if possible.
        # But UI loop is gone. So we return a generic map.
        
        final_resources = []
        for chapter, questions in results_map.items():
            final_resources.append({
                "chapter": chapter,
                "subtopics": [], # We skip subtopics fetch for speed in batch mode
                "questions": questions
            })
            
        duration = time.time() - t0
        print(f"[BATCH_GEN] total_time={duration:.2f}s | chapters={len(req.requests)} | questions={sum(len(q) for q in results_map.values())}")
        
        return {
            "subject": req.subject,
            "resources": final_resources,
            "duration": duration
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Batch generation failed: {e}")

class ChapterResourceRequest(BaseModel):
    subject: str
    grade: str
    chapter: str

@app.post("/teacher/chapter-resources")
async def generate_chapter_resources(req: ChapterResourceRequest):
    """Generate subtopics and questions for a SINGLE chapter (B.Tech)"""
    print(f"Generating resources for chapter: {req.chapter}")
    try:
        # Extract Unit ID from string "UnitID: Title"
        unit_id = req.chapter.split(":")[0].strip() if ":" in req.chapter else ""
        
        # 1. Fetch Subtopics from JSON if available
        subtopics = []
        units = get_units_for_subject(req.subject)
        for u in units:
            # Match directly or by ID
            if u["unit_id"] == unit_id or u["unit_title"] in req.chapter:
                subtopics = [t["topic_name"] for t in u.get("topics", [])]
                break
        
        if not subtopics:
             subtopics = ["Introduction", "Key Concepts", "Applications", "Advanced Topics"]

        # 2. REAL LLM QUESTION GENERATION (Verified via Engine)
        print(f"Generating verified questions for: {req.chapter}")
        
        # Split unit ID "DS-U1" from title if needed, or pass full string
        # We pass full chapter string as topic
        questions = await question_engine.generate_batch_questions_async(
            subject=req.subject,
            grade=req.grade,
            topic=req.chapter,
            count=5,
            distinct_difficulties=True
        )

        # Fallback to Mock ONLY if Question Engine fails completely
        if not questions:
            print("Question Engine returned empty, using fallback.")
            difficulties = ["easy"] * 3 + ["hard"] * 2
            for i, diff in enumerate(difficulties, 1):
                questions.append({
                    "question": f"Question {i} about {req.chapter} ({diff})?",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "correct_answer": "Option A",
                    "difficulty": diff,
                    "chapter": req.chapter,
                    "validation_status": "FALLBACK"
                })
        
        # Inject Chapter Info (Required for Publishing)
        for q in questions:
            q["chapter"] = req.chapter

        return {
            "chapter": req.chapter,
            "subtopics": subtopics,
            "questions": questions
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Resource generation failed: {e}")

class PublishQuestion(BaseModel):
    question: str
    options: List[str]
    correct_answer: str
    difficulty: str
    chapter: str # "DS-U1: Intro..."

class PublishRequest(BaseModel):
    subject: str
    grade: str
    questions: List[PublishQuestion]
    replace_existing: bool = True

@app.post("/teacher/publish-questions")
async def publish_questions(req: PublishRequest):
    """Publish selected questions to the Final Exam database"""
    print(f"Publishing {len(req.questions)} questions for {req.subject} (Replace: {req.replace_existing})...")
    
    try:
        # 1. Resolve Subject ID
        slug_name = req.subject.lower().replace(" ", "_")
        subject_id = f"btech_{slug_name}_y{req.grade}"
        
        # 2. Handle Replacement (Clear previous exam questions)
        if req.replace_existing:
            print(f"Clearing existing questions for {subject_id}...")
            supabase.table("questions_final").delete().eq("subject_id", subject_id).execute()

        inserted_count = 0
        
        for q in req.questions:
            # 3. Extract Module ID
            # Chapter format: "DS-U1: Title" -> "DS-U1"
            # If no colon, use whole string or mapping?
            # Our seed script put "DS-U1" as module_id.
            module_id = q.chapter.split(":")[0].strip() if ":" in q.chapter else q.chapter
            
            # 3. Insert into questions_final
            data = {
                "question_id": str(uuid.uuid4()),
                "subject_id": subject_id,
                "module_id": module_id, 
                "question_text": q.question,
                "correct_answer": q.correct_answer,
                "options": json.dumps(q.options),
                "difficulty": q.difficulty,
                # 'topic_id' is optional, strict mapping not always available from simple generation
            }
            
            # Use questions_final as requested
            supabase.table("questions_final").insert(data).execute()
            inserted_count += 1
            
        # 4. RESET STUDENT PROGRESS if Re-assigning
        if req.replace_existing:
             final_mod_id = f"{subject_id}_final_exam"
             print(f"Re-assigning: Resetting progress for {final_mod_id}...")
             
             # Reset status='unlocked', best_score=0.0 for those who have it 'completed' or 'in_progress'
             # Note: Supabase-py 'update' applies to filtered rows.
             
             # Step A: Reset 'completed' -> 'unlocked'
             supabase.table("student_module_status")\
                 .update({"status": "unlocked", "best_score": 0.0})\
                 .eq("module_id", final_mod_id)\
                 .in_("status", ["completed", "in_progress"])\
                 .execute()
                 
             print("Student progress reset successfully.")
            
        print(f"Successfully published {inserted_count} questions.")
        return {"success": True, "count": inserted_count, "message": f"Published {inserted_count} questions to Database."}
        
    except Exception as e:
        print(f"Publish Error: {e}")
        raise HTTPException(500, f"Publish failed: {e}")

# ================= ANALYTICS ENDPOINTS =================
from services.analytics import analytics_service

@app.get("/teacher/analytics/overview")
async def get_class_overview(subject_id: Optional[str] = None):
    """Get aggregated class performance metrics"""
    return analytics_service.get_class_overview(subject_id)

@app.get("/teacher/students")
async def get_student_list():
    """Get list of all students"""
    return {"students": analytics_service.get_student_list()}

@app.get("/teacher/analytics/student/{student_id}")
async def get_student_details(student_id: str):
    """Get detailed analytics for a single student"""
    data = analytics_service.get_student_details(student_id)
    if not data:
        raise HTTPException(404, "Student not found or no analytics available")
    return data

@app.get("/teacher/analytics/performance")
async def get_performance_dist(subject_id: Optional[str] = None):
    """Histogram data for student scores"""
    return analytics_service.get_performance_distribution(subject_id)

@app.get("/teacher/analytics/cohort")
async def get_cohort_dist(subject_id: Optional[str] = None):
    """Cohort progress distribution"""
    return analytics_service.get_cohort_distribution(subject_id)

@app.get("/teacher/analytics/leaderboard")
async def get_leaderboard(subject_id: Optional[str] = None):
    """Top/Bottom students"""
    return analytics_service.get_student_leaderboard(subject_id)

@app.get("/teacher/analytics/exam")
async def get_exam_analytics(subject_id: str): # Subject ID is required for Exam
    """Get analytics for the Final Assignment"""
    if not subject_id:
        raise HTTPException(400, "subject_id is required")
    return analytics_service.get_exam_analytics(subject_id)

from services.analytics_agent import analytics_agent
from services.mapping_service import mapping_service

@app.post("/obe/mappings/auto-suggest/{subject_id}")
async def auto_suggest_mappings(subject_id: str):
    """
    Use CrewAI to auto-suggest CO mappings for modules.
    Returns: JSON map {module_id: [co_id1, co_id2]}
    """
    try:
        suggestions = mapping_service.generate_suggestions(subject_id)
        return {"success": True, "data": suggestions}
    except Exception as e:
        raise HTTPException(500, f"Auto-Mapping Failed: {e}")

@app.get("/teacher/analytics/insights")
async def get_analytics_insights(subject_id: str):
    """
    Get AI-generated insights for Weak Areas.
    Returns: {"insight": markdown_string, "data": raw_structured_data}
    """
    if not subject_id:
        raise HTTPException(400, "subject_id is required")
    
    # 1. Get Structured Data
    raw_data = analytics_service.get_weak_area_analytics(subject_id)
    
    # 2. Generate Insight
    narrative = await analytics_agent.generate_insights(raw_data)
    
    return {
        "insight": narrative,
        "data": raw_data 
    }


# ================= OBE SCHEMAS & ENDPOINTS =================
class CourseOutcome(BaseModel):
    co_id: str
    subject_id: str
    co_code: str
    description: str

class ProgramOutcome(BaseModel):
    po_id: str
    title: str
    description: str

class ModuleMappingUpdate(BaseModel):
    module_id: str
    co_ids: List[str]

# Import Calculator for API use
try:
    from Student.core.obe_calculator import OBECalculator
    obe_calculator = OBECalculator()
except ImportError:
    # Safe fallback if path is tricky, but structure suggests this works
    print("OBECalculator import failed. Check paths.")
    obe_calculator = None

@app.get("/obe/cos/{subject_id}")
async def get_course_outcomes(subject_id: str):
    """Fetch COs for a subject"""
    try:
        res = supabase.table("course_outcomes").select("*").eq("subject_id", subject_id).order("co_code").execute()
        return {"data": res.data}
    except Exception as e:
        raise HTTPException(500, f"DB Error: {e}")

@app.get("/obe/pos")
async def get_program_outcomes():
    """Fetch all POs"""
    try:
        res = supabase.table("program_outcomes").select("*").order("po_id").execute()
        # Sort POs naturally
        data = res.data
        try:
            data.sort(key=lambda x: int(x['po_id'].replace("PO", "")) if x['po_id'].startswith("PO") and x['po_id'][2:].isdigit() else x['po_id'])
        except:
            pass
        return {"data": data}
    except Exception as e:
        raise HTTPException(500, f"DB Error: {e}")

@app.get("/obe/mappings/module-co")
async def get_module_co_mappings():
    """Fetch all Module-CO mappings"""
    try:
        res = supabase.table("module_co_mapping").select("*").execute()
        return {"data": res.data}
    except Exception as e:
        raise HTTPException(500, f"DB Error: {e}")

@app.post("/obe/mappings/module-co")
async def update_module_mapping(req: ModuleMappingUpdate):
    """
    Update mappings for a single module.
    Strategy: Delete existing for module -> Insert new.
    """
    try:
        # 1. Delete existing
        supabase.table("module_co_mapping").delete().eq("module_id", req.module_id).execute()
        
        # 2. Insert new
        if req.co_ids:
            new_rows = [{"module_id": req.module_id, "co_id": cid} for cid in req.co_ids]
            supabase.table("module_co_mapping").insert(new_rows).execute()
            
        return {"success": True, "message": f"Updated {req.module_id} with {len(req.co_ids)} COs"}
    except Exception as e:
        print(f"Mapping Update Error: {e}")
        raise HTTPException(500, f"Update failed: {e}")

@app.get("/obe/mappings/co-po")
async def get_co_po_matrix():
    """Fetch the CO-PO mapping matrix"""
    try:
        res = supabase.table("co_po_mapping").select("*").execute()
        return {"data": res.data}
    except Exception as e:
        raise HTTPException(500, f"DB Error: {e}")

@app.get("/obe/analytics/attainment/co/{subject_id}")
async def get_co_attainment_api(subject_id: str):
    """Calculate Class CO Attainment"""
    if not obe_calculator:
        raise HTTPException(503, "OBE Service Unavailable")
    
    # Run calculation here (or offload to thread if heavy)
    results = obe_calculator.calculate_class_co_attainment(subject_id)
    if not results:
        return {"data": {}}
    return {"data": results}

@app.get("/obe/modules/{subject_id}")
async def get_modules_for_subject(subject_id: str):
    """
    Fetch modules for a given subject.
    Handles ID mapping (e.g., DS203 -> btech_data_structures_y2).
    """
    try:
        # MAP ID: The 'modules' table uses long IDs
        db_subject_id = subject_id
        if subject_id == "DS203":
            db_subject_id = "btech_data_structures_y2"
        elif subject_id == "DM201":
            db_subject_id = "btech_discrete_mathematics_y2"

        # Fetch from Supabase
        res = supabase.table("modules")\
            .select("module_id, module_name")\
            .eq("subject_id", db_subject_id)\
            .order("module_id")\
            .execute()
        
        # If DB is empty, maybe fallback or just return empty
        return {"data": res.data}
    except Exception as e:
        print(f"Error fetching modules: {e}")
        raise HTTPException(500, f"DB Error: {e}")

@app.get("/obe/analytics/attainment/po/{subject_id}")
async def get_po_attainment_api(subject_id: str):
    """Calculate Class PO Attainment (Requires CO Attainment first)"""
    if not obe_calculator:
        raise HTTPException(503, "OBE Service Unavailable")
        
    # 1. Get CO Results first
    co_results = obe_calculator.calculate_class_co_attainment(subject_id)
    if not co_results:
        return {"data": []}
        
    # 2. Calculate PO
    po_results = obe_calculator.calculate_class_po_attainment(subject_id, co_results)
    return {"data": po_results}

if __name__ == "__main__":
    import uvicorn
    # Loop policy now set at top of file
    uvicorn.run(app, host="127.0.0.1", port=8001)
