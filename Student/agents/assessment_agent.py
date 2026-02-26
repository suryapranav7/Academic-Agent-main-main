
from typing import List

from crewai import Agent, Task

from core.state_manager import StateManager
from core.policies import AssessmentPolicy
from tools.interfaces.assessment_tool import AssessmentTool
from schemas.assessment import Question, AnswerEvaluation, DifficultyReasoning

import logging
import os
import json
from datetime import datetime

# --- AUDIT LOGGING SETUP ---
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
audit_logger = logging.getLogger("difficulty_audit")
audit_logger.setLevel(logging.INFO)
audit_handler = logging.FileHandler(os.path.join(LOG_DIR, "difficulty_audit.log"))
audit_handler.setFormatter(logging.Formatter('%(message)s')) # Raw JSON
if not audit_logger.handlers:
    audit_logger.addHandler(audit_handler)

# --- ROBUST DIFFICULTY RUBRIC ---
DIFFICULTY_RUBRIC = {
    "easy": {
        "min_steps": 1,
        "max_steps": 1, 
        "cognitive_levels": ["recall", "understanding"]
    },
    "medium": {
        "min_steps": 2, 
        "max_steps": 2, 
        "cognitive_levels": ["application"]
    },
    "hard": {
        "min_steps": 3, 
        "max_steps": 5, 
        "cognitive_levels": ["analysis", "synthesis"]
    }
}

def validate_difficulty(ai_output: dict, expected_difficulty: str) -> tuple[bool, list]:
    """
    Validates AI reasoning against the Rubric.
    Returns: (passed, violations_list)
    """
    rubric = DIFFICULTY_RUBRIC.get(expected_difficulty, DIFFICULTY_RUBRIC["medium"])
    violations = []

    # 1. Check Structure
    reasoning = ai_output.get("difficulty_reasoning")
    if not reasoning:
        return False, ["Missing 'difficulty_reasoning' block"]

    try:
        # Pydantic Structural Validation
        # We manually construct to check types
        dr = DifficultyReasoning(**reasoning)
    except Exception as e:
        return False, [f"Schema Validation Error: {str(e)}"]

    # 2. Check Logical Rules
    steps = dr.steps_required
    if steps < rubric["min_steps"]:
        violations.append(f"Too few steps ({steps} < {rubric['min_steps']})")
    if steps > rubric["max_steps"]:
        violations.append(f"Too many steps ({steps} > {rubric['max_steps']})")
        
    if dr.cognitive_level not in rubric["cognitive_levels"]:
        violations.append(f"Cognitive level '{dr.cognitive_level}' not allowed for {expected_difficulty}")

    return len(violations) == 0, violations


def create_assessment_agent(llm):
    """
    CrewAI Assessment Agent.
    Responsible ONLY for generating questions and evaluating answers.
    """

    return Agent(
        role="Assessment Agent",
        goal="Assess the student's understanding strictly based on the curriculum.",
        backstory=(
            "You are a strict examiner. "
            "You generate clear, curriculum-aligned questions. "
            "You never give hints or answers. "
            "You do not decide pass or fail."
        ),
        verbose=True,
        allow_delegation=False,
        tools=[],      # 🔒 tools accessed via interface functions only
        llm=llm,
    )


from db.repositories.curriculum_repo import CurriculumRepository
from db.repositories.assessment_repo import AssessmentRepository
import json

def conduct_assessment(
    *,
    agent: Agent,
    student_id: str,
    module_id: str,
    student_answers: List[str],
    state_manager: StateManager
) -> dict:
    """
    Full assessment flow for one module.
    """

    # 1️⃣ Permission check
    if not state_manager.can_assess(student_id, module_id):
        return {
            "status": "blocked",
            "message": "You are not allowed to take this assessment yet."
        }

    # 3️⃣ Retrieve questions
    # CHECK FOR FINAL ASSESSMENT
    module_data = CurriculumRepository.get_module(module_id)
    print(f"DEBUG: module_id='{module_id}'")
    print(f"DEBUG: module_data={module_data}")
    
    is_final_exam = module_data and (module_data.get("module_name") == "Final Assessment" or "final" in module_id.lower())
    print(f"DEBUG: is_final_exam={is_final_exam}")
    
    questions: List[Question] = []
    
    if is_final_exam:
        print(f"INFO: Conducting Final Assessment for {module_id}")
        # Fetch ALL questions (no limit)
        db_questions = AssessmentRepository.get_final_questions(module_data["subject_id"], limit=None)
        
        # Map to Question objects
        for db_q in db_questions:
             # Parse options if string
             opts = db_q["options"]
             if isinstance(opts, str):
                 opts = json.loads(opts)
                 
             questions.append(Question(
                 question_id=db_q["question_id"], # Ensure we use the DB ID
                 question_text=db_q["question_text"],
                 options=opts,
                 difficulty=db_q["difficulty"],
                 topic_id=db_q.get("topic_id"),
                 expected_concepts=[]
             ))
             
        if not questions:
            return {
                "status": "error",
                "message": "Final Assessment questions not found in database."
            }
    else:
        # Standard Agent Generation
        difficulty = AssessmentTool.infer_initial_difficulty(student_id)
        questions = AssessmentTool.get_questions(
            module_id=module_id,
            difficulty=difficulty
        )

    if len(student_answers) != len(questions):
        return {
            "status": "error",
            "message": "Number of answers does not match number of questions."
        }

    # 4️⃣ Evaluate answers (NO DECISION HERE)
    evaluations: List[AnswerEvaluation] = []
    total_score = 0.0

    print(f"DEBUG: Processing {len(questions)} questions and {len(student_answers)} answers")
    for question, answer in zip(questions, student_answers):
        evaluation = AssessmentTool.evaluate(question, answer)
        evaluations.append(evaluation)
        total_score += evaluation.score
        
        # 🟢 LOG GRANULAR ATTEMPT
        print(f"DEBUG: Logging attempt for {question.question_text[:20]}...")
        # Since we don't have attempt_id passed here easily without refactoring 'conduct_assessment' signature or logic,
        # we will rely on state_manager.record_assessment to create the MAIN attempt, 
        # but ideally 'attempt_details' should link to a specific attempt_id.
        # For this refactor, let's create a temporary attempt_id strictly for this session or allow decoupled detail logging if usage permits.
        # However, proper design requires 'attempt_id' to be generated at start of assessment.
        
        # NOTE: logic flow update - we need an attempt_id to link details.
        
        # Temporary fallback: We'll skip granular detail logging here or we need to Generate attempt_id beforehand.
        # Let's Generate attempt_id NOW.
    
    # Generate Attempt ID first
    import uuid
    attempt_id = str(uuid.uuid4())

    # Re-iterate to log details
    for question, answer, evaluation in zip(questions, student_answers, evaluations):
         AssessmentRepository.log_attempt_detail(
            attempt_id=attempt_id,
            question_id=question.question_id,
            student_answer=answer,
            is_correct=evaluation.is_correct
        )

    # DEBUG SCORING ANOMALY
    print(f"DEBUG SCORING: Total Score: {total_score}")
    print(f"DEBUG SCORING: Questions Len: {len(questions)}")
    print(f"DEBUG SCORING: Answers Len: {len(student_answers)}")
    
    final_score = total_score / len(questions)

    # 5️⃣ Policy decision (OUTSIDE agent)
    passed = AssessmentPolicy.is_pass(final_score)
    can_retry = AssessmentPolicy.can_retry(
        state_manager.load_state(student_id)
        .modules[module_id]
        .attempts
    )

    # 6️⃣ Update state (SINGLE authority)
    # We pass the pre-generated attempt_id to be used/logged
    updated_state = state_manager.record_assessment(
        student_id=student_id,
        module_id=module_id,
        score=final_score,
        passed=passed,
        attempt_id=attempt_id # PASS THIS NEW ARGUMENT
    )

    # Calculate Immediate Session Analytics
    easy_qs = [q for q in questions if q.difficulty == "easy"]
    hard_qs = [q for q in questions if q.difficulty == "hard"]
    
    easy_attempted = len(easy_qs)
    hard_attempted = len(hard_qs)
    
    # Weak Areas: Topics of incorrect Easy questions
    weak_topics = []
    for q, eval in zip(questions, evaluations):
        if not eval.correct and q.difficulty == "easy" and q.topic_id:
             weak_topics.append(q.topic_id)
             
    # Strong Areas: Topics of correct Hard questions
    strong_topics = []
    for q, eval in zip(questions, evaluations):
        if eval.correct and q.difficulty == "hard" and q.topic_id:
             strong_topics.append(q.topic_id)

    return {
        "status": "completed",
        "passed": passed,
        "score": round(final_score * 100, 2),
        "evaluations": [e.model_dump() for e in evaluations],
        "can_retry": (not passed) and can_retry,
        "current_module": updated_state.current_module_id,
        "analytics": {
            "easy_attempted": easy_attempted,
            "hard_attempted": hard_attempted,
            "weak_topics": list(set(weak_topics)),
            "strong_topics": list(set(strong_topics))
        }
    }


def generate_single_question(*, agent: Agent, module_id: str, difficulty: str) -> str:
    """
    Agent Task: Generate a single question.
    """
    # Fetch topics for targeted generation
    topics_data = CurriculumRepository.get_topics_for_module(module_id)
    # topics_data is list of dicts: {topic_id, topic_name, ...}
    
    topic_names = [t["topic_name"] for t in topics_data]
    topic_str = f"Focus on these topics: {', '.join(topic_names)}" if topic_names else "Focus on general module concepts."

    rubric = DIFFICULTY_RUBRIC.get(difficulty, DIFFICULTY_RUBRIC["medium"])
    
    # Updated Prompt with Reasoning Requirements & Chain of Thought
    task_desc = f"""
    Act as an expert exam setter. Your task is to generate one {difficulty} MULTIPLE CHOICE QUESTION for module {module_id}.
    
    CONTEXT:
    {topic_str}
    
    RUBRIC ({difficulty}):
    - Min Steps: {rubric['min_steps']}, Max Steps: {rubric['max_steps']}
    - Bloom's Levels: {rubric['cognitive_levels']}
    
    INSTRUCTIONS:
    1. **Think Step-by-Step (Internal Chain of Thought)**:
       - First, determine the concept you want to test.
       - Second, construct the problem statement. *DO NOT* include the answer or hints in the question text (e.g., do not say "Since X is true, what is...").
       - Third, solve it yourself to ensure it has exactly ONE correct answer.
       - Fourth, generate 3 plausible distractors (wrong options) that target common misconceptions.
    
    2. **Constraint Checklist**:
       - The question must be mathematically/logically precise.
       - Avoid ambiguity.
       - For "Hard" questions, combine 2 concepts or requires multi-step deduction, BUT ensure the logic is sound.
       - If asking about Tautologies/Contradictions, VERIFY the truth table mentally before generating.
    
    OUTPUT FORMAT:
    Provide STRICT VALID JSON ONLY. NO MARKDOWN.
    {{
        "question_text": "The concise problem statement",
        "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
        "correct_answer": "B) ...",
        "difficulty_reasoning": {{
            "cognitive_level": "{rubric['cognitive_levels'][0]}", 
            "steps_required": {rubric['min_steps']},
            "uses_formula": true,
            "requires_prior_concept_linking": false,
            "justification": "Why this matches the difficulty."
        }}
    }}
    """

    task = Task(
        description=task_desc,
        agent=agent,
        expected_output="JSON object with question_text, options, correct_answer, difficulty_reasoning"
    )

    # RETRY LOGIC (1 Retry)
    max_retries = 1
    attempt = 0
    final_data = None
    verification_status = "unverified"
    violations = []
    
    while attempt <= max_retries:
        result = task.execute_sync()
        result = str(result)
        
        try:
            import re
            cleaned_result = re.sub(r"```json|```", "", result).strip()
            data = json.loads(cleaned_result)
            
            # VALIDATE
            passed, violations = validate_difficulty(data, difficulty)
            if passed:
                final_data = data
                verification_status = "verified"
                break # Success
            else:
                print(f"WARN: Validation Failed (Attempt {attempt+1}): {violations}")
                attempt += 1
                if attempt <= max_retries:
                    # Optional: We could update prompt here, but for now simple retry
                    pass
                else:
                    # Final Fail: Accept but mark unverified
                    final_data = data
                    verification_status = "unverified"
        
        except Exception as e:
            print(f"ERROR: Parse failed (Attempt {attempt+1}): {e}")
            attempt += 1
            if attempt > max_retries: 
                 # Emergency Fallback
                 return {
                    "question_id": "error",
                     "question_text": "Error generating question.",
                     "options": [],
                     "difficulty": difficulty
                 }

    # Extract Fields
    question_text = final_data.get("question_text", "Error")
    options = final_data.get("options", [])
    correct_answer = final_data.get("correct_answer")
    reasoning = final_data.get("difficulty_reasoning", {})

    # AUDIT LOGGING
    audit_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "module_id": module_id,
        "requested_difficulty": difficulty,
        "ai_claimed_difficulty": difficulty, # Assuming AI tried
        "validation_result": "PASSED" if verification_status == "verified" else "FAILED",
        "violations": violations,
        "reasoning": reasoning
    }
    audit_logger.info(json.dumps(audit_entry))

    # SAVE to DB
    import uuid
    question_id = str(uuid.uuid4())
    topic_id = topics_data[0]["topic_id"] if topics_data else None
    
    # DYNAMIC SUBJECT ID FETCH
    # We need the subject_id for the module to save correctly. 
    # Use the Repo to get it.
    module_data = CurriculumRepository.get_module(module_id)
    subject_id = module_data["subject_id"] if module_data else "unknown_subject"
    
    AssessmentRepository.save_generated_question(
        question_id=question_id,
        subject_id=subject_id, # DYNAMICALLY SET
        module_id=module_id,
        topic_id=topic_id,
        difficulty=difficulty,
        question_text=str(question_text),
        correct_answer=str(correct_answer) if correct_answer else None,
        options=options
    )
    
    return {
        "question_id": question_id,
        "question_text": question_text,
        "options": options,
        "difficulty": difficulty,
        "topic_id": topic_id,
        "verification_status": verification_status
    }


def evaluate_single_answer(*, agent: Agent, question_text: str, student_answer: str) -> str:
    """
    Agent Task: Evaluate a single answer.
    """
    task = Task(
        description=f"""
        Question: {question_text}
        Student Answer: {student_answer}
        
        Evaluate the answer. valid/invalid.
        Output a short feedback string (e.g. "Correct! [Reason]" or "Incorrect. [Reason]").
        """,
        agent=agent,
        expected_output="Evaluation feedback"
    )
    return task.execute_sync()
