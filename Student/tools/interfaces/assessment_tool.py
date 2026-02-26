import uuid
from typing import List

from db.repositories.assessment_repo import AssessmentRepository
from db.repositories.curriculum_repo import CurriculumRepository


class AssessmentTool:
    """
    Assessment intelligence adapter.
    Handles question generation, evaluation, and persistence.
    """

    @staticmethod
    def generate_question(
        lesson_id: str,
        difficulty: str,
        llm
    ) -> dict:
        """
        Generate a single lesson-level question.
        """
        question_id = str(uuid.uuid4())

        # Prompt kept minimal & curriculum-bound
        prompt = f"""
        Generate ONE {difficulty} question for the lesson.
        Lesson ID: {lesson_id}
        """

        question_text = llm(prompt)

        AssessmentRepository.save_generated_question(
            question_id=question_id,
            lesson_id=lesson_id,
            difficulty=difficulty,
            question_text=question_text,
            expected_concepts=""
        )

        return {
            "question_id": question_id,
            "question_text": question_text,
            "difficulty": difficulty
        }

    @staticmethod
    def get_questions(module_id: str, difficulty: str) -> List[dict]:
        """
        Retrieves formatted Question objects for the assessment agent.
        """
        from db.supabase_client import get_supabase
        from schemas.assessment import Question
        import json
        
        supabase = get_supabase()
        
        # Determine table
        table = "questions"
        if module_id == "mod_final_exam":
            table = "questions_final"
        
        response = supabase.table(table)\
            .select("question_id, question_text, difficulty, options, correct_answer, topic_id")\
            .eq("module_id", module_id)\
            .eq("difficulty", difficulty)\
            .order("created_at", desc=True)\
            .limit(6)\
            .execute()
        
        questions = []
        for r in response.data:
            # Parse options if stored as JSON string
            opts = []
            if r["options"]:
                try:
                    opts = json.loads(r["options"])
                except:
                    pass
            
            questions.append(Question(
                question_id=r["question_id"],
                question_text=r["question_text"],
                difficulty=r["difficulty"],
                topic_id=r.get("topic_id"),
                expected_concepts=[], 
                correct_answer=r["correct_answer"],
                options=opts
            ))
        return questions

    @staticmethod
    def evaluate_answer(
        question_text: str,
        student_answer: str,
        llm
    ) -> dict:
        """
        Evaluate answer using LLM.
        """
        prompt = f"""
        Question:
        {question_text}

        Student Answer:
        {student_answer}

        Evaluate correctness.
        Return score between 0 and 1.
        """

        # NOTE: For now assume llm returns float-like string
        score = float(llm(prompt))
        is_correct = score >= 0.7

        return {
            "score": score,
            "is_correct": is_correct
        }

    @staticmethod
    def evaluate_by_id(question_id: str, student_answer: str) -> dict:
        """
        Evaluate answer based on stored ground truth. Deterministic.
        """
        from db.supabase_client import get_supabase
        from schemas.assessment import Question
        import json
        
        supabase = get_supabase()
        
        # Try fetching from both tables
        tables = ["questions", "questions_final"]
        record = None
        
        for t in tables:
            resp = supabase.table(t).select("*").eq("question_id", question_id).execute()
            if resp.data:
                record = resp.data[0]
                break
        
        if not record:
            return {"score": 0.0, "is_correct": False, "feedback": "Error: Question not found."}
            
        # Parse Question object
        opts = []
        if record["options"]:
            try:
                opts = json.loads(record["options"])
            except:
                pass

        q = Question(
            question_id=record["question_id"],
            question_text=record["question_text"],
            difficulty=record["difficulty"],
            correct_answer=record["correct_answer"],
            options=opts,
            expected_concepts=[]
        )
        
        # Use existing deterministic logic
        evaluation = AssessmentTool.evaluate(q, student_answer)
        
        return {
            "score": evaluation.score,
            "is_correct": evaluation.correct,
            "feedback": evaluation.feedback
        }

    @staticmethod
    def evaluate(question: 'Question', student_answer: str) -> 'AnswerEvaluation':
        """
        Agent-compatible evaluation returning Pydantic model.
        Uses deterministic comparison against stored ground truth.
        """
        from schemas.assessment import AnswerEvaluation
        import re

        if not question.correct_answer:
            is_correct = False
            feedback = "Error: No correct answer stored for this question."
        else:
            def normalize(text):
                if not text: return ""
                # Remove Markdown bold/italic and surrounding quotes
                text = re.sub(r"\*\*|\*|__|_", "", str(text))
                return text.strip().lower()

            def extract_option_key(text):
                """Extracts 'A', 'B', 'C', 'D' if present at start."""
                # Match "A)", "A.", "A " at start
                match = re.match(r"^([a-d])[\)\.\s]", normalize(text))
                if match:
                    return match.group(1)
                # If the string is EXACTLY "a" or "b"
                norm = normalize(text)
                if norm in ["a", "b", "c", "d"] and len(norm) == 1:
                    return norm
                return None

            sa_norm = normalize(student_answer)
            ca_norm = normalize(question.correct_answer)
            
            # --- INTELLIGENT MATCHING LOGIC ---
            
            # 1. OPTION MAPPING (Letter -> Text)
            # If student gave a Letter ("A"), and we have options, find the text.
            sa_key = extract_option_key(student_answer)
            mapped_student_text = None
            
            if sa_key and question.options:
                # Map A->0, B->1 etc
                idx = ord(sa_key) - ord('a')
                if 0 <= idx < len(question.options):
                    mapped_student_text = normalize(question.options[idx])
            
            # 2. Key-based Comparison (A vs A)
            # Valid if Correct Answer is ALSO just a letter or starts with letter
            ca_key = extract_option_key(question.correct_answer)
            
            match_found = False
            
            # Case A: Both are Keys (e.g. SA="A", CA="A")
            if sa_key and ca_key:
                if sa_key == ca_key:
                    match_found = True
            
            # Case B: Letter vs Text (e.g. SA="A" -> Mapped "Array", CA="Array")
            if not match_found and mapped_student_text:
                # Compare mapped text to normalized Correct Answer (which might involve stripping prefixes)
                
                # Strip prefix from CA if it exists (e.g. "B) Array" -> "Array")
                def strip_prefix(text):
                    return re.sub(r"^[a-d][\)\.\s]\s*", "", normalize(text))
                
                ca_pure = strip_prefix(question.correct_answer)
                sa_pure = strip_prefix(mapped_student_text)
                
                if ca_pure == sa_pure:
                    match_found = True

            # Case C: Direct Text Comparison (Fallback)
            if not match_found:
                 if sa_norm == ca_norm:
                     match_found = True
            
            is_correct = match_found
            feedback = "Correct!" if is_correct else f"Incorrect."

        score = 1.0 if is_correct else 0.0
        
        return AnswerEvaluation(
            score=score,
            correct=is_correct,
            feedback=feedback,
            missing_concepts=[]
        )

    @staticmethod
    def run_adaptive_assessment(
        *,
        student_id: str,
        module_id: str,
        lessons: List[str],
        llm,
        policy
    ) -> dict:
        """
        Runs adaptive assessment loop.
        """
        attempt_id = str(uuid.uuid4())
        AssessmentRepository.create_assessment_attempt(
            attempt_id=attempt_id,
            student_id=student_id,
            module_id=module_id
        )

        difficulty = "medium"
        total_score = 0.0
        question_count = 0

        for lesson_id in lessons:
            question = AssessmentTool.generate_question(
                lesson_id=lesson_id,
                difficulty=difficulty,
                llm=llm
            )

            # In real flow, student answers via UI
            student_answer = ""  # placeholder

            evaluation = AssessmentTool.evaluate_answer(
                question_text=question["question_text"],
                student_answer=student_answer,
                llm=llm
            )

            AssessmentRepository.save_question_attempt(
                attempt_id=attempt_id,
                question_id=question["question_id"],
                student_answer=student_answer,
                is_correct=int(evaluation["is_correct"]),
                difficulty=difficulty,
                score=evaluation["score"]
            )

            total_score += evaluation["score"]
            question_count += 1

            # Adaptive difficulty decision
            difficulty = policy.next_difficulty(
                current_difficulty=difficulty,
                score=evaluation["score"]
            )

        final_score = total_score / max(question_count, 1)

        return {
            "attempt_id": attempt_id,
            "final_score": final_score
        }
