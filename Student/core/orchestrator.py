from typing import Literal, List, Dict, Any

from core.state_manager import StateManager
from agents.student_learning_agent import (
    create_student_learning_agent,
    handle_learning_request,
)
from agents.assessment_agent import (
    create_assessment_agent,
    conduct_assessment,
)
from agents.analytics_agent import (
    create_analytics_agent,
    generate_student_analytics,
)


RequestType = Literal["LEARN", "ASSESS", "ANALYTICS"]


from core.logger import get_logger

logger = get_logger("Orchestrator")


class Orchestrator:
    """
    Central coordinator for all student interactions.
    """

    def __init__(self, *, llm, vector_store_client):
        self.state_manager = StateManager()


        # Agents (CrewAI)
        self.learning_agent = create_student_learning_agent(llm)
        self.assessment_agent = create_assessment_agent(llm)
        self.analytics_agent = create_analytics_agent(llm)

    # -------------------------------------------------
    # Entry Point
    # -------------------------------------------------

    def handle_request(
        self,
        *,
        request_type: RequestType,
        student_id: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:

        if request_type == "LEARN":
            logger.info(f"Dispatching to Learning Agent via {student_id}")
            return self._handle_learning(student_id, payload)

        if request_type == "ASSESS":
            logger.info(f"Dispatching to Assessment Agent via {student_id}")
            return self._handle_assessment(student_id, payload)

        if request_type == "ANALYTICS":
            logger.info(f"Dispatching to Analytics Agent via {student_id}")
            return self._handle_analytics(student_id, payload) # Pass payload

        if request_type == "GET_QUESTION":
             return self._handle_get_question(student_id, payload)

        if request_type == "EVALUATE_ANSWER":
             return self._handle_evaluate_answer(student_id, payload)

        logger.warning(f"Unsupported request type: {request_type}")
        return {
            "status": "error",
            "message": f"Unsupported request type: {request_type}",
        }

    # -------------------------------------------------
    # Handlers
    # -------------------------------------------------

    def _handle_learning(self, student_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        module_id = payload.get("module_id")
        query = payload.get("query")

        if not module_id or not query:
            return {
                "status": "error",
                "message": "module_id and query are required for learning.",
            }

        response = handle_learning_request(
            agent=self.learning_agent,
            student_id=student_id,
            module_id=module_id,
            user_query=query,
            state_manager=self.state_manager,
        )

        return {
            "status": "success",
            "response": response,
        }

    def _handle_assessment(self, student_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        module_id = payload.get("module_id")
        answers: List[str] = payload.get("answers")

        if not module_id or answers is None:
            return {
                "status": "error",
                "message": "module_id and answers are required for assessment.",
            }

        return conduct_assessment(
            agent=self.assessment_agent,
            student_id=student_id,
            module_id=module_id,
            student_answers=answers,
            state_manager=self.state_manager,
        )

    def _handle_analytics(self, student_id: str, payload: Dict[str, Any]) -> Dict[str, Any]: # Added payload
        subject_id = payload.get("subject_id") if payload else None
        
        analytics = generate_student_analytics(
            agent=self.analytics_agent,
            student_id=student_id,
            subject_id=subject_id # Pass it down
        )

        return {
            "status": "success",
            "data": analytics,
        }

    def _handle_get_question(self, student_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        from agents.assessment_agent import generate_single_question
        
        module_id = payload.get("module_id")
        difficulty = payload.get("difficulty", "medium")
        
        # Use Agent to generate
        # Returns dict {question_id, question_text, options, difficulty}
        q_data = generate_single_question(
            agent=self.assessment_agent,
            module_id=module_id,
            difficulty=difficulty
        )
        
        # Handle legacy string return if any (should stay dict)
        if isinstance(q_data, str):
             return {
                "status": "success",
                "question": q_data,
                "difficulty": difficulty
            }

        # Format legacy text for UI if needed? 
        # API expects "question" field. Currently logic used formatted text.
        # Let's recreate the formatted text for "question" field so UI doesn't break?
        # api/main.py puts q_data["question"] into Response.question
        # UI expects single string? 
        # Streamlit UI splits by lines? Let's check streamlit_app.py later.
        # For safety, let's concatenate options to text if "question" field implies full display text.
        
        full_text = q_data["question_text"]
        if q_data.get("options"):
             full_text += "\n\n" + "\n".join(q_data["options"])
             
        return {
            "status": "success",
            "question_id": q_data["question_id"],
            "question": full_text, 
            "difficulty": q_data["difficulty"],
            "topic_id": q_data.get("topic_id")
        }

    def _handle_evaluate_answer(self, student_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        from agents.assessment_agent import evaluate_single_answer
        from tools.interfaces.assessment_tool import AssessmentTool
        
        q_text = payload.get("question")
        ans = payload.get("answer")
        q_id = payload.get("question_id")
        
        if q_id:
             # Deterministic check
             eval_result = AssessmentTool.evaluate_by_id(q_id, ans)
             return {
                 "status": "success",
                 "feedback": eval_result["feedback"],
                 "is_correct": eval_result["is_correct"] # Pass explict bool
             }

        # Fallback to LLM
        feedback = evaluate_single_answer(
            agent=self.assessment_agent,
            question_text=q_text,
            student_answer=ans
        )
        
        return {
            "status": "success",
            "feedback": str(feedback)
        }
