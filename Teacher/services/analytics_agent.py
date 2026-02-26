from typing import Dict, Any
import json
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

class AnalyticsAgent:
    def __init__(self):
        # Use gpt-4o-mini for speed/cost, slightly higher temp for "natural" tone but strictly grounded
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

    async def generate_insights(self, analytics_data: Dict[str, Any]) -> str:
        """
        Generate teacher-facing narrative from structured analytics data.
        """
        if not analytics_data or not analytics_data.get("topics"):
            return "No significant weak areas detected at this time."

        # Serialize data for the prompt
        data_str = json.dumps(analytics_data, indent=2)

        system_prompt = """
        You are a Teacher Analytics Agent in a university academic system.

        Your task is to analyze student weak areas and generate a concise,
        actionable teaching insight for faculty.

        STRICT CONTEXT RULES:
        - Use ONLY the provided analytics data.
        - Do NOT invent student behavior, topics, or causes.
        - Do NOT give generic advice.
        - Be factual, structured, and teacher-oriented.

        INPUT YOU WILL RECEIVE:
        1. Subject-wise weak area data aggregated across students.
        2. Each weak area includes:
           - subject_name
           - unit_title
           - topic_name
           - number_of_students_affected (affected_students)
           - severity_breakdown (critical / moderate / mild)
           - number_of_students_affected (affected_students)
           - severity_breakdown (critical / moderate / mild)
           - priority_score (calculated urgency)
        3. "at_risk_cos": List of Course Outcomes at risk, including:
           - co_code
           - description
           - affected_topics (count)
           - students_impacted (max count)

        YOUR RESPONSIBILITIES:
        1. Segregate insights STRICTLY by SUBJECT.
        2. Within each subject:
           - Identify High-Risk Topics (many critical students)
           - Identify Moderate Concern Topics
           - Identify Isolated / Monitor-only Topics
        3. Rank topics by teaching priority (critical > moderate > mild).
        4. Provide short, instructional recommendations focused on:
           - what to re-explain
           - what to reinforce
           - what to reinforce
           - what can be monitored
           - how to address the specific At-Risk COs

        OUTPUT FORMAT (MANDATORY):

        Subject: <Subject Name>

        High-Risk Topics (Immediate Attention):
        - <Topic Name> (<Unit Name>): 
          <clear reason based on severity distribution, e.g., '12 students show critical difficulty in this topic.' - ALWAYS use specific student counts, NOT percentages.>

        Low Priority / Monitor Only:
        - <Topic Name>: <brief observation>

        Outcome Alignment Risks (At-Risk COs):
        - <CO Code>: <Description>
          Impact: Affected by <Count> topics (e.g. Recursion, Trees). <Count> students failing this outcome.

        Teaching Recommendation:
        - <1–2 concise, actionable steps>

        STYLE CONSTRAINTS:
        - Professional academic tone
        - No emojis
        - No student blaming
        - No speculation beyond data
        - Prefer clarity over verbosity
        """

        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"ANALYTICS DATA:\n{data_str}")
            ])
            return response.content
        except Exception as e:
            return f"Error generating insights: {e}"

analytics_agent = AnalyticsAgent()
