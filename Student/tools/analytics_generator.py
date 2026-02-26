from typing import Dict, Any, List
import json
from core.state_manager import StateManager
from db.repositories.analytics_repo import AnalyticsRepository
from db.repositories.assessment_repo import AssessmentRepository
from db.repositories.curriculum_repo import CurriculumRepository
from db.repositories.student_repo import StudentRepository

def generate_analytics(student_id: str, subject_id: str = None) -> Dict[str, Any]:
    """
    Real analytics generation using StateManager and AssessmentRepository.
    Saves the computed analytics to the database (persistence).
    """
    state_manager = StateManager()
    student_state = state_manager.load_state(student_id)
    
    # --- Filter by Current Subject ---
    # Fetch student metadata to get grade
    student_record = StudentRepository.get_student(student_id)
    target_subject_id = subject_id # Use passed ID if available
    
    if student_record and not target_subject_id:
        grade = student_record.get("grade", "9")
        # Dynamic Subject Retrieval
        subjects = CurriculumRepository.get_subjects_by_grade(grade)
        
        # Default policy: Pick "Mathematics" or the first subject found
        if subjects:
            # Try to find Math
            # PRIORITY FIX: Prefer the legacy Subject ID "f4ef..." for Grade 9 to maintain student_9 history
            known_legacy_id = "f4ef477e-3dae-4ede-911b-205bfbdc202a"
            
            math_subjs = [s for s in subjects if "math" in s["subject_name"].lower()]
            print(f"DEBUG: Found {len(math_subjs)} Math subjects for Grade {grade}")
            
            # Check if legacy ID is in the list
            target_subject = next((s for s in math_subjs if s["subject_id"] == known_legacy_id), None)
            
            if target_subject:
                print(f"DEBUG: Selected Legacy Subject: {target_subject['subject_id']}")
                target_subject_id = target_subject["subject_id"]
            else:
                if math_subjs:
                     target_subject = math_subjs[0]
                     print(f"DEBUG: Legacy not found. Selected First Math: {target_subject['subject_id']}")
                     target_subject_id = target_subject["subject_id"]
                else:
                    # Fallback to first available
                    target_subject_id = subjects[0]["subject_id"]
                    print(f"DEBUG: No Math found. Selected First Available: {target_subject_id}")
    
    # 1. State-based stats (Filtered)
    all_modules = student_state.modules
    filtered_modules = {}
    
    if target_subject_id:
        # Fetch valid modules for this subject
        subject_modules = CurriculumRepository.get_modules_for_subject(target_subject_id)
        valid_module_ids = {m["module_id"] for m in subject_modules}
        
        # Filter state
        for mid, mdata in all_modules.items():
            if mid in valid_module_ids:
                filtered_modules[mid] = mdata
    else:
        # Fallback if no student record or map found
         filtered_modules = all_modules

    
    total_modules = len(filtered_modules)
    completed_modules = sum(1 for m in filtered_modules.values() if m.status == "completed")
    
    # Average score (only for attempted modules in filter)
    scores = [m.best_score for m in filtered_modules.values() if m.best_score is not None and m.best_score > 0]
    avg_score = sum(scores) / len(scores) if scores else 0.0
    
    # Module Breakdown
    breakdown = []
    for mod_id, mod_data in filtered_modules.items():
        # Exclude locked modules from report
        if mod_data.status == "locked":
            continue
            
        score_val = mod_data.best_score if mod_data.best_score is not None else 0.0
        
        # Resolve Module Name
        mod_info = CurriculumRepository.get_module(mod_id)
        mod_name = mod_info.get("module_name", "Unknown Module") if mod_info else "Unknown Module"
        
        breakdown.append({
            "module_id": mod_id,
            "module_name": mod_name,
            "status": mod_data.status,
            "score": score_val,
            "attempts": mod_data.attempts
        })
        
    # 2. Detailed Attempt Stats (from AssessmentRepository)
    details = AssessmentRepository.get_student_attempt_details(student_id)
    
    # Weak Questions: Incorrect attempts on EASY questions
    # User Rule: "if it is easy question and answered [in]correct increment count in weak_questions_count column"
    # Interpreted as: Easy question + Incorrect Answer = Weakness.
    weak_questions_list = []
    weak_areas_map = {} # {topic_id: {name: "Unknown", count: 0}}
    weak_topics_set = set() # Legacy support (actually strong topics variable name was used for this?)
    
    # We need to fetch Topic Data (Name) potentially? 
    # For now, let's just store topic_id and count. 
    # Or ideally, we'd fetch topic names. But topic_id is robust. 
    # UI can resolve names if we have a cache or fetch.
    # Let's try to infer name from question metadata if possible, but we don't store it in attempt_details.
    # We'll store topic_id -> count.
    
    for d in details:
        is_easy = d.get("difficulty") == "easy"
        is_hard = d.get("difficulty") == "hard"
        topic_id = d.get("topic_id")
        
        if not d["is_correct"] and (is_easy or d.get("difficulty") == "medium"): # Count Medium too? User said "analysis on weak areas"
            # Let's count ALL incorrects for weak areas frequency, but maybe weight them?
            # User requirement: "easy quesitons attempted, hard questions attempted" (counts)
            # "weak areas and strong areas"
            # Let's stick to: Weak = Incorrect on Easy/Medium.
            if topic_id:
                if topic_id not in weak_areas_map:
                    # Resolve Name
                    topic_data = CurriculumRepository.get_topic(topic_id)
                    topic_name = topic_data.get("topic_name", "Unknown Topic") if topic_data else "Unknown Topic"
                    
                    weak_areas_map[topic_id] = {
                        "name": topic_name,
                        "count": 0
                    }
                weak_areas_map[topic_id]["count"] += 1
                
                # Legacy List support
                if is_easy:
                    weak_questions_list.append(d["question_text"])
                    weak_topics_set.add(weak_areas_map[topic_id]["name"]) # Use Name now!
    
    # Current Module
    current_module_id = student_state.current_module_id or "Completed"
    if not student_state.current_module_id and completed_modules < total_modules:
         # Find first non-completed
         for m in student_state.modules.values():
             if m.status != "completed":
                 current_module_id = m.module_id
                 break

    # 3. Persistence
    AnalyticsRepository.update_student_analytics(
        student_id=student_id,
        current_module_id=current_module_id,
        average_score=avg_score,
        weak_questions_count=len(set(weak_questions_list)), # Count unique weak questions
        strong_topics=[], # Deprecated/Corrected: Don't pass weak topics as strong topics!
        weak_areas=weak_areas_map,
        overall_progress=round(completed_modules / total_modules, 2) if total_modules else 0
    )

    return {
        "student_id": student_id,
        "overall_progress": round(completed_modules / total_modules, 2) if total_modules else 0,
        "completed_modules": completed_modules,
        "total_modules": total_modules,
        "weak_areas": list(weak_topics_set),  # Keep returning list for legacy UI parts if any
        "weak_areas_map": weak_areas_map, # New detailed map
        "average_score": round(avg_score, 2),
        "module_breakdown": breakdown
    }
