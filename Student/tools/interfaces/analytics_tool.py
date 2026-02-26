from schemas.analytics import StudentAnalytics
from tools.analytics_generator import generate_analytics


class AnalyticsTool:
    """
    Single interface for analytics generation.
    """

    @staticmethod
    def generate(student_id: str, subject_id: str = None) -> StudentAnalytics:
        data = generate_analytics(student_id, subject_id=subject_id)
        return StudentAnalytics.model_validate(data)
