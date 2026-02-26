
from crewai import Agent, Task

from tools.interfaces.analytics_tool import AnalyticsTool
from schemas.analytics import StudentAnalytics


def create_analytics_agent(llm):
    """
    CrewAI Analytics Agent.
    Responsible for summarizing and explaining analytics data.
    """

    return Agent(
        role="Analytics Agent",
        goal="Analyze student performance and present clear learning insights.",
        backstory=(
            "You are a precise analyst. "
            "You only report insights derived from data. "
            "You never speculate or invent reasons. "
            "You present results clearly and concisely."
        ),
        verbose=True,
        allow_delegation=False,
        tools=[],     # 🔒 No direct tools, interface only
        llm=llm,
    )


def generate_student_analytics(
    *,
    agent: Agent,
    student_id: str,
    subject_id: str = None # Added param
) -> dict:
    """
    Generates analytics for a given student.
    """

    # 1️⃣ Fetch analytics data (deterministic)
    analytics: StudentAnalytics = AnalyticsTool.generate(student_id, subject_id=subject_id)

    # 2️⃣ Structured explanation prompt (NO hallucination)
    prompt = f"""
You must explain the analytics below strictly based on the data.

Analytics data (JSON):
{analytics.model_dump_json(indent=2)}

Rules:
- Do NOT assume reasons beyond the data
- Do NOT invent causes
- Do NOT give advice unless data supports it
- If a metric is missing, say it is unavailable
- Analyze the 'module_breakdown' to give specific feedback per module.
"""

    task = Task(
        description=prompt,
        agent=agent,
        expected_output="Clear explanation of the analytics data."
    )
    result = task.execute_sync()
    explanation = result.raw if hasattr(result, "raw") else str(result)

    # 3️⃣ Final payload
    return {
        "analytics": analytics.model_dump(),
        "explanation": explanation
    }
