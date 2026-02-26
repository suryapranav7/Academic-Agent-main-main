import json
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

class RetrievalEngine:
    def __init__(self, kb_path: str = None):
        if kb_path is None:
            # Resolve relative to this file: Teacher/services/retrieval_engine.py -> Teacher/data/kb_unit_1.json
            base_dir = Path(__file__).resolve().parent.parent
            kb_path = base_dir / "data" / "kb_unit_1.json"
        
        self.kb = self._load_kb(str(kb_path))

    def _infer_time_cost(self, node: Dict) -> int:
        """Estimates time in minutes based on node type and metadata."""
        node_type = node.get("type", "concept")
        meta = node.get("metadata", {})
        
        # Base costs
        if node_type in ["unit", "section"]:
            return 0 # Container cost is sum of children
        elif node_type in ["definition", "concept", "illustration"]:
            return 5
        elif node_type in ["specification", "structure"]:
            return 10
        elif node_type in ["implementation", "algorithm"]:
            return 15
        elif node_type in ["application", "variation"]:
            return 10
        return 5

    def _get_node_priority(self, node: Dict) -> int:
        """Returns priority (Higher is better)."""
        meta = node.get("metadata", {})
        weight = meta.get("exam_weight", "medium")
        n_type = node.get("type", "")
        
        # 1. Critical definitions/specs are top priority
        if n_type in ["definition", "specification"] or meta.get("critical_concept"):
            return 100
        
        # 2. High exam weight
        if weight == "high":
            return 80
            
        # 3. Core implementations
        if n_type == "implementation" and weight != "low":
            return 60
            
        # 4. Standard
        if weight == "medium":
            return 40
            
        # 5. Nice to have
        return 20

    def _prune_structure(self, node: Dict, budget: int) -> Dict:
        """Returns a copy of the node with children filtered to fit budget."""
        # Cost of this node logic (if it has content itself, rare for Unit/Section)
        # We assume primarily container logic for high level, content logic for leaf.
        
        if "children" not in node:
            return node
            
        # 1. Calculate costs for all children
        scored_children = []
        for child in node["children"]:
            cost = self._infer_time_cost(child)
            # Recurse if child is container? 
            # For simplicity, we prune at the immediate children level for the Lesson Plan "Phases".
            # Deep pruning can be added later.
            priority = self._get_node_priority(child)
            scored_children.append({
                "child": child,
                "cost": cost,
                "priority": priority
            })
            
        # 2. Sort by Priority (Desc) then Cost (Asc - cheap things first?)
        # Actually High Priority first.
        scored_children.sort(key=lambda x: x["priority"], reverse=True)
        
        selected_children = []
        # Reserve 5 mins for Intro/Outro overhead
        effective_budget = max(5, budget - 5)
        current_cost = 0
        
        for item in scored_children:
            if current_cost + item["cost"] <= effective_budget:
                selected_children.append(item["child"])
                current_cost += item["cost"]
            else:
                print(f"✂️ Pruning Child: {item['child'].get('title')} (Cost {item['cost']}, Budget Left {budget - current_cost})")
                continue
                
        # 3. Re-sort selected children to original order (Pedagogical Flow)
        # We need to maintain the KB's logical sequence (e.g. Def -> Impl -> Apps)
        # Assuming original list has IDs or index.
        # We can map back to original index.
        
        # Helper map
        original_order_map = {c["id"]: i for i, c in enumerate(node["children"])}
        selected_children.sort(key=lambda x: original_order_map.get(x["id"], 0))
        
        node_copy = node.copy()
        node_copy["children"] = selected_children
        node_copy["_estimated_time"] = current_cost
        return node_copy
        
    def _load_kb(self, path: str) -> Dict[str, Any]:
        """Loads and indexes the Knowledge Base."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️ KB File not found at {path}")
            return {}

    def fetch_topic_context(self, query: str, mode: str = "teaching", time_budget: int = 60) -> Dict[str, Any]:
        """
        Retrieves KB node.
        Mode 'teaching': Returns Payload + Ancestry (for Lesson Plan).
        Mode 'structural': Returns Hierarchy/Children (for List/Outline).
        Time Budget: If < 60 mins, prunes non-essential children.
        """
        query = query.lower().strip()
        
        # Helper to search and keep track of path
        def collect_matches(node: Dict, path_so_far: List[Dict], matches: List[Dict]):
            title = node.get("title", "").lower()
            aliases = [a.lower() for a in node.get("aliases", [])]
            node_id = str(node.get("id", "")).lower()
            
            # Match Condition 1: Query is substring of Title or Alias or ID
            # Match Condition 2: Title/Alias is substring of Query (if significant length)
            # Match Logic with Precision Scoring
            score = 0
            is_match = False
            
            if query == title or query in aliases or query == node_id:
                is_match = True
                score = 1000  # Exact match is king
                
            elif query in title:
                is_match = True
                # Query "Stack" in "Stack ADT".
                # Prefer tighter matches. "Stack" (5) in "Stack ADT" (9) diff=4. 
                # "Stack" (5) in "Introduction to Stack" (21) diff=16.
                # Higher score for small diff.
                score = 100 - (len(title) - len(query))
                
            elif title in query and len(title) > 3:
                is_match = True
                # Title "Stack" in Query "Teach me Stack".
                # Prefer longer (more specific) titles.
                # "Stack Implementation" (20) > "Stack" (5).
                score = len(title)
                
            if is_match:
                matches.append({
                    "node": node,
                    "ancestry": path_so_far,
                    "score": score
                })
            
            # Recurse
            if "children" in node:
                for child in node["children"]:
                    collect_matches(child, path_so_far + [node], matches)

        # Execute Search
        all_matches = []
        collect_matches(self.kb, [], all_matches)
        
        if all_matches:
            # Sort by score (descending)
            all_matches.sort(key=lambda x: x["score"], reverse=True)
            match = all_matches[0]
            
            node = match["node"]
            ancestry = match["ancestry"]
            path_names = [a.get("title") for a in ancestry] + [node.get("title")]
            
            # STRUCTURAL MODE: Simple Hierarchy Return
            if mode == "structural":
                children_list = [c.get("title") for c in node.get("children", [])]
                return {
                    "found": True,
                    "type": "structural_list",
                    "title": node.get("title"),
                    "node": node, # ADDED: Required for recursive flattening in LessonArchitect
                    "children": children_list,
                    "path": path_names,
                    "source": self.kb.get("source", "Unknown")
                }

            # TEACHING MODE (Default): Rich Payload + TIME GOVERNOR
            
            # Apply Limit (The Governor)
            if time_budget < 60:
                 # Prune children based on priority/cost
                 node = self._prune_structure(node, time_budget)

            siblings = []
            if ancestry:
                parent = ancestry[-1]
                siblings = [child.get("title") for child in parent.get("children", []) if child.get("id") != node.get("id")]
            
            return {
                "found": True,
                "node": node,
                "ancestry_payloads": [a.get("payload", {}) for a in ancestry],
                "path": path_names,
                "siblings": siblings,
                "source": self.kb.get("source", "Unknown")
            }
            
        return {"found": False, "node": None, "path": [], "reason": "Topic not found in Unit I KB"}

    def get_all_titles(self) -> List[str]:
        """Flatten KB to list of all titles for Intent Resolution scope."""
        titles = []
        def _recurse(node):
            if "title" in node:
                titles.append(node["title"])
            for child in node.get("children", []):
                _recurse(child)
        
        _recurse(self.kb)
        return titles

    def get_full_curriculum_structure(self) -> Dict[str, Any]:
        """Returns the skeleton (titles only) of the KB."""
        def extract_titles(node):
            return {
                "title": node.get("title"),
                "id": node.get("id"),
                "children": [extract_titles(c) for c in node.get("children", [])]
            }
        return extract_titles(self.kb)
