import sys
import os

# Ensure we can import from local modules
sys.path.append(os.path.dirname(__file__))

from agents.assessment_agent import validate_difficulty

def test_validator():
    print("--- Testing Difficulty Validator ---")

    # CASE 1: Valid Easy
    print("\n1. Testing Valid Easy:")
    easy_data = {
        "difficulty_reasoning": {
            "cognitive_level": "recall",
            "steps_required": 1,
            "uses_formula": False,
            "requires_prior_concept_linking": False,
            "justification": "Simple recall."
        }
    }
    passed, violations = validate_difficulty(easy_data, "easy")
    print(f"Result: {passed}, Violations: {violations}")
    if not passed: print("❌ FAIL: Valid Easy was rejected.")
    else: print("✅ PASS")

    # CASE 2: Invalid Medium (Too few steps)
    print("\n2. Testing Invalid Medium (1 step):")
    medium_invalid = {
        "difficulty_reasoning": {
            "cognitive_level": "application",
            "steps_required": 1, # Should be 2
            "uses_formula": True,
            "requires_prior_concept_linking": False,
            "justification": "..."
        }
    }
    passed, violations = validate_difficulty(medium_invalid, "medium")
    print(f"Result: {passed}, Violations: {violations}")
    if passed: print("❌ FAIL: Invalid Medium was accepted.")
    elif "Too few steps" not in violations[0]: print("❌ FAIL: Wrong violation message.")
    else: print("✅ PASS")

    # CASE 3: Invalid Hard (Cognitive Mismatch)
    print("\n3. Testing Invalid Hard (Wrong Cognitive Level):")
    hard_invalid = {
         "difficulty_reasoning": {
            "cognitive_level": "recall", # Should be analysis/synthesis
            "steps_required": 3,
            "uses_formula": True,
            "requires_prior_concept_linking": True,
            "justification": "..."
        }
    }
    passed, violations = validate_difficulty(hard_invalid, "hard")
    print(f"Result: {passed}, Violations: {violations}")
    if passed: print("❌ FAIL: Invalid Hard was accepted.")
    elif "Cognitive level" not in violations[0]: print("❌ FAIL: Wrong violation message.")
    else: print("✅ PASS")
    
    # CASE 4: Missing Reasoning
    print("\n4. Testing Missing Reasoning:")
    missing = {}
    passed, violations = validate_difficulty(missing, "hard")
    print(f"Result: {passed}, Violations: {violations}")
    if passed: print("❌ FAIL: Missing Reasoning was accepted.")
    else: print("✅ PASS")

    print("\n--- Test Complete ---")

if __name__ == "__main__":
    test_validator()
