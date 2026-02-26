import json
import os
import logging
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
import asyncio
import aiofiles

# --- CONFIGURATION ---
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# --- ASYNC LOGGING SETUP ---
class AsyncAuditLogger:
    def __init__(self, log_file):
        self.log_file = log_file
        self.queue = None # Lazy init
        self.worker_task = None
        
    async def start(self):
        if self.queue is None:
            self.queue = asyncio.Queue()
            
        if self.worker_task is None:
            self.worker_task = asyncio.create_task(self._process_logs())
            
    async def log(self, entry: Dict[str, Any]):
        await self.queue.put(entry)
        
    async def _process_logs(self):
        while True:
            entry = await self.queue.get()
            try:
                async with aiofiles.open(self.log_file, mode='a') as f:
                    await f.write(json.dumps(entry) + "\n")
            except Exception as e:
                print(f"❌ Log Write Error: {e}")
            finally:
                self.queue.task_done()

# Global Async Logger
audit_logger = AsyncAuditLogger(os.path.join(LOG_DIR, "difficulty_audit.jsonl"))


# --- RUBRIC & SCHEMA ---
DIFFICULTY_RUBRIC = {
    "easy": {
        "min_steps": 1,
        "max_steps": 2,
        "cognitive_levels": ["recall", "understanding", "definitions", "remembering", "define", "identify"],
        "description": "Direct recall of facts or simple definitions. No calculation or multi-step logic."
    },
    "medium": {
        "min_steps": 2, 
        "max_steps": 4, 
        "cognitive_levels": ["application", "calculations", "applying", "solve", "compute"],
        "description": "Applying a concept to a standard problem. Simple calculations."
    },
    "hard": {
        "min_steps": 3, 
        "max_steps": 8, 
        "cognitive_levels": ["analysis", "synthesis", "evaluation", "code_output", "analyzing", "evaluating", "create"],
        "description": "Multi-step reasoning, analyzing edge cases, predicting code output, or linking multiple concepts."
    }
}

class QuestionProof(BaseModel):
    cognitive_level: str
    steps_required: int
    used_formula: bool
    reasoning: str

class ValidatedQuestion(BaseModel):
    question: str
    options: List[str]
    correct_answer: str
    difficulty: str
    proof: QuestionProof

class QuestionEngine:
    def __init__(self, model_name="gpt-4o-mini", concurrency_limit=5):
        self.model_name = model_name
        # ⚠️ SAFETY: Limit concurrent LLM calls to prevent rate-limiting and OOM
        self.semaphore = asyncio.Semaphore(concurrency_limit) 

    async def ensure_logger(self):
        await audit_logger.start()

    def validate_question(self, q_data: Dict[str, Any], target_difficulty: str) -> tuple[bool, List[str]]:
        """
        Validates if the generated question meets the difficulty rubric.
        """
        rubric = DIFFICULTY_RUBRIC.get(target_difficulty, DIFFICULTY_RUBRIC["medium"])
        violations = []
        
        # 1. Check schema existence
        proof = q_data.get("proof", {})
        if not proof:
            return False, ["Missing 'proof' block"]
            
        steps = proof.get("steps_required", 0)
        cog = proof.get("cognitive_level", "").lower()
        
        # 2. Check Steps
        if steps < rubric["min_steps"]:
            violations.append(f"Steps {steps} < Min {rubric['min_steps']}")
        
        # Note: We enforce MIN steps strictly. Max steps is a soft guideline usually, but let's be strict for accuracy.
        # Actually for 'hard', more steps is fine. Checking Max might filter good hard questions. 
        # Let's check max only for 'easy' to prevent accidental hard questions.
        if target_difficulty == "easy" and steps > rubric["max_steps"]:
             violations.append(f"Steps {steps} > Max {rubric['max_steps']} (Too hard for Easy)")

        # 3. Check Cognitive Level
        valid_cogs = [c.lower() for c in rubric["cognitive_levels"]]
        # tailored fuzzy match
        if not any(v in cog for v in valid_cogs):
             violations.append(f"Cognitive '{cog}' not in {valid_cogs}")

        return len(violations) == 0, violations

    async def generate_batch_questions_async(self, subject: str, grade: str, topic: str, count: int = 5, distinct_difficulties: bool = True) -> List[Dict[str, Any]]:
        """
        Generates a batch of validated questions (Async).
        NOW: Reused as the worker unit for parallel execution.
        """
        await self.ensure_logger()
        
        # Define Distribution
        if distinct_difficulties:
            # 3 Easy, 2 Hard pattern
            requests = ["easy"] * 3 + ["hard"] * 2
        else:
            requests = ["medium"] * count
            
        # We process in one Prompt for efficiency, but ask for structured list
        prompt = f"""
        You are an Expert Exam Setter for B.Tech {subject}.
        Topic: {topic}
        
        TASK: Generate {len(requests)} distinct MCQs following this difficulty distribution:
        {requests}
        
        RUBRIC (STRICT ADHERENCE):
        - EASY: Direct definition/recall. 1 step.
        - HARD: Analysis/Code Output. 3+ steps.
        
        OUTPUT FORMAT (JSON List):
        [
            {{
                "question": "text",
                "options": ["A. Option One", "B. Option Two", "C. Option Three", "D. Option Four"],
                "correct_answer": "A. Option One",
                "difficulty": "easy/hard",
                "proof": {{
                    "cognitive_level": "recall/analysis",
                    "steps_required": int,
                    "used_formula": bool,
                    "reasoning": "Explanation..."
                }}
            }}
        ]
        
        IMPORTANT: 
        1. Options MUST start with "A. ", "B. ", "C. ", "D. ".
        2. "correct_answer" MUST be one of the strings from the "options" list exactly.
        """
        
        try:
            # ASYNC INVOKE with LOCAL CLIENT for Parallel Connections
            llm = ChatOpenAI(model=self.model_name, temperature=0.3)
            response = await llm.ainvoke([SystemMessage(content=prompt)])
            raw_content = response.content.replace("```json", "").replace("```", "").strip()
            data = json.loads(raw_content)
            
            valid_questions = []
            
            for index, q in enumerate(data):
                target_diff = requests[index] if index < len(requests) else "medium"
                
                # Validation
                passed, violations = self.validate_question(q, target_diff)
                
                status = "PASSED" if passed else "FAILED"
                
                # Async Log
                await audit_logger.log({
                    "timestamp": "now",
                    "topic": topic,
                    "target_diff": target_diff,
                    "generated_diff": q.get("difficulty"),
                    "question_snippet": q.get("question")[:50],
                    "proof": q.get("proof"),
                    "status": status,
                    "violations": violations
                })
                
                q["validation_status"] = status
                q["validation_violations"] = violations
                valid_questions.append(q)
                
            return valid_questions

        except Exception as e:
            print(f"❌ Question Engine Error ({topic}): {e}")
            return []

    async def _generate_topic_safe(self, subject, grade, topic, count):
        """Helper to run one topic with semaphore protection"""
        async with self.semaphore:
            # We reuse the robust single-topic logic. 
            # This isolates context (Risk 3 Mitigation) and limits concurrency (Risk 1, 2 Mitigation).
            return await self.generate_batch_questions_async(subject, grade, topic, count, distinct_difficulties=True)

    async def generate_multi_topic_questions_async(self, subject: str, grade: str, topic_map: Dict[str, int]) -> Dict[str, List[Any]]:
        """
        Generates questions for MULTIPLE topics in PARALLEL (Scatter-Gather).
        """
        await self.ensure_logger()
        
        # 1. Create Tasks (Scatter)
        tasks = []
        ordered_topics = list(topic_map.keys())
        
        for topic in ordered_topics:
            count = topic_map[topic]
            tasks.append(self._generate_topic_safe(subject, grade, topic, count))
            
        # 2. Execute Parallel (Gather)
        # return_exceptions=True allows one failure without crashing all
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 3. Aggregate Results
        final_map = {}
        for i, topic in enumerate(ordered_topics):
            res = results_list[i]
            if isinstance(res, Exception):
                print(f"⚠️ Task Failed for {topic}: {res}")
                final_map[topic] = [] 
            else:
                final_map[topic] = res
                
        return final_map

# Singleton - MOVED TO api.py to prevent Event Loop capture issues
# question_engine = QuestionEngine()
