import sys
import os

# Ensure we can import from local modules
sys.path.append(os.path.dirname(__file__))

from tools.interfaces.assessment_tool import AssessmentTool
from schemas.assessment import Question

def test_evaluation():
    print("--- Testing Answer Evaluation ---")
    
    # Mock Question
    q = Question(
        question_id="test",
        question_text="What is 2+2?",
        difficulty="easy",
        expected_concepts=[],
        correct_answer="B) 4",
        options=["A) 3", "B) 4", "C) 5"]
    )

    # 1. Exact Match
    res = AssessmentTool.evaluate(q, "B) 4")
    print(f"1. Exact Match: {res.correct}")
    assert res.correct

    # 2. Key Only
    res = AssessmentTool.evaluate(q, "B")
    print(f"2. Key Only: {res.correct}")
    assert res.correct
    
    # 3. Lowercase Key
    res = AssessmentTool.evaluate(q, "b")
    print(f"3. Lowercase Key: {res.correct}")
    assert res.correct

    # 4. Text Only (Fuzzy Match logic)
    res = AssessmentTool.evaluate(q, "4")
    print(f"4. Text Only: {res.correct}")
    assert res.correct
    
    # 5. Bold Markdown
    res = AssessmentTool.evaluate(q, "**B**")
    print(f"5. Bold Markdown: {res.correct}")
    assert res.correct

    # 6. INCORRECT
    res = AssessmentTool.evaluate(q, "A")
    print(f"6. Incorrect Key: {res.correct}")
    assert not res.correct

    print("\n✅ All Tests Passed!")

if __name__ == "__main__":
    test_evaluation()
