from db.supabase_client import get_supabase
import json

class AnalyticsRepository:

    @staticmethod
    def update_student_analytics(
        student_id: str,
        current_module_id: str = None,
        average_score: float = 0.0,
        weak_questions_count: int = 0,
        strong_topics: list = None,
        hard_questions_attempted: int = 0,
        overall_progress: float = 0.0,
        weak_areas: dict = None
    ):
        supabase = get_supabase()
        
        data = {
            "student_id": student_id,
            "current_module_id": current_module_id,
            "average_score": average_score,
            "weak_questions_count": weak_questions_count,
            "strong_topics": json.dumps(strong_topics or []),
            "weak_areas": weak_areas or {},
            "hard_questions_attempted": hard_questions_attempted,
            "overall_progress": overall_progress,
            "last_updated": "now()"
        }
        
        try:
            supabase.table("student_analytics").upsert(data).execute()
        except Exception as e:
            # Fallback: If weak_areas column missing, remove it and try again
            if "weak_areas" in str(e) or "UndefinedColumn" in str(e):
                print("WARNING: weak_areas column missing. Saving without it.")
                del data["weak_areas"]
                supabase.table("student_analytics").upsert(data).execute()
            else:
                raise e

