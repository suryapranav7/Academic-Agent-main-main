import os
from typing import Dict, List, Any
try:
    from Student.db.supabase_client import get_supabase
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))
    from Student.db.supabase_client import get_supabase

from .mapping_crew import MappingCrew
from .curriculum_enricher import CurriculumEnricher

class MappingService:
    def __init__(self):
        self.supabase = get_supabase()
        self.crew = MappingCrew()
        self.enricher = CurriculumEnricher()

    def generate_suggestions(self, subject_id: str) -> Dict[str, List[str]]:
        """
        Fetches modules and COs for a subject, then uses CrewAI to map them.
        Returns: { "module_id": ["co_id1", "co_id2"] }
        """
        print(f"🤖 Auto-Mapping Service started for {subject_id}...")

        # 1. Fetch Modules
        try:
            # MAP ID: The 'modules' table uses long IDs (e.g. 'btech_data_structures_y2')
            # while 'course_outcomes' and UI use short IDs (e.g. 'DS203').
            # We map them here for the Pilot.
            db_subject_id = subject_id
            if subject_id == "DS203":
                db_subject_id = "btech_data_structures_y2"
            elif subject_id == "DM201":
                db_subject_id = "btech_discrete_mathematics_y2"

            # We want module_id and module_name
            modules_res = self.supabase.table("modules")\
                .select("module_id, module_name")\
                .eq("subject_id", db_subject_id)\
                .execute()
            modules_data = modules_res.data or []
        except Exception as e:
            print(f"❌ Failed to fetch modules: {e}")
            return {}

        # 2. Fetch Course Outcomes
        try:
            cos_res = self.supabase.table("course_outcomes")\
                .select("co_id, co_code, description")\
                .eq("subject_id", subject_id)\
                .execute()
            cos_data = cos_res.data or []
        except Exception as e:
            print(f"❌ Failed to fetch COs: {e}")
            return {}

        if not modules_data or not cos_data:
            print(f"⚠️ Insufficient data: {len(modules_data)} modules, {len(cos_data)} COs.")
            return {}

        # 3. Pre-process Data for LLM (Reduce Token Count)
        llm_modules = []
        # 3. Pre-process Data for LLM (Reduce Token Count)
        llm_modules = []
        for m in modules_data:
            # ENRICHMENT: Fetch topics from Curriculum JSON
            topics = self.enricher.get_topics_for_unit(m["module_name"])
            
            if topics:
                summary = f"{m['module_name']}\nTopics: {', '.join(topics)}"
            else:
                summary = m["module_name"]
            
            llm_modules.append({
                "module_id": m["module_id"],
                "unit_title": m["module_name"],
                "content_summary": summary 
            })

        llm_cos = []
        for c in cos_data:
            llm_cos.append({
                "co_id": c["co_id"],
                "co_code": c["co_code"],
                "description": c["description"]
            })

        print(f"📤 Sending {len(llm_modules)} Modules and {len(llm_cos)} COs to CrewAI agent...")

        # 4. Invoke Crew
        try:
            result_map = self.crew.run(llm_modules, llm_cos)
            print(f"✅ Mapping complete. Generated {len(result_map)} mappings.")
            return result_map
        except Exception as e:
            print(f"❌ Crew Execution Failed: {e}")
            return {}

# Singleton instance
mapping_service = MappingService()
