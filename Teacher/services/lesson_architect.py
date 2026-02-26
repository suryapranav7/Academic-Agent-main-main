from typing import Dict, List, Any
import json
import difflib
import asyncio
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from .preference_parser import preference_parser
from .retrieval_engine import RetrievalEngine

class LessonArchitect:
    def __init__(self):
        # Using gpt-4o-mini for efficient planning
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        self.retriever = RetrievalEngine()

    def _resolve_intent_with_llm(self, preference: str, valid_topics: List[str], subject_context: str = "Computer Science") -> Dict[str, Any]:
        """
        HYBRID INTENT RESOLVER (With Guardrails):
        1. Core Validation: strictly checks against valid_topics.
        2. Extension Admission: allows NEW topics ONLY if explicitly named and relevant.
        3. Relevance Guardrail: blocks unrelated topics (e.g. 'Baking').
        """
        if not preference or not preference.strip():
            return {"ordering": [], "emphasis": [], "difficulty": "standard", "topic_metadata": {}}
            
        # REFACTORED STRICT PROMPT (Determinism Fix)
        system_prompt = f"""
        ROLE:
        You are a Curriculum Intent Classifier for an Engineering (B.Tech) Computer Science course.

        YOU ARE NOT A TEACHER.
        YOU ARE NOT A CONTENT GENERATOR.

        ABSOLUTE RULE:
        - You do NOT decide structure.
        - You ONLY fill the structure provided.
        - Do NOT add, remove, merge, or rename sections.
        - Do NOT write free-flow essays.
        - Every section must be concise, explicit, and scannable.

        YOUR JOB IS ONLY TO:
        1. Classify teacher intent
        2. Select topics strictly from the valid list
        3. Admit new topics ONLY if explicitly named

        STRICT RULES:
        - Do NOT infer new topics implicitly
        - Do NOT rename topics
        - Do NOT explain anything
        - Do NOT add commentary

        VALID CORE TOPICS (Strict Authority):
        {json.dumps(valid_topics)}

        TEACHER PREFERENCE:
        "{preference}"

        OUTPUT FORMAT (VALID JSON ONLY):
        {{
            "strategy": "overview_first" | "standard" | "review",
            "core_topics": [],
            "extension_topics": [],
            "irrelevant_topics": [],
            "emphasis": [],
            "difficulty": "beginner" | "standard" | "advanced"
        }}
        """
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content="Resolve intent JSON.")
            ])
            cleaned = response.content.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)
            
            # 1. CORE VALIDATION
            final_ordering = []
            topic_metadata = {}
            
            for t in data.get("core_topics", []):
                # fuzzy match or strict? Let's do strict check against generic list to be safe
                # But typically LLM copies well. Let's trust it but verify against list if possible
                # For now, we assume if it put it in "core", it found it.
                if t in valid_topics:
                    final_ordering.append(t)
                    topic_metadata[t] = "core"
            
            # 2. EXTENSION ADMISSION (The Guardrail)
            for t in data.get("extension_topics", []):
                # Double check: Is it already in core?
                if t in valid_topics:
                    if t not in final_ordering:
                        final_ordering.append(t)
                        topic_metadata[t] = "core"
                else:
                    # It is an extension (or a typo).
                    # Check for Fuzzy Match in Valid Topics (to recover warped titles)
                    import difflib
                    matches = difflib.get_close_matches(t, valid_topics, n=1, cutoff=0.7)
                    
                    if matches:
                        corrected = matches[0]
                        print(f"🔧 Fuzzy Recovery: '{t}' -> '{corrected}'")
                        if corrected not in final_ordering:
                            final_ordering.append(corrected)
                            topic_metadata[corrected] = "core"
                    else:
                        # It is a true new extension
                        final_ordering.append(t)
                        topic_metadata[t] = "extension"
                        print(f"🔓 Extension Admitted: '{t}'")

            # Log blocked topics
            if data.get("irrelevant_topics"):
                print(f"🛡️ Guardrail Blocked: {data['irrelevant_topics']}")
            
            return {
                "strategy": data.get("strategy", "standard"),
                "ordering": final_ordering,
                "deep_dive_topics": data.get("deep_dive_topics", final_ordering), # Default to all if not specified
                "emphasis": data.get("emphasis", []),
                "difficulty": data.get("difficulty", "standard"),
                "topic_metadata": topic_metadata
            }
            
        except Exception as e:
            print(f"❌ Intent Resolution Failed: {e}")
            return {"ordering": [], "emphasis": [], "difficulty": "standard", "topic_metadata": {}}


    # KNOWLEDGE GRAPH: Conceptual Prerequisites
    # This prevents pedagogical hallucinations (jumps in logic).
    PREREQUISITE_MAP = {
        "Kadane's Algorithm": ["Arrays", "Prefix Sum"],
        "Two Pointers": ["Arrays"],
        "Sliding Window": ["Arrays", "Iteration"],
        "Floyd's Cycle Detection": ["Linked List", "Pointers"],
        "Merge Sort": ["Recursion", "Arrays"],
        "Quick Sort": ["Recursion", "Arrays"],
        "Binary Search": ["Arrays", "Sorted Data"],
        "Dynamic Programming": ["Recursion", "Overlapping Subproblems"],
        "Graph Traversal (BFS/DFS)": ["Queue", "Stack", "Adjacency Matrix"],
        "Dijkstra's Algorithm": ["Graph", "Priority Queue"],
        "Center Expand Palindrome": ["Strings", "Two Pointers"],
        "KMP Algorithm": ["Strings", "Prefix Suffix"],
        "Tries": ["Tree Structure", "Strings"],
        "Heap Sort": ["Binary Heap", "Arrays"]
    }

    def _classify_topic_validity(self, requested_topic: str, context_concepts: List[str]) -> Dict[str, str]:
        """
        ADMISSION CONTROLLER:
        Decides if a requested topic is conceptually valid in the current lesson context.
        Returns: { status: CORE|EXTENSION|DEFERRED, reason: str }
        """
        topic = requested_topic.strip()
        
        # 1. CORE: If no prerequisites defined, assume it's a foundational or generic topic
        # Ideally, we should check against the full curriculum list here, but for now, 
        # if it's not in the 'Advanced Algorithms' list map, we verify loosely (Extension).
        prereqs = self.PREREQUISITE_MAP.get(topic)
        
        if not prereqs:
            # UNKNOWN TOPIC case -> Benefit of doubt (Extension)
            # We don't block it, but we flag it.
            return {"status": "EXTENSION", "reason": "Unverified Dependency - Admitted as Extension"}
            
        # 2. CHECK PREREQ SATISFACTION
        # Simple string matching for v1. Real system would use vectors/embeddings.
        # Context Concepts usually come from the main Topic title (e.g. "Linked Lists" -> "Linked List")
        missing = [p for p in prereqs if not any(c.lower() in p.lower() or p.lower() in c.lower() for c in context_concepts)]
        
        if not missing:
            return {"status": "EXTENSION", "reason": "Prerequisites satisfied"}
            
        # 3. DEFERRED: Prerequisites missing
        return {
            "status": "DEFERRED", 
            "reason": f"Requires concepts {missing}, which are not in current context {context_concepts}."
        }

    def _detect_teaching_angle(self, preference: str) -> str:
        """Determines the 'Teaching Angle' deterministically from keywords."""
        pref = preference.lower()
        if any(w in pref for w in ["algorithm", "complexity", "optimization", "big o"]):
            return "ALGORITHMIC"
        if any(w in pref for w in ["interview", "leetcode", "faang", "question"]):
            return "INTERVIEW" 
        if any(w in pref for w in ["concept", "theory", "definition", "fundamental"]):
            return "THEORETICAL"
        if any(w in pref for w in ["implementation", "code", "coding", "practice", "hands-on"]):
            return "IMPLEMENTATION"
        return "STANDARD"

    def _compile_strategy_graph(self, intent: Dict[str, Any], topics: List[str], preference: str = "") -> List[Dict[str, Any]]:
        """
        STRATEGY COMPILER (The Pedagogical Brain):
        Converts list of topics + strategy -> Execution Graph with weights.
        NOW SUPPORTS: Dynamic Phase Labeling based on Teaching Angle.
        """
        strategy = intent.get("strategy", "standard")
        deep_targets = intent.get("deep_dive_topics", [])
        angle = self._detect_teaching_angle(preference)
        
        # Helper to format title based on angle
        def format_phase_title(topic_name):
            t = topic_name.title()
            if angle == "ALGORITHMIC":
                return f"Algorithmic Aspects of {t}"
            if angle == "INTERVIEW":
                return f"Interview Patterns: {t}"
            if angle == "THEORETICAL":
                return f"Theory & Concepts: {t}"
            if angle == "IMPLEMENTATION":
                return f"Implementation Details: {t}"
            return t
        
        # If no deep targets specified but strategy is overview, assume all are deep targets
        if not deep_targets and strategy == "overview_first":
             deep_targets = topics
             
        graph = []
        
        if strategy == "overview_first":
            # 1. Synthetic Overview Phase (Contextual)
            display_topics = topics[:3]
            overview_topics_str = ", ".join(display_topics)
            if len(topics) > 3:
                overview_topics_str += "..."
                
            overview_title = f"Foundations: {overview_topics_str}"
            if angle != "STANDARD":
                 overview_title = f"{angle.title()} Overview: {overview_topics_str}"

            graph.append({
                "topic": overview_title,
                "phase_type": "overview",
                "topics_covered": topics, 
                "weight": 0.20,
                "allowed_scope": topics, # Contract: Overview must only cover these
                "teaching_angle": angle
            })
            
            # 2. Deep Dive Phases
            # Only for topics marked for Deep Dive
            effective_deep_topics = [t for t in topics if t in deep_targets]
            
            remaining_weight = 0.80
            weight_per_topic = remaining_weight / len(effective_deep_topics) if effective_deep_topics else 0
            
            for t in effective_deep_topics:
                graph.append({
                    "topic": format_phase_title(t),
                    "phase_type": "deep_dive",
                    "weight": weight_per_topic,
                    "teaching_angle": angle
                })
                
        else:
            # Standard Linear Strategy
            weight = 1.0 / len(topics) if topics else 1.0
            for t in topics:
                graph.append({
                    "topic": format_phase_title(t),
                    "phase_type": "standard",
                    "weight": weight,
                    "teaching_angle": angle
                })
                
        return graph

    def calculate_phased_structure(self, topic: str, intent: Dict[str, Any], teaching_level: str = "intermediate", phase_type: str = "standard", teaching_angle: str = "STANDARD") -> Dict[str, Any]:
        """
        Generates a Topic-Native Structure Phase with DISTINCT Pedagogical Models.
        NOW AWARE OF: Teaching Angle (Algorithmic, Interview, etc.)
        """
        level = teaching_level.lower()
        score = 3 # Default for intermediate
        
        # --- STRATEGY: OVERVIEW PHASE (Universal) ---
        if phase_type == "overview":
            return [
                {"type": "definitions", "title": "Concept Map & Basic Definitions", "count": 3, "priority": "high"},
                {"type": "comparison", "title": "Comparison Table", "count": 1, "priority": "critical"},
                {"type": "visuals", "title": "Visual Intuition", "count": 1, "priority": "high"}
            ]

        segments = []
        
        # --- MODEL 1: BEGINNER (Intuition First) ---
        if level == "beginner":
            # 1. Intuition (Replace formal Defs)
            segments.append({
                "type": "intuition", 
                "title": f"🧩 What is {topic}?", 
                "count": 1, 
                "priority": "high"
            })
            # 2. Analogy (The Core)
            segments.append({
                "type": "analogy", 
                "title": "🌍 Real-World Analogy", 
                "count": 1, 
                "priority": "critical"
            })
            # 3. Simple Visual
            segments.append({
                "type": "visuals", 
                "title": "👀 Visual Example", 
                "count": 1, 
                "priority": "medium"
            })
            # 4. Think About It (Replace formal Questions)
            segments.append({
                "type": "simple_question", 
                "title": "🤔 Think About It", 
                "count": 2, 
                "priority": "medium"
            })
            return segments

        # --- MODEL 2: ADVANCED (Architectural) ---
        elif level == "advanced":
            # 1. Deep Concepts
            segments.append({
                "type": "deep_concepts", 
                "title": f"Deep Concepts: {topic}", 
                "count": 2, 
                "priority": "high"
            })
            # 2. Design Insight (Trade-offs) - NEW text block
            segments.append({
                "type": "design_insight", 
                "title": "🔍 Design Insight (Trade-offs)", 
                "count": 1, 
                "priority": "critical"
            })
            # 3. Edge Cases
            segments.append({
                "type": "edge_cases", 
                "title": "⚠️ Edge Cases & Optimizations", 
                "count": 2, 
                "priority": "high"
            })
            # 4. Decision Scenario
            segments.append({
                "type": "decision_question", 
                "title": "🧠 Architect's Decision", 
                "count": 1, 
                "priority": "critical"
            })
            return segments

        # --- MODEL 3: INTERMEDIATE (Standard B.Tech) ---
        else:
            # 1. Definitions
            segments.append({
                "type": "definitions",
                "title": f"Concepts: {topic}",
                "count": 2,
                "priority": "high"
            })
            # 2. Rules / Formulae
            if "rules" in intent.get("emphasis", []):
                segments.append({
                    "type": "rules",
                    "title": "Critical Rules & Constraints",
                    "count": 3, 
                    "priority": "critical"
                })
            # 3. Code Examples
            segments.append({
                "type": "examples",
                "title": f"Implementation: {topic}",
                "count": 3,
                "priority": "medium"
            })
            # 4. Practice
            segments.append({
                "type": "interactive_questions",
                "title": "Practice Problems",
                "count": 4,
                "priority": "medium"
            })
            
        # --- ANGLE INJECTION (The "Hardcoded Slot", Dynamic Content) ---
        if teaching_angle == "ALGORITHMIC":
            # Add strict Algorithms Segment
            segments.append({
                "type": "key_algorithms",
                "title": f"🔑 Key Algorithms: {topic}", 
                "count": 3, # Ask for 3 specific algorithms
                "priority": "critical"
            })
            
        elif teaching_angle == "INTERVIEW":
            segments.append({
                "type": "interview_pattern", 
                "title": f"💼 Interview Patterns: {topic}", 
                "count": 2, 
                "priority": "critical"
            })

        return segments

    def _flatten_phases(self, node: Dict[str, Any], depth_limit: int = 2, current_depth: int = 0) -> List[Dict[str, Any]]:
        """
        Recursively unpacks a KB Node into a flat list of granular teaching phases.
        Stops if:
        1. Node has no children (Leaf).
        2. Depth limit reached (to prevent over-fragmentation).
        """
        # Base case: Leaf or Depth Limit
        if "children" not in node or not node["children"] or current_depth >= depth_limit:
            # Return self as the phase
            return [node]
            
        # Recursive Step
        flat_list = []
        for child in node["children"]:
            # Recurse
            flat_list.extend(self._flatten_phases(child, depth_limit, current_depth + 1))
            
        return flat_list

    async def generate_lesson_plan_async(self, subject: str, grade: str, topic: str, 
                           teacher_preference: str, teaching_level: str = "intermediate",
                           valid_curriculum_topics: List[str] = [], module_id: str = None):
        """
        RAG-DRIVEN LESSON GENERATOR
        Source of Truth: Knowledge Base (retrieved via RetrievalEngine).
        Flow: Intent -> RAG Lookup -> Composition (LLM as Arranger)
        """
        start_time = asyncio.get_event_loop().time()
        
        # 0. STRICT MODULE CONTEXT (CO Resolution)
        module_cos = []
        if module_id:
            print(f"🔒 Module Context Lock: {module_id}")
            module_cos = self._fetch_module_cos(module_id)

        # 1. INTENT ROUTER (Teaching vs Structural)
        # We classify if the user wants a "Lesson Plan" (Teaching) or just a "List" (Structural).
        intent_type = await self._classify_intent_type(teacher_preference)
        print(f"🚦 Intent Router: {intent_type}")
        
        # --- PATH A: STRUCTURAL (List/Outline) ---
        if intent_type == "STRUCTURAL":
             # Use wider scope to find unit/topic
            kb_topics = self.retriever.get_all_titles()
            full_valid_scope = list(set(valid_curriculum_topics + kb_topics))
            
            # Resolve target (lightweight)
            intent = self._resolve_intent_with_llm(teacher_preference, full_valid_scope)
            resolved_topic = intent["ordering"][0] if intent["ordering"] else topic
            
            # RULE: Force Unit Anchor if "unit" is requested in Structural Mode
            if "unit" in teacher_preference.lower():
                 print("⚓ Anchor Rule: Forcing 'unit_1' (Root) for Structural View.")
                 resolved_topic = "unit_1"

            # Fetch Structure Only
            kb_result = self.retriever.fetch_topic_context(resolved_topic, mode="structural")
            
            if kb_result["found"]:
                # Use Recursive Flattening to show SUB-TOPICS (Depth 3)
                # This proves dynamic retrieval and exposes inner modules.
                phases = self._flatten_phases(kb_result["node"], depth_limit=3)
                
                structural_timeline = []
                for p in phases:
                    structural_timeline.append({
                        "title": p["title"],
                        "duration": "N/A",
                        "content": f"Topic: {p['title']} ({p.get('type', 'node')})"
                    })
                
                return {
                    "meta": {
                        "subject": subject,
                        "grade": grade,
                        "topic": resolved_topic,
                        "teaching_level": "Structural View",
                        "teaching_angle": "Outline",
                        "architect_logic": {"mode": "STRUCTURAL", "source": kb_result["source"]},
                        "estimated_time_breakdown": {}
                    },
                    "timeline": structural_timeline
                }
            else:
                # Fallback to empty if not found
                 return {
                    "meta": {"error": "Topic not found for structural view"},
                    "timeline": []
                }

        # --- PATH B: TEACHING (RAG Lesson Plan) ---
        
        # 1. EXPAND SCOPE with RAG Knowledge
        kb_topics = self.retriever.get_all_titles()
        full_valid_scope = list(set(valid_curriculum_topics + kb_topics))
        
        # 2. PARSE & RESOLVE INTENT (Hybrid)
        
        # RULE: Empty Preference = WHOLE UNIT Scope (Unit Root)
        # Prevents getting locked into the first section "Introduction" by default.
        if not teacher_preference or not teacher_preference.strip():
            print("⚓ Anchor Rule: Empty Preference detected -> Forcing 'unit_1' (Root) for Teaching View.")
            resolved_topic = "unit_1"
            intent = {
                "strategy": "standard",
                "ordering": ["unit_1"],
                "deep_dive_topics": [],
                "emphasis": [],
                "difficulty": "standard",
                "topic_metadata": {"unit_1": "core"}
            }
        else:
            intent = self._resolve_intent_with_llm(teacher_preference, full_valid_scope)
            # Default to provided topic if LLM fails
            resolved_topic = intent["ordering"][0] if intent["ordering"] else topic
        print(f"🧠 Resolved Hybrid Intent: {intent}")
        print(f"🎯 Targeted RAG Topic: {resolved_topic}")

        # 3. PARSE TIME CONSTRAINT (Simple Regex)
        import re
        time_budget = 60 # Default
        exclude_intro = False
        
        # Look for "X minutes/mins" pattern
        time_match = re.search(r'(\d+)\s*(?:minutes|mins|min)', teacher_preference.lower())
        if time_match:
            time_budget = int(time_match.group(1))
            print(f"⏳ Time Constraint Detected: {time_budget} mins")
            
        if time_budget < 30:
            exclude_intro = True

        # 2a. SCOPE SHRINKING (Retriever Override)
        # LLM might pick "Unit 1" (Broad), but Retriever finds "Linear Lists" (Specific).
        strict_scope_lock = False
        print(f"🔍 Validating Scope Specificity for: '{teacher_preference}'")
        
        # Check raw query against KB
        scope_check = self.retriever.fetch_topic_context(teacher_preference, mode="structural")
        
        if scope_check.get("found") and scope_check.get("title"):
            retrieved_title = scope_check.get("title")
            print(f"🔒 Scope Override Check: Retrieved '{retrieved_title}' vs Resolved '{resolved_topic}'")
             # Update Topic if they differ
            if retrieved_title != resolved_topic:
                 print(f"   -> Overriding '{resolved_topic}' with '{retrieved_title}'")
                 resolved_topic = retrieved_title
            
            # Lock on the strict match
            strict_scope_lock = True
            
        else:
            # Fallback: Validate LLM's resolved topic against KB
            print(f"🔍 Validating LLM Topic '{resolved_topic}' for Lock...")
            llm_check = self.retriever.fetch_topic_context(resolved_topic, mode="teaching")
            if llm_check.get("found"):
                 # DRILL DOWN LOGIC
                 # If locked node is "Unit 1", check if any child (e.g. "Linear Lists") is in the query
                 current_node = llm_check["node"]
                 
                 def find_deeper_match(node, query):
                     # Check direct children
                     best_child = None
                     best_score = 0.0
                     
                     if "children" in node:
                         for child in node["children"]:
                             c_title = child.get("title", "").lower()
                             # 1. Exact Substring Match (Robust to partials)
                             # "linear list" in "linear lists" -> False
                             # "linear list" in "linear list" -> True
                             # We need to check if QUERY contains TITLE (or almost title)
                             # But here query="focus on linear list", title="Linear Lists"
                             
                             # Normalize: Remove 's' at end? 
                             # Better: logic "if any word intersection is strong"?
                             
                             # Let's use difflib ratio for Title vs any N-gram in Query?
                             # Simple hack for Plural: Check both singular and plural forms
                             c_title_sing = c_title.rstrip('s')
                             
                             if (c_title in query.lower()) or (c_title_sing in query.lower()):
                                 # Found match
                                 best_child = child
                                 break
                                 
                     if best_child:
                         print(f"⬇️ Scope Drill-Down: Found '{best_child['title']}' in query. Going deeper.")
                         return find_deeper_match(best_child, query)
                     return node

                 final_node = find_deeper_match(current_node, teacher_preference)
                 
                 if final_node["title"] != resolved_topic:
                     print(f"🔒 Locking to DRILL-DOWN Topic: '{final_node['title']}'")
                     resolved_topic = final_node["title"]
                 else:
                     print(f"🔒 Locking to LLM-Selected Topic: '{resolved_topic}'")
                     
                 strict_scope_lock = True

        print(f"🧠 Resolved Hybrid Intent: {intent}")
        print(f"🎯 Targeted RAG Topic: {resolved_topic} (Strict Lock: {strict_scope_lock})")

        # 3. PARSE TIME CONSTRAINT (Simple Regex)
        import re
        time_budget = 60 # Default
        exclude_intro = False
        
        # Look for "X minutes/mins" pattern
        time_match = re.search(r'(\d+)\s*(?:minutes|mins|min)', teacher_preference.lower())
        if time_match:
            time_budget = int(time_match.group(1))
            print(f"⏳ Time Constraint Detected: {time_budget} mins")
            
        if time_budget < 30:
            exclude_intro = True

        # 4. DETECT ANGLE
        teaching_angle = self._detect_teaching_angle(teacher_preference)
        print(f"📐 Teaching Angle: {teaching_angle}")

        # 5. RAG LOOKUP (The Librarian + The Governor)
        # Handle MULTIPLE topics if the intent resolver returned a list (e.g. ['Stack', 'Queue'])
        # If ordering is empty, default to the requested topic.
        topics_to_process = intent.get("ordering") if intent.get("ordering") else [topic]
        
        all_phases_to_build = []
        all_ancestry_payloads = [] # We'll collect unique ancestries
        kb_source_name = "Unknown"
        
        print(f"🔄 Processing Topics: {topics_to_process}")

        processed_titles = set()
        
        for target_topic in topics_to_process:
            # DEDUPLICATION CHECK
            if target_topic in processed_titles:
                print(f"⏭️ Skipping '{target_topic}' (Already covered by a parent topic).")
                continue

            kb_result = self.retriever.fetch_topic_context(target_topic, mode="teaching", time_budget=time_budget)
            
            # STRICT SUBTREE LOCK: Purge Siblings if locked
            # ... (unchanged)
            if strict_scope_lock:
                 print(f"🛡️ STRICT LOCK ACTIVE for '{target_topic}': Purging siblings.")
                 kb_result["siblings"] = []

            if kb_result["found"]:
                print(f"📚 KB HIT: Found '{target_topic}' in path {kb_result['path']}")
                kb_source_name = kb_result.get("source", "Unknown")
                
                # Merge Ancestry (for context)
                all_ancestry_payloads.extend(kb_result.get("ancestry_payloads", []))
                
                # FLATTEN PHASES (Recursive Decomposition)
                # This breaks "Unit I" into "Introduction", "Arrays", "Stacks"...
                target_node = kb_result["node"]
                phases = self._flatten_phases(target_node)
                
                # Register all flattened titles to prevent re-processing duplicates
                for p in phases:
                    processed_titles.add(p["title"])
                
                all_phases_to_build.extend(phases)
            else:
                print(f"⚠️ KB MISS: '{target_topic}' not found. Using fallback.")
                # Fallback phase
                all_phases_to_build.append({"title": target_topic, "type": "fallback", "payload": {}})
                processed_titles.add(target_topic)

        # Deduplicate ancestry logic could go here if needed
        full_timeline = []
        meta_log = {
            "intent_type": intent_type,
            "intent": intent,
            "resolved_topics": topics_to_process,
            "teaching_angle": teaching_angle,
            "time_budget": time_budget,
            "source_material": kb_source_name,
            "phases": []
        }
        
        # Determine total items to process
        phases_to_build = all_phases_to_build
        
        print(f"🚀 Launching {len(phases_to_build)} RAG Composition tasks...")
        
        total_time_budget = 45
        
        # WEIGHTED DURATION LOGIC
        # Give more time to "Implementation" and "Structure" nodes, especially in Advanced mode.
        total_weight = 0
        phase_weights = []
        
        for phase in phases_to_build:
            p_type = phase.get("type", "concept").lower()
            w = 1  # default
            if p_type in ["implementation", "algorithm", "structure"]:
                w = 2 
                if teaching_level == "advanced": w = 3 # Heavy focus
            elif p_type in ["application"]:
                w = 1.5
            
            phase_weights.append(w)
            total_weight += w
            
        # Calculate time per phase based on weight
        # time_per_phase is now distinct per phase


        tasks = []
        
        # --- NEW: GENERATE PLAN OVERVIEW (Parallel Task) ---
        print("📝 Generating Plan Overview...")
        overview_task = self._generate_plan_overview_async(
            teaching_level, teacher_preference, [p['title'] for p in phases_to_build]
        )
        # We can await it now or later. Let's await later with gather if we want true parallel, 
        # but for simplicity and logic flow, let's await it or add to tasks?
        # Adding to tasks makes return type handling complex (str vs list).
        # Let's run it essentially in parallel by creating the coroutine but awaiting it with the rest?
        # Actually, let's just await it separately or use gather with mixed types.
        # Simplest: Await it now (it's fast).
        # Better: Add to gather list but wrapped.
        
        # Let's just await it now to ensure it's ready for prepend.
        plan_overview_text = await overview_task
        
        # Add to timeline as first item
        full_timeline.append({
            "title": "Teaching Plan Overview",
            "duration": "Brief",
            "content": plan_overview_text, # String content compatible with UI
            "type": "overview" 
        })
        
        for idx, child_node in enumerate(phases_to_build):
            # We build a specific Source Context for this phase
            # It includes: Global Ancestry (Context) + Specific Node Payload (Content)
            source_package = {
                "global_context": all_ancestry_payloads,
                "siblings_available": [], # Siblings deactivated for multi-topic aggregation
                "target_content": child_node.get("payload", {}),
                "target_metadata": child_node.get("metadata", {})
            }
            
            # Dynamic Title
            phase_title = child_node["title"]
            if teaching_angle == "ALGORITHMIC":
                phase_title = f"Algorithmic View: {phase_title}"
            elif teaching_angle == "INTERVIEW":
                phase_title = f"Interview Focus: {phase_title}"

            # Calculate Time
            weight_idx = phases_to_build.index(child_node)
            my_weight = phase_weights[weight_idx]
            my_duration = max(5, int((my_weight / total_weight) * total_time_budget))

            # REMOVED: Previous prompt injection hack for 'Plan Overview'
            
            tasks.append(self._generate_content_from_kb_node(
                phase_title,
                source_package, 
                my_duration, 
                teaching_level, 
                teaching_angle,
                teacher_preference, # Original preference
                strict_mode=strict_scope_lock
            ))
            
            meta_log["phases"].append({
                "topic": phase_title,
                "type": child_node.get("type", "concept"),
                "source": "Textbook KB"
            })

        print(f"🚀 Launching {len(tasks)} RAG Composition tasks...")
        results = await asyncio.gather(*tasks)
        
        for res in results:
            full_timeline.extend(res)
                
        # LOGIC FIX: Determine Source Material based on actual success
        if all_phases_to_build:
            meta_log["source_material"] = kb_source_name
        else:
            meta_log["source_material"] = "None (Topic not in KB)"

        # 3.5 STRICT CO SUMMARY (Append at End with Narrative)
        if module_cos:
            print("🧠 Synthesizing CO Alignment Narrative...")
            narrative = await self._synthesize_co_alignment(module_cos, full_timeline)
            
            summary_card = self._generate_co_summary_card(module_cos, narrative=narrative)
            if summary_card:
                full_timeline.append(summary_card)
                print(f"✅ Appended CO Summary Card: {len(module_cos)} outcomes + narrative.")

        # 4. FINAL ASSEMBLY
        plan = {
            "meta": {
                "subject": subject,
                "grade": grade,
                "topic": topic,
                "teaching_level": f"{teaching_level.title()}",
                "teaching_angle": teaching_angle,
                "architect_logic": meta_log,
                "why_this_structure": f"Derived from {meta_log['source_material']}"
            },
            "timeline": full_timeline
        }
        
        return plan

    async def _classify_intent_type(self, request: str) -> str:
        """
        INTENT ROUTER (Strict Classifier)
        Determines if the request is 'TEACHING' (generate plan) or 'STRUCTURAL' (list/read-only).
        """
        req_lower = request.lower()
        
        # 1. REGEX OVERRIDES (Fast Path)
        # If user explicitly asks for "teaching", "explain", "focus", or "plan" (as in lesson plan), it is TEACHING.
        if any(w in req_lower for w in ["teaching", "teach", "explain", "focus", "depth", "content", "lesson plan"]):
            print(f"🚦 Intent Router (Regex): Detected '{request[:20]}...' -> TEACHING")
            return "TEACHING"
            
        # If user explicitly asks for "list", "outline", "structure", "syllabus" WITHOUT "teaching" context
        if any(w in req_lower for w in ["list", "outline", "structure", "syllabus", "titles"]):
             print(f"🚦 Intent Router (Regex): Detected '{request[:20]}...' -> STRUCTURAL")
             return "STRUCTURAL"

        # 2. LLM FALLBACK
        # REFACTORED STRICT PROMPT (Hard Decision)
        system_prompt = """
        ROLE: Request Classifier

        TASK:
        Classify the request into EXACTLY ONE category.

        CATEGORIES:
        - STRUCTURAL -> list / outline / syllabus only (headers only, no descriptions)
        - TEACHING -> explain / teach / focus / follow order / lesson plan (full content)

        HARD RULES:
        - If the request mentions teaching, explaining, focus, depth, or class -> TEACHING
        - If ambiguous -> TEACHING
        - NEVER explain your choice

        OUTPUT:
        STRUCTURAL or TEACHING
        """
        
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Request: {request}")
            ])
            decision = response.content.strip().upper().replace(".", "")
            if decision not in ["STRUCTURAL", "TEACHING"]:
                return "TEACHING" # Fallback
            return decision
        except Exception:
            return decision
        except Exception:
            return "TEACHING"

    async def _exec_phase_a_skeleton_design(self, title, source_package, level, preference):
        """
        PHASE A: PEDAGOGICAL SKELETON DESIGN
        Decides WHAT to teach and HOW DEEP, without generating text.
        """
        # PREFERENCE SAFETY LAYER (Golden Rule: Preference is a Lens, not a Filter)
        sanitized_pref = preference
        if preference:
            # Soften exclusionary language
            sanitized_pref = preference.lower().replace("only", "focus mainly on").replace("just", "focus on").replace("exclude", "de-emphasize")
            # Add strict instruction
            sanitized_pref += " (NOTE: Do NOT remove other topics. Maintain full curriculum coverage. Use this ONLY for emphasis.)"

        system_prompt = f"""
        ROLE:
        You are an experienced Computer Science professor designing a teaching plan.

        YOU ARE NOT WRITING CONTENT.
        YOU ARE DESIGNING A PEDAGOGICAL PLAN.

        GOAL:
        Create a teaching skeleton that covers ALL concepts from the given KB context,
        while adjusting depth and emphasis based on Teaching Level and Teacher Preference.

        NON-NEGOTIABLE RULES:
        - DO NOT skip any KB concept coverage (Full Scope is MANDATORY)
        - DO NOT introduce concepts not present in KB
        - DO NOT write explanations or examples
        - ONLY decide structure and depth

        TEACHING LEVEL POLICY:
        Beginner:
        - Awareness-level coverage for all concepts
        - Simple explanations only
        - NO heavy code or complexity analysis
        
        Intermediate:
        - Standard B.Tech depth
        - Definitions + algorithms + examples
        
        Advanced:
        - Implementation, edge cases, trade-offs, applications
        - Engineering-oriented depth
        - Must include Complexity Analysis & Production Code logic

        TEACHER PREFERENCE (LENS Rule):
        "{sanitized_pref}"
        - INTERPRETATION: Use this to adjust DEPTH and EMPHASIS.
        - FORBIDDEN: Do NOT filter out or delete topics based on this.

        INPUT CONTEXT (KB NODE):
        Title: {title}
        Type: {source_package.get("type", "concept")}
        Payload: {json.dumps(source_package.get("target_content", {}), indent=2)}

        OUTPUT FORMAT (STRICT JSON):
        {{
            "concepts": [
                {{
                    "concept_name": "<main_concept_title>",
                    "teaching_depth": "light | standard | deep",
                    "mandatory_sections": [
                        "<section_title_1>",
                        "<section_title_2>"
                    ]
                }}
            ]
        }}
        """
        
        try:
            response = await self.llm.ainvoke([SystemMessage(content=system_prompt)])
            cleaned = response.content.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned)
        except Exception as e:
            print(f"Phase A Failed: {e}")
            # Fallback Skeleton
            return {
                "concepts": [{
                    "concept_name": title,
                    "teaching_depth": "standard",
                    "mandatory_sections": ["Definition", "Concept", "Example"]
                }]
            }

    async def _exec_phase_b_content_generation(self, skeleton_concept, source_package, voice):
        """
        PHASE B: CONTENT GENERATION
        Fills the approved skeleton with content.
        """
        system_prompt = f"""
        ROLE:
        You are teaching Computer Science students.

        TASK:
        Generate teaching content for the concept '{skeleton_concept['concept_name']}' 
        using the provided teaching skeleton.

        STRICT RULES:
        - Follow the given sections EXACTLY
        - Do NOT add or remove sections
        - Do NOT introduce new concepts
        - Depth must match teaching_depth: {skeleton_concept['teaching_depth']}
        - Use the KB as the source of truth

        DEPTH RULES:
        light:
        - Definitions, intuition, simple analogy
        standard:
        - Definitions, algorithms, examples, basic complexity
        deep:
        - Detailed algorithms, Implementation discussion, Edge cases, Trade-offs, Real-world applications

        SKELETON SECTIONS (MANDATORY):
        {json.dumps(skeleton_concept['mandatory_sections'], indent=2)}

        SOURCE MATERIAL (KB):
        {json.dumps(source_package.get("target_content", {}), indent=2)}

        {voice}

        OUTPUT FORMAT (STRICT JSON):
        {{
            "title": "{skeleton_concept['concept_name']}",
            "sections": [
                {{ "label": "<section_from_skeleton>", "content": "<academic_content>" }}
            ]
        }}
        """
        
        try:
            response = await self.llm.ainvoke([SystemMessage(content=system_prompt)])
            cleaned = response.content.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned)
        except Exception as e:
            print(f"Phase B Failed: {e}")
            return {"title": skeleton_concept['concept_name'], "sections": []}
            return {"title": skeleton_concept['concept_name'], "sections": []}

    async def _generate_structured_engagement(self, module_title: str, topic: str, teaching_level: str, content_json: Dict) -> List[Dict]:
        """
        Generates 2-3 structured engagement objects (Action Objects) for the given content.
        Follows strict Pedagogical Levels (Beginner/Intermediate/Advanced).
        """
        # Extract seeds from content to ground the engagement
        seeds = [s.get('content', '')[:200] for s in content_json.get('sections', [])]
        seeds_json = json.dumps(seeds)

        system_prompt = f"""
        You are assisting a university faculty member.
        
        Your task is to GENERATE CLASSROOM ENGAGEMENTS.
        You are NOT allowed to generate syllabus content definitions.

        CONTEXT
        -------
        Module: {module_title}
        Topic: {topic}
        Teaching Level: {teaching_level}

        ENGAGEMENT RULES
        ----------------
        - Engagements must be executable directly in class.
        - Each engagement MUST include:
          1. teacher_script (What teacher says)
          2. student_action (What students do)
          3. key_realization (The 'Aha' moment)
          4. quick_check (How to verify)
        - Language must be simple and teacher-friendly.
        - Do NOT introduce new topics.
        - Do NOT mention Course Outcomes.

        TEACHING LEVEL CONSTRAINTS
        --------------------------
        Beginner:
        - Use analogies, prediction, simple questions
        - No technical depth or proofs

        Intermediate:
        - Use comparison, reasoning, constraints, dry-runs
        - Exam-oriented thinking allowed (no memorization)

        Advanced:
        - Use real-world scenarios, design decisions, lab-style tasks
        - Focus on implementation and failure cases

        INPUT SEEDS (Content Context)
        ----------------------
        {seeds_json}

        OUTPUT FORMAT (STRICT JSON)
        ---------------------------
        Return ONLY valid JSON with this structure:
        {{
            "engagements": [
                {{
                    "engagement_type": "analogy|prediction|constraint|error_analysis|design_task|discussion",
                    "duration_minutes": 5,
                    "teacher_script": "...",
                    "student_action": "...",
                    "key_realization": "...",
                    "quick_check": "..."
                }}
            ]
        }}
        """

        try:
            # We explicitly ask for 2 engagements
            response = await self.llm.ainvoke([
                SystemMessage(content="You are an expert in Active Learning pedagogy."),
                HumanMessage(content=system_prompt)
            ])
            cleaned = response.content.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)
            return data.get("engagements", [])
        except Exception as e:
            print(f"⚠️ Engagement Generation Failed: {e}")
            # Fallback (Empty list is better than broken text)
            return []

    async def _generate_content_from_kb_node(self, title, source_package, duration, level, angle, preference, strict_mode=False, module_cos=[]):
        """
        TWO-PHASE GENERATION ORCHESTRATOR
        Phase A: Skeleton Design (Design Plan)
        Phase B: Content Construction (Fill Plan)
        """
        print(f"🎬 [Phase A] Designing Skeleton for: {title} ({level})")
        
        # 1. PHASE A: SKELETON DESIGN
        skeleton_plan = await self._exec_phase_a_skeleton_design(
            title, source_package, level, preference
        )
        
        final_timeline = []
        
        # 2. ITERATE & EXECUTE PHASE B
        for concept in skeleton_plan.get("concepts", []):
            print(f"  📝 [Phase B] Drafting content for: {concept['concept_name']} (Depth: {concept['teaching_depth']})")
            
            # --- NEW: Module-Level CO Context ---
            co_codes = [c['co_code'] for c in module_cos]
            co_desc_str = "; ".join([f"{c['co_code']}: {c['description'][:50]}..." for c in module_cos])
            
            # Voice Context + Broad CO Alignment
            voice = f"""
            Ensure tone is {angle.lower()} and {level.lower()} level.
            
            OUTCOME CONTEXT (MODULE LEVEL):
            This lesson contributes to: {co_codes}
            Intent: {co_desc_str}
            """

            # Generate Content
            content_json = await self._exec_phase_b_content_generation(
                concept, source_package, voice
            )
            
            # 3. CALCULATE REALISTIC TIMING
            t_depth = concept['teaching_depth']
            base_time = 3
            if t_depth == "standard": base_time = 5
            elif t_depth == "deep": base_time = 8
            
            n_sections = len(content_json.get("sections", []))
            calc_duration = max(3, base_time + (n_sections - 2)) 
            
            final_timeline.append({
                "title": content_json.get("title", concept["concept_name"]),
                "duration": calc_duration,
                "sections": content_json.get("sections", []),
                "sections": content_json.get("sections", []),
                "engagement": [] # Will fill next
            })

            # 4. GENERATE STRUCTURED ENGAGEMENT (Post-Process)
            # We do this separately to ensure strong adherence to the "Action Object" schema
            print(f"  💡 Designing Engagements for: {concept['concept_name']}")
            structured_eng = await self._generate_structured_engagement(
                module_title=title, 
                topic=concept['concept_name'], 
                teaching_level=level, 
                content_json=content_json
            )
            final_timeline[-1]["engagement"] = structured_eng
            
        # 3. Generate Outcome Achievement Summary (STRICT MODULE)
        summary_card = self._generate_co_summary_card(module_cos)
        if summary_card:
            final_timeline.append(summary_card)

        print(f"✅ [Phase B] Completed content for: {title}")
        return final_timeline

    async def _generate_plan_overview_async(self, teaching_level: str, teacher_preference: str, phase_titles: List[str]) -> str:
        """
        Generates a 4-6 sentence meta-overview of the entire lesson plan.
        """
        system_prompt = f"""
        You are generating a brief overview for a teacher.

        Context you know:
        - Teaching level: {teaching_level}
        - Teaching preference: {teacher_preference or "General"}
        - Topics covered in this plan:
          {json.dumps(phase_titles, indent=2)}

        Instructions:
        - Write a concise introduction (4–6 sentences).
        - Explain:
          1. What this teaching plan covers.
          2. How the flow progresses (from basics → advanced topics).
          3. What depth or focus is applied based on teaching level.
        - Do NOT explain individual topics.
        - Do NOT add new topics.
        - Do NOT include timings.
        - This is a meta overview, not lesson content.
        """
        
        try:
            response = await self.llm.ainvoke([SystemMessage(content=system_prompt)])
            return response.content.strip()
        except Exception as e:
            print(f"⚠️ Overview Generation Failed: {e}")
            return "Overview not available."

    def _get_short_desc(self, level: str) -> str:
        level = level.lower()
        if level == "beginner": return "Intuition First"
        if level == "advanced": return "Architectural Depth"
        return "Standard B.Tech"
        
    def _get_teaching_voice(self, level: str, angle: str = "STANDARD") -> str:
        """Returns the specific system instruction for the teaching voice (Depth Governor)."""
        level = level.lower()
        
        # MANDATORY VOICE CONTRACT
        header = """
        VOICE CONTRACT (MANDATORY):
        - Violation of these rules is considered failure
        - Do not soften tone
        - Do not add storytelling
        """
        
        # 1. DEPTH GOVERNOR
        depth_rule = ""
        if level == "advanced":
            depth_rule = """
            DEPTH: ADVANCED / EXPERT
            - CONTROLLED EXPANSION: You MUST elaborate on keys explicitly present in the source.
            - REQUIRED SECTION (Where Applicable): 'Complexity Analysis'.
              - IF the topic involves algorithms/operations: State Time (Big O) and Space complexity.
              - IF the topic is strictly conceptual (e.g. Definition): Skip complexity. Do NOT force it.
            - REQUIRED SECTION (Where Applicable): 'Memory & Pointers'. Discuss fragmentation/overhead where relevant.
            - CONSTRAINT: Do NOT invent new operations or data structures not in source. Deepen ONLY what is given.
            """
        elif level == "beginner":
            depth_rule = """
            DEPTH: BEGINNER / INTUITION
            - SIMPLIFICATION: Use real-world analogies (e.g. Stack = Cafeteria Trays).
            - CONSTRAINT: Avoid complex code or pointer logic. Focus on "What" and "Why", not "How".
            - TONE: Encouraging and simple.
            """
        else: # Intermediate
            depth_rule = """
            DEPTH: STANDARD B.TECH
            - BALANCE: Mix formal definition with clear explanation.
            - Focus on correctness and standard textbook flow.
            - No metaphors unless explicitly requested.
            """

        # 2. ANGLE OVERRIDES
        angle_rule = ""
        if angle == "ALGORITHMIC":
            angle_rule = """
            ANGLE: ALGORITHMIC MODE
            - SUPPRESS generic definitions (e.g. "What is an Array?"). Assume basic knowledge.
            - REQUIRE Time/Space Complexity analysis for every concept (Where Applicable).
            - MENTION named algorithms (e.g. KMP, Floyd) ONLY if relevant to the topic. Do not force them.
            """
        elif angle == "INTERVIEW":
            angle_rule = """
            ANGLE: INTERVIEW MODE
            - Focus on 'Pattern Recognition' (e.g. Sliding Window, Two Pointers).
            - Discuss common interview pitfalls and optimization tricks.
            """
        elif angle == "THEORETICAL":
            angle_rule = """
            ANGLE: THEORETICAL MODE
            - Focus on mathematical proofs and formal definitions.
            - Discuss abstract data types and invariants.
            """
        elif angle == "IMPLEMENTATION":
            angle_rule = """
            ANGLE: IMPLEMENTATION MODE
            - Provide production-ready code snippets.
            - Focus on memory management and practical details.
            """

        # 3. BASE VOICE (CONSTRAINTS)
        base_rule = ""
        if level == "beginner":
            base_rule = """
            TEACHING VOICE (BEGINNER):
            - Explain concepts using everyday analogies.
            - Avoid dense jargon unless clearly defined.
            - Focus on INTUITION over Formalism.
            """
        elif level == "advanced":
            base_rule = """
            TEACHING VOICE (ADVANCED / ARCHITECT):
            - Assume strong fundamentals.
            - Focus on SCALABILITY, MEMORY, and EDGE CASES.
            - Discuss Trade-offs (Space vs Time).
            - ALGORITHM RULE: You MUST cite specific, named algorithms relevant to the current topic.
            """
        else: # Intermediate
            base_rule = """
            TEACHING VOICE (INTERMEDIATE):
            - Standard Undergraduate B.Tech level.
            - Balanced usage of Theory and Code.
            - ALGORITHM RULE: If discussing algorithms, cite specific named algorithms RELEVANT to the topic.
            """
            
        return f"{header}\n{depth_rule}\n{angle_rule}\n{base_rule}"

    # --- ENGAGEMENT LAYER (Outcome Based - STRICT MODULE) ---

    def _fetch_module_cos(self, module_id: str) -> List[Dict]:
        """
        Fetch COs strictly mapped to the given Module ID.
        """
        if not module_id: return []
        
        try:
            if not hasattr(self, 'supabase'):
                from Student.db.supabase_client import get_supabase
                self.supabase = get_supabase()

            # 1. Get CO IDs
            map_res = self.supabase.table("module_co_mapping").select("co_id").eq("module_id", module_id).execute()
            co_ids = [m['co_id'] for m in map_res.data]
            print(f"🔍 [CO Debug] Module {module_id} -> CO IDs: {co_ids}")
            
            if not co_ids: 
                print(f"⚠️ [CO Debug] No COs mapped for {module_id}.")
                return []

            # 2. Get Details
            # intent_type column removed as per verification (schema mismatch)
            co_res = self.supabase.table("course_outcomes").select("co_code, description").in_("co_id", co_ids).execute()
            print(f"✅ [CO Debug] Fetched {len(co_res.data)} CO details.")
            return co_res.data or []
            
        except Exception as e:
            print(f"⚠️ Failed to fetch Module COs: {e}")
            return []

    async def _synthesize_co_alignment(self, module_cos: List[Dict], timeline: List[Dict]) -> str:
        """
        Uses LLM to explain HOW the generated lesson content achieves the COs.
        """
        try:
            # Prepare Context
            topics_covered = [t.get("title", t.get("section", "")) for t in timeline if t.get("phase_type") != "overview"]
            topics_str = ", ".join(topics_covered[:10]) # Limit to top 10 to save tokens
            
            cos_str = "\n".join([f"{c.get('co_code')}: {c.get('description')}" for c in module_cos])
            
            prompt = f"""
            You are an Academic Quality Assurance Expert.
            
            COURSE OUTCOMES:
            {cos_str}
            
            LESSON CONTENT COVERED:
            {topics_str}
            
            TASK:
            Write a concise 2-sentence explanation of how the lesson content directly facilitates the attainment of these outcomes.
            Focus on the connection between the *Activities/Topics* and the *Outcome Skills* (e.g. "By implementing X, students practice Y").
            Do not use bullet points. Write a smooth narrative.
            """
            
            # Using self.llm (LangChain ChatOpenAI)
            messages = [
                SystemMessage(content="You are an expert curriculum designer. Write a 2-sentence narrative connecting lesson activities to outcomes."),
                HumanMessage(content=prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            content = response.content
            
            return content.strip().replace('"', '')
            
        except Exception as e:
            print(f"⚠️ CO Synthesis Failed: {e}")
            return ""

    def _generate_co_summary_card(self, module_cos: List[Dict], narrative: str = "") -> Dict[str, Any]:
        """
        Generates a summary card based on strict Module COs.
        """
        if not module_cos:
            return None
            
        summary_items = []
        for co in module_cos:
            summary_items.append({
                "term": co.get('co_code', 'CO?'),
                "definition": co.get('description', '')
            })
        
        # Add narrative as the first item or a special field?
        # The UI expects 'content' list of dicts.
        # I can add a special "narrative" field to the card dict, which I updated UI to ignore/handle?
        # Step 6311 UI update:
        # if item.get("type") == "summary":
        #    content_items = item.get("content", [])
        #    for c in content_items: ...
        
        # So if I add "narrative" to the DICT, I need to update UI to display it.
        # OR I can add it as a content item with a special key? 
        # UI loop: `t = c.get("term", ""), d = c.get("definition", "")`.
        # If I add `{"term": "Strategy Link", "definition": narrative}`, it will render perfectly!
            
        if narrative:
            summary_items.append({
                "term": "Alignment Strategy",
                "definition": narrative
            })

        return {
            "title": "✅ Outcome Achievement Targets",
            "duration": "Report",
            "type": "summary",
            "content": summary_items
        }

# Singleton instance - MOVED TO api.py to prevent Event Loop capture issues
# lesson_architect = LessonArchitect()

