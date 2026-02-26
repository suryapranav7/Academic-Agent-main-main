# Teacher Agent Architectural Definitions

## 1. Lesson Planner (The Architect)
The **Lesson Architect** is a dual-phase RAG system that acts as a pedagogical engine. It does not merely "summarize" text; it constructs valid teaching artifacts based on strict academic rules.

### A. Teaching Levels (The Voice Governor)
The Agent modulates its "Teaching Voice" based on the selected level. This is enforced via a system-level **Depth Governor**.

| Level | Definition & Constraint Logic | Target Audience |
| :--- | :--- | :--- |
| **Beginner** | **Intuition First.** <br> • **Rule**: Use real-world analogies (e.g., Stack = Cafeteria Trays). <br> • **Forbidden**: Complex pointer arithmetic, Big-O proofs. <br> • **Focus**: "What" and "Why" over "How". | First-year students; Non-CS majors. |
| **Intermediate** | **Standard B.Tech.** <br> • **Rule**: Balanced mix of formal definition, algorithm steps, and code. <br> • **Requirement**: Must cite standard textbook definitions. <br> • **Focus**: Correctness and implementation. | Standard undergraduate curriculum. |
| **Advanced** | **Architectural Depth.** <br> • **Rule**: Must include **Complexity Analysis** (Time/Space) and **Memory Management** details. <br> • **Focus**: Scalability, Trade-offs, Edge Cases, and Production readiness. | Final-year students; Interview Prep. |

### B. Architectural Workflow (The 2-Phase Engine)
To prevent hallucinations and ensures structural integrity, the generation process is split:

1.  **Phase A: Skeleton Design**
    *   **Input**: Topic + Teaching Level + Preferences.
    *   **Action**: The LLM acts as a "Curriculum Designer". It produces a **JSON structure** (titles, sections, depth instructions) *without* writing any content.
    *   **Output**: A valid Teaching Skeleton.

2.  **Plan Overview Generation**
    *   **Action**: A parallel task looks at the *entire* skeleton and writes a 4-6 sentence **Meta-Overview** explaining the lesson's flow.

3.  **Phase B: Content Construction**
    *   **Input**: Approved Skeleton Node + RAG Source Context.
    *   **Action**: The LLM acts as a "Subject Matter Expert". It fills each section of the skeleton with academic content, strictly adhering to the `source_material`.
    *   **Output**: Final Lesson Content blocks.

---

## 2. Analytics Suite (The Observer)
The Analytics engine determines student standing not by simple averages, but by **aggregated failure patterns**.

### A. Weak Area Definitions
We do not rely on pre-computed flags. Weakness is derived dynamically from the `student_analytics` table (JSONB `weak_areas` column).

*   **Weakness Detection**: A topic is flagged if a student scores **< 60%** in the relevant module.
*   **Severity Categorization** (Cohort Level):
    *   **Mild**: Only **1** student is struggling. (Monitor)
    *   **Moderate**: **2-3** students are struggling. (Review)
    *   **Critical**: **≥ 4** students are struggling. (Immediate Intervention Required)

*   **Priority Score Calculation**:
    $$ Priority = (Count_{Critical} \times 3) + (Count_{Moderate} \times 2) + (Count_{Mild} \times 1) $$
    *Topics with higher Priority Scores appear at the top of the Teacher Insights report.*

### B. Student Position Logic ("Good" vs "Bad")
*   **Good Position**:
    *   Average Score > 75%
    *   Completed Modules > Class Average Count
    *   No "Critical" Weak Areas.
*   **Needs Support ("Bad" Position)**:
    *   Average Score < 50%
    *   **OR** Failed (>3 attempts) on any "Core" module.
    *   **OR** Velocity (modules/week) is 50% below cohort average.

---

## 3. OBE Dashboard (Outcome Based Education)
This module mathematically quantifies learning attainment.

### A. Calculation Logic
We track two layers of attainment: **CO (Course Outcome)** and **PO (Program Outcome)**.

#### 1. CO Attainment Formula
For a specific Course Outcome ($CO_x$), mapped to a set of Modules ($M_{1...n}$):

$$ Attainment(CO_x) = \frac{ \sum_{i=1}^{n} (Score(M_i) \times Weight(M_i)) }{ \sum_{i=1}^{n} TotalPossibleWeight(M_i) } $$

*   **Score($M_i$)**: Student's best score in Module $i$ (Normalized 0-100).
*   **Weight($M_i$)**: How strongly Module $i$ contributes to $CO_x$ (defined in `module_co_mapping`).

**Status Determination**:
*   **Achieved**: $Attainment \ge TargetThreshold$ (e.g., 60%).
*   **Not Achieved**: $Attainment < TargetThreshold$.

#### 2. PO Attainment Formula
Program Outcomes are higher-level goals (e.g., "Engineering Knowledge"). They are attained via COs.

$$ Attainment(PO_y) = \frac{ \sum (Attainment(CO_j) \times MapWeight(CO_j \rightarrow PO_y)) }{ \sum MapWeight(CO_j \rightarrow PO_y) } $$

*   This is a weighted average of the attainment of all COs that map to a specific PO.

### B. "Good" vs "Bad" Attainment
*   **Good Attainment**: Consistent $>60\%$ across all mapped COs.
*   **Gap/Bad Attainment**: Any PO where the calculated attainment is $>10\%$ below the department target.

---

## 4. Full Teacher Agent Flow
The complete lifecycle of the Teacher Agent:

1.  **Ingestion**:
    *   Teacher uploads/selects Curriculum (Units/Topics).
    *   System enriches topics with JSON metadata (Subject mapping).

2.  **Assessment & Data Gathering**:
    *   Teacher uses **Question Engine** to generate/publish assessments.
    *   Students take assessments (Student Agent).
    *   Results flow into `student_module_status` and `student_analytics`.

3.  **Analysis (The Loop)**:
    *   **Real-time Check**: Is the Cohort Average < 60%?
    *   **Weak Area Aggregation**: Group failures by Topic ID.
    *   **Insight Generation**: AI Agent reads aggregated stats -> Writes "Teacher Insights" narrative.

4.  **Intervention (The Action)**:
    *   Teacher views "Critical Weakness" (e.g., "Arrays").
    *   Teacher invokes **Lesson Architect**.
    *   **Plan Generation**: "Generate Remedial Lesson on Arrays (Beginner Level)".
    *   **Execution**: Teacher delivers lesson -> Re-assesses -> Loop closes.
