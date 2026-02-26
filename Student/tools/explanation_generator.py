from crewai.tools import tool

@tool("ExplanationGenerator")
def explanation_generator_tool(concept: str, audience_level: str = "beginner") -> str:
    """
    Generates a clear explanation for a given concept tailored to the audience level.
    useful for breaking down complex topics.
    """
    # In a real scenario, this might call an LLM directly or use a specific template.
    # For now, we return a prompt-ready instruction.
    return f"Please explain '{concept}' in simple terms suitable for a {audience_level}."
