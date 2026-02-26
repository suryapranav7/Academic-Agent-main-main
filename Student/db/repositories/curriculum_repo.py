from db.supabase_client import get_supabase

class CurriculumRepository:

    @staticmethod
    def get_subjects_by_grade(grade: str):
        supabase = get_supabase()
        response = supabase.table("subjects")\
            .select("subject_id, subject_name, grade, board")\
            .eq("grade", grade)\
            .execute()
        return response.data

    @staticmethod
    def get_modules_for_subject(subject_id: str):
        supabase = get_supabase()
        response = supabase.table("modules")\
            .select("module_id, module_name, module_order, description")\
            .eq("subject_id", subject_id)\
            .order("module_order")\
            .execute()
        return response.data

    @staticmethod
    def get_topics_for_module(module_id: str):
        """
        Fetches specific topics for a module.
        """
        supabase = get_supabase()
        response = supabase.table("module_topics")\
            .select("topic_id, topic_name, topic_order, content")\
            .eq("module_id", module_id)\
            .order("topic_order")\
            .execute()
        return response.data
        
    @staticmethod
    def get_topic(topic_id: str):
        supabase = get_supabase()
        response = supabase.table("module_topics")\
            .select("*")\
            .eq("topic_id", topic_id)\
            .execute()
        return response.data[0] if response.data else None

    @staticmethod
    def get_module(module_id: str):
        """
        Fetches specific module details by ID.
        """
        supabase = get_supabase()
        response = supabase.table("modules")\
            .select("module_id, module_name, description, subject_id")\
            .eq("module_id", module_id)\
            .execute()
        return response.data[0] if response.data else None

