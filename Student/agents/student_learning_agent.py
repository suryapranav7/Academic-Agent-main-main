from crewai import Agent, Task

from core.state_manager import StateManager
from tools.interfaces.curriculum_tool import CurriculumTool


def create_student_learning_agent(llm):
    """
    Factory function to create the Student Learning Agent.
    """

    return Agent(
        role="Student Learning Agent",
        goal="Guide the student through the curriculum strictly based on provided content.",
        backstory=(
            "You are a disciplined tutor. "
            "You only use the given curriculum. "
            "If something is not in the curriculum, you clearly say so. "
            "You explain concepts step by step in simple language."
        ),
        verbose=True,
        allow_delegation=False,
        tools=[],          # NO direct tools — access via interfaces only
        llm=llm,           # injected from outside
    )


from core.logger import get_logger

logger = get_logger("LearningAgent")


def handle_learning_request(
    *,
    agent: Agent,
    student_id: str,
    module_id: str,
    user_query: str,
    state_manager: StateManager,
    course_id: str = None

) -> str:
    """
    Handles a single learning interaction for a student.
    """

    # 1 Permission check
    if not state_manager.can_learn(student_id, module_id):
        logger.warning(f"Access denied for {student_id} on {module_id}")
        return "You cannot access this module yet. Please complete the previous modules."

    # 1. Retrieve Context (RAG + Structure)
    from tools.curriculum_retriever import retrieve_curriculum
    from db.repositories.curriculum_repo import CurriculumRepository
    
    # A. Full Module Scope (Topic Names)
    all_topics_data = CurriculumRepository.get_topics_for_module(module_id)
    allowed_topics = [t["topic_name"] for t in all_topics_data]
    scope_str = ", ".join(allowed_topics)

    # B. RAG Content
    rag_context = ""
    curriculum_data = {}
    try:
        curriculum_data = retrieve_curriculum(course_id, query=user_query, student_id=student_id, module_id=module_id)
    except Exception as e:
        logger.error(f"Error retrieving curriculum: {e}")
    
    # 2. Get student state
    student_state = state_manager.load_state(student_id)
    
    # 3. Formulate Prompt
    prompt = f"""
    You are a Tutor for the module: {module_id}
    
    OFFICIAL SCOPE (Allowed Topics): 
    {scope_str}

    RETRIEVED CONTENT (Specific details):
    {curriculum_data}
    
    STUDENT QUESTION:
    {user_query}
    
    INSTRUCTIONS:
    1. STRICTLY LIMIT your answer to the 'Official Scope'. 
    2. If the user asks about a topic NOT in the list [ {scope_str} ], politely refuse: "That is outside the scope of this module."
    3. Use the 'Retrieved Content' for definitions and examples.
    4. If the content is missing but the topic IS in the Scope, you may explain generally.
    """

    logger.info("Executing Agent Task...")

    # 5 Let the agent respond (bounded)
    task = Task(
        description=prompt,
        agent=agent,
        expected_output="A helpful, curriculum-based response to the student's question."
    )
    result = task.execute_sync()
    
    response_text = result.raw if hasattr(result, "raw") else str(result)
    logger.info(f"Agent Response: {response_text[:100]}...")
    
    # Return raw text content
    return response_text
