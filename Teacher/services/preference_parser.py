from typing import Dict, List, Any
import re

class PreferenceParser:
    """
    Deterministically parses Teacher Preference strings into an Actionable Intent DSL.
    Philosophy: Treats input as a set of instructional constraints, not just context.
    """

    # --- KEYWORD DICTIONARIES ---
    
    # 1. Ordering Keywords (Splitters)
    ORDER_TOKENS = ["then", "followed by", "after that", "next", "and also"]
    
    # 2. Emphasis Keywords
    EMPHASIS_TOKENS = {
        "rules": ["rule", "principle", "law", "guideline"],
        "definitions": ["define", "definition", "meaning", "what is"],
        "examples": ["example", "demo", "sample", "illustration", "case study"],
        "comparison": ["compare", "difference", "vs", "versus"],
        "deep": ["deep", "advanced", "detailed", "comprehensive", "core"],
    }
    
    # 3. Structure Keywords
    STRUCTURE_TOKENS = {
        "repeat": ["repeat", "same structure", "similarly", "same for"],
        "separate": ["separately", "individually"],
    }
    
    # 4. Difficulty Keywords
    DIFFICULTY_TOKENS = {
        "btech": ["b.tech", "btech", "engineering", "university"],
        "school": ["school", "basic", "fundamental", "beginner"],
    }

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Main entry point. Converts raw text -> Intent Dict.
        """
        if not text:
            return self._default_intent()

        text_lower = text.lower()
        
        # 1. PARSE ORDERING (Subject Splitting)
        # "Stacks then Queues" -> ["Stacks", "Queues"]
        # This is a basic split logic. A robust version would need Named Entity Recognition (NER), 
        # but for now we split by explicit temporal keywords if present.
        ordering = [text] # Default: Whole text is one subject context
        for token in self.ORDER_TOKENS:
            if token in text_lower:
                parts = text_lower.split(token)
                ordering = [p.strip() for p in parts if p.strip()]
                break # Split on the first strong temporal marker found
        
        # 2. PARSE EMPHASIS FLAGS
        emphasis = []
        for category, keywords in self.EMPHASIS_TOKENS.items():
            if any(k in text_lower for k in keywords):
                emphasis.append(category)

        # 3. PARSE STRUCTURE FLAGS
        structure_intent = "standard"
        if any(k in text_lower for k in self.STRUCTURE_TOKENS["repeat"]):
            structure_intent = "repeat_phases"
            
        # 4. PARSE DIFFICULTY
        difficulty = "standard"
        if any(k in text_lower for k in self.DIFFICULTY_TOKENS["btech"]):
            difficulty = "btech_advanced"
        elif any(k in text_lower for k in self.DIFFICULTY_TOKENS["school"]):
            difficulty = "basics"

        return {
            "ordering_split": ordering,  # List of textual segments representing potential topics
            "emphasis": emphasis,        # List of tags: ['rules', 'deep']
            "structure": structure_intent, # 'standard' or 'repeat_phases'
            "difficulty": difficulty     # 'btech_advanced', 'basics', 'standard'
        }

    def _default_intent(self):
        return {
            "ordering_split": [],
            "emphasis": [],
            "structure": "standard",
            "difficulty": "standard"
        }

# Singleton
preference_parser = PreferenceParser()
