import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from db.supabase_client import get_supabase

def seed_curriculum():
    supabase = get_supabase()
    print("🌱 Seeding IB Mathematics Grade 9 Curriculum to Supabase...")

    # -------------------------------------------------
    # SUBJECT
    # -------------------------------------------------
    subject_data = {
        "subject_id": "ib_math_gr9",
        "subject_name": "IB Mathematics",
        "grade": "9",
        "board": "IB"
    }
    supabase.table("subjects").upsert(subject_data).execute()

    # -------------------------------------------------
    # MODULES
    # -------------------------------------------------
    modules = [
        {"module_id": "mod_1_reasoning", "subject_id": "ib_math_gr9", "module_name": "Mathematical Reasoning", "module_order": 1, "description": "Foundations of logic and proof."},
        {"module_id": "mod_2_functions", "subject_id": "ib_math_gr9", "module_name": "Functions", "module_order": 2, "description": "Understanding relations and functions."},
        {"module_id": "mod_3_stats", "subject_id": "ib_math_gr9", "module_name": "Statistics and Probability", "module_order": 3, "description": "Data analysis and chance."},
        {"module_id": "mod_4_geometry", "subject_id": "ib_math_gr9", "module_name": "Geometry and Trigonometry", "module_order": 4, "description": "Shapes, sizes, and relative positions."},
        {"module_id": "mod_5_algebra", "subject_id": "ib_math_gr9", "module_name": "Number and Algebra", "module_order": 5, "description": "Number systems and algebraic structures."},
        {"module_id": "mod_final_exam", "subject_id": "ib_math_gr9", "module_name": "Final Exam", "module_order": 6, "description": "Comprehensive assessment of all topics."}
    ]
    supabase.table("modules").upsert(modules).execute()

    # -------------------------------------------------
    # MODULE TOPICS
    # -------------------------------------------------
    topics = [
        # Module 1
        {"topic_id": "topic_1_1", "module_id": "mod_1_reasoning", "topic_name": "Inductive and Deductive Reasoning", "topic_order": 1, "content": "Inductive reasoning involves drawing general conclusions from specific observations (bottom-up). Deductive reasoning starts with a general hypothesis or known fact and creates a specific conclusion (top-down)."},
        {"topic_id": "topic_1_2", "module_id": "mod_1_reasoning", "topic_name": "Proof Techniques", "topic_order": 2, "content": "Mathematical proof is a rigorous argument to demonstrate the truth of a statement. Methods include Direct Proof, Proof by Contradiction, and Proof by Induction."},
        {"topic_id": "topic_1_3", "module_id": "mod_1_reasoning", "topic_name": "Logic Puzzles & Statements", "topic_order": 3, "content": "A logical statement is a declarative sentence that is true or false. Truth tables track the validity of compound statements using connectives AND, OR, NOT, IMPLIES."},
        {"topic_id": "topic_1_4", "module_id": "mod_1_reasoning", "topic_name": "Problem Solving Strategies", "topic_order": 4, "content": "Key strategies include: Guess and Check, Working Backwards, Finding a Pattern, and Polya’s Four-Step Process (Understand, Plan, Execute, Review)."},

        # Module 2
        {"topic_id": "topic_2_1", "module_id": "mod_2_functions", "topic_name": "Domain and Range", "topic_order": 1, "content": "A function is a relation where each input (x) has exactly one output (y). The set of all inputs is the Domain, and the set of all outputs is the Range."},
        {"topic_id": "topic_2_2", "module_id": "mod_2_functions", "topic_name": "Linear Functions", "topic_order": 2, "content": "Linear functions form straight lines when graphed. Standard form: y = mx + c, where m is slope and c is y-intercept."},
        {"topic_id": "topic_2_3", "module_id": "mod_2_functions", "topic_name": "Quadratic Graphs", "topic_order": 3, "content": "Quadratic functions have the form f(x) = ax^2 + bx + c. Their graphs are parabolas. Key features include the vertex, axis of symmetry, and roots."},

        # Module 3
        {"topic_id": "topic_3_1", "module_id": "mod_3_stats", "topic_name": "Data Representation", "topic_order": 1, "content": "Data can be categorical or numerical. Representation methods include Bar Charts, Histograms, Pie Charts, and Box-and-Whisker Plots."},
        {"topic_id": "topic_3_2", "module_id": "mod_3_stats", "topic_name": "Mean Median Mode", "topic_order": 2, "content": "Mean is the average. Median is the middle value. Mode is the most frequent value. Each gives a different perspective on the 'center' of data."},

        # Module 4
        {"topic_id": "topic_4_1", "module_id": "mod_4_geometry", "topic_name": "Triangle Properties", "topic_order": 1, "content": "Polygons are classified by sides (Triangle 3, Quadrilateral 4, etc.). Regular polygons have equal sides and angles."},
        {"topic_id": "topic_4_2", "module_id": "mod_4_geometry", "topic_name": "Pythagorean Theorem", "topic_order": 2, "content": "In a right-angled triangle, the square of the hypotenuse equals the sum of squares of the other two sides: a^2 + b^2 = c^2."},
         
        # Module 5
        {"topic_id": "topic_5_1", "module_id": "mod_5_algebra", "topic_name": "Integer Operations", "topic_order": 1, "content": "Integers include positive and negative whole numbers. Rational numbers can be expressed as a fraction p/q where p and q are integers and q is not zero."},
        {"topic_id": "topic_5_2", "module_id": "mod_5_algebra", "topic_name": "Linear Equations", "topic_order": 2, "content": "Solving a linear equation means finding the value of the variable that makes the equation true. Example: 2x + 5 = 15 implies 2x = 10, so x = 5."},

        # Module 6
        {"topic_id": "topic_final_1", "module_id": "mod_final_exam", "topic_name": "Comprehensive Review", "topic_order": 1, "content": "Review of all Grade 9 Mathematics topics including Reasoning, Functions, Statistics, Geometry, and Algebra."}
    ]

    supabase.table("module_topics").upsert(topics).execute()

    print("✅ IB Math Gr9 Curriculum seeded seeded to Supabase successfully.")


if __name__ == "__main__":
    seed_curriculum()
