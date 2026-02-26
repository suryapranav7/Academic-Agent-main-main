from typing import List, Optional

from db.repositories.student_repo import StudentRepository
from db.repositories.curriculum_repo import CurriculumRepository
from schemas.student_state import StudentState, ModuleProgress


class StateManager:
    """
    DB-backed student state manager.
    Owns progression rules, not storage.
    """

    def __init__(self):
        self.student_repo = StudentRepository()
        self.curriculum_repo = CurriculumRepository()

    # -------------------------------------------------
    # Initialization
    # -------------------------------------------------


    def initialize_student(self, student_id: str, subject_id: str, grade: str = "9"):
        """
        Initialize student progress for all modules in a subject.
        Handles subject switching by checking if progress exists FOR THIS SUBJECT.
        """
        # Fetch target modules for this subject
        modules = self.curriculum_repo.get_modules_for_subject(subject_id)
        if not modules:
            return # No modules to initialize
            
        target_module_ids = {m["module_id"] for m in modules}

        # Check existing progress
        existing_progress = self.student_repo.get_module_progress(student_id)
        
        # Determine if we need to initialize
        # We check if any of the target modules are already in existing_progress
        existing_module_ids = {row["module_id"] for row in existing_progress}
        
        # If all target modules already exist, we skip
        if target_module_ids.issubset(existing_module_ids):
             return

        # Ensure student record exists (idempotent)
        self.student_repo.create_student(student_id, grade=grade)

        # Initialize missing modules
        for idx, module in enumerate(modules):
            mod_id = module["module_id"]
            if mod_id not in existing_module_ids:
                status = "unlocked" if idx == 0 else "locked" # Default logic
                
                self.student_repo.update_module_status(
                    student_id=student_id,
                    module_id=mod_id,
                    status=status,
                    best_score=0.0
                )

    # -------------------------------------------------
    # Permission Checks
    # -------------------------------------------------

    def can_learn(self, student_id: str, module_id: str) -> bool:
        progress = self.student_repo.get_module_progress(student_id)

        for row in progress:
            if row["module_id"] == module_id:
                return row["status"] in ("unlocked", "completed")

        return False

    def can_assess(self, student_id: str, module_id: str) -> bool:
        progress = self.student_repo.get_module_progress(student_id)

        for row in progress:
            if row["module_id"] == module_id:
                return row["status"] == "unlocked" or row["status"] == "completed" # Can retry if completed

        return False

    # -------------------------------------------------
    # Progression Updates
    # -------------------------------------------------

    def record_assessment(
        self,
        student_id: str,
        module_id: str,
        score: float,
        passed: bool,
        attempt_id: str = None,
        attempt_details: list = None
    ):
        from db.repositories.assessment_repo import AssessmentRepository
        import uuid
        
        # 1. Log the attempt first
        final_attempt_id = attempt_id or str(uuid.uuid4())
        
        # Log main attempt
        # Note: log_attempt in student_repo currently takes (student_id, module_id, score, attempt_no)
        # We should use AssessmentRepository to create_assessment_attempt properly if we want to link details?
        # AssessmentRepository.create_assessment_attempt(attempt_id, student_id, module_id)
        # But we want to maintain the existing StudentRepo flow for now too?
        # Let's align on ONE flow:
        # A. Create attempt row in `student_attempts` using AssessmentsRepo
        # B. Log details linked to that attempt ID.
        
        AssessmentRepository.create_assessment_attempt(
            attempt_id=final_attempt_id,
            student_id=student_id,
            module_id=module_id,
            score=score
        )
        
        # Log details if any
        if attempt_details:
             for d in attempt_details:
                 AssessmentRepository.log_attempt_detail(
                     attempt_id=final_attempt_id,
                     question_id=d.get("question_id"),
                     student_answer=d.get("answer") or d.get("student_answer"), # Handle keys
                     is_correct=d.get("is_correct", False)
                 )

        # 2. Update Status (Legacy/Progress Logic)
        current_progress = self.student_repo.get_module_progress(student_id)
        # Find module progress
        attempts_count = 0
        current_best = 0.0
        
        # We don't track raw attempt count in status table anymore (except implicitly),
        # but the schema for student_module_status does NOT have 'attempts' count column in my update?
        # Wait, I removed 'attempts' column in schema.py but need it here?
        # Ah, I replaced it with `student_attempts` table.
        # So to get count, I should query `student_attempts` table.
        # For now, let's just log it. attempt_no can be queried.
        
        # Log to student_attempts - Handled by AssessmentRepository above
        # self.student_repo.log_attempt(student_id, module_id, score, 1) 
        
        # 2. Update Status
        progress = self.student_repo.get_module_progress(student_id)

        # FIX: Filter progress by Subject ID to prevent unlocking wrong subject's modules
        # We need to find the subject_id of the current module first
        current_subject_id = None
        for row in progress:
            if row["module_id"] == module_id:
                current_subject_id = row.get("subject_id")
                break
        
        # If we can't identify subject (shouldn't happen), fall back to raw list
        target_list = [r for r in progress if r.get("subject_id") == current_subject_id] if current_subject_id else progress

        for i, row in enumerate(target_list):
            if row["module_id"] == module_id:
                current_best = max(row["best_score"] or 0.0, score)
                
                # Logic: If passed, mark complete and unlock NEXT in target_list
                if passed:
                    # Mark current module completed
                    self.student_repo.update_module_status(
                        student_id, module_id, "completed", current_best
                    )

                    # Unlock next module if exists in THIS SUBJECT
                    if i + 1 < len(target_list):
                        next_module = target_list[i + 1]["module_id"]
                        self.student_repo.update_module_status(
                            student_id, next_module, "unlocked", 0.0
                        )
                else:
                    self.student_repo.update_module_status(
                        student_id, module_id, "unlocked", current_best
                    )

                return self.load_state(student_id) # Return new state object

    # -------------------------------------------------
    # Utility
    # -------------------------------------------------

    def get_current_module(self, student_id: str) -> Optional[str]:
        progress = self.student_repo.get_module_progress(student_id)

        for row in progress:
            if row["status"] == "in_progress":
                return row["module_id"]

        return None

    def load_state(self, student_id: str) -> StudentState:
        """
        Loads the full student state object for the agent.
        """
        progress_rows = self.student_repo.get_module_progress(student_id)
        
        modules_map = {}
        completed = []
        current_mod = None
        
        for row in progress_rows:
            mod_id = row["module_id"]
            status = row["status"]
            
            # Build Pydantic model for module progress
            mp = ModuleProgress(
                module_id=mod_id,
                status=status,
                attempts=row.get("attempts", 0),
                best_score=row["best_score"]
            )
            modules_map[mod_id] = mp
            
            if status == "completed":
                completed.append(mod_id)
            elif status == "in_progress":
                current_mod = mod_id
                
        return StudentState(
            student_id=student_id,
            current_module_id=current_mod,
            modules=modules_map,
            completed_modules=completed
        )
