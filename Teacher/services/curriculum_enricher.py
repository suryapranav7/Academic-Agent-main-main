import json
import os
from typing import Dict, Any, Optional

class CurriculumEnricher:
    _instance = None
    _lookup_map = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CurriculumEnricher, cls).__new__(cls)
            cls._instance._load_curriculum()
        return cls._instance

    def _load_curriculum(self):
        """Load and parse the college_curriculum.json into a lookup map"""
        try:
            # Locate the file relative to this script
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            json_path = os.path.join(base_dir, "curriculum", "college_curriculum.json")
            
            if not os.path.exists(json_path):
                print(f"[WARN] Curriculum file not found at: {json_path}")
                return

            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Build Lookup Map
            # Key: topic_id (e.g., "DS-U1-T1") -> Value: { subject, unit, topic }
            for subject in data.get("subjects", []):
                subj_name = subject.get("subject")
                for unit in subject.get("units", []):
                    unit_title = unit.get("unit_title")
                    for topic in unit.get("topics", []):
                        t_id = topic.get("topic_id")
                        t_name = topic.get("topic_name")
                        
                        if t_id:
                            self._lookup_map[t_id] = {
                                "subject": subj_name,
                                "unit": unit_title,
                                "topic": t_name
                            }
            
            print(f"[INFO] Curriculum Enricher loaded {len(self._lookup_map)} topics.")

        except Exception as e:
            print(f"[ERROR] Failed to load curriculum for enrichment: {e}")

    def get_topic_details(self, topic_id: str) -> Optional[Dict[str, str]]:
        """
        Get details for a topic ID.
        Returns: { "subject": "...", "unit": "...", "topic": "..." } or None
        """
        # 1. Direct Match (ID)
        if topic_id in self._lookup_map:
            return self._lookup_map[topic_id]
            
        return None

    def get_subject_for_topic(self, topic_name: str) -> Optional[str]:
        """
        Resolve Subject for a given Topic Name.
        """
        # Lazy search (can optimize with map if needed)
        for t_id, details in self._lookup_map.items():
            if details['topic'].lower() == topic_name.lower():
                return details['subject']
        return None

    def get_details_by_topic_name(self, topic_name: str) -> Optional[Dict[str, str]]:
        """
        Reverse lookup details using Topic Name (Fuzzy/Exact).
        """
        t_lower = topic_name.lower().strip()
        for t_id, details in self._lookup_map.items():
            if details['topic'].lower().strip() == t_lower:
                return details
        return None

    def get_topics_for_unit(self, unit_name: str) -> list[str]:
        """
        Get all topics belonging to a specific unit (by title).
        Useful for enriching module context.
        """
        unit_lower = unit_name.lower().strip()
        topics = []
        for t_id, details in self._lookup_map.items():
            if details['unit'].lower().strip() == unit_lower:
                topics.append(details['topic'])
        return topics

enricher = CurriculumEnricher()
