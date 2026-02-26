import streamlit as st
import requests
import json
import os
from io import BytesIO

# ---------------- CONFIG ----------------
API_URL = os.getenv("API_URL", "http://localhost:8001")


def fetch_subjects():
    """Fetch available B.Tech subjects"""
    try:
        response = requests.get(f"{API_URL}/subjects")
        if response.status_code == 200:
            return response.json().get("subjects", [])
        return []
    except Exception as e:
        st.error(f"❌ API Error: {e}")
        return []

def fetch_curriculum(subject, grade):
    """Fetch full curriculum data including units and topics"""
    try:
        response = requests.get(f"{API_URL}/curriculum", params={"subject": subject, "grade": grade})
        if response.status_code == 200:
            return response.json()
        return {}
    except Exception as e:
        st.error(f"❌ API Error: {e}")
        return {}

def generate_lesson_plan(subject, grade, topic, teaching_level, preference, model="standard", module_id=None):
    """Generate lesson plan using Lesson Architect"""
    payload = {
        "subject": subject,
        "grade": str(grade),
        "topic": topic,
        "teaching_level": teaching_level.lower(), # Normalize to lowercase
        "teacher_preference": preference,
        "module_id": module_id
    }
    try:
        res = requests.post(f"{API_URL}/teacher/lesson-plan", json=payload, timeout=120)
        if res.status_code == 200:
            return res.json()
        else:
            st.error(f"❌ Error: {res.text}")
            return None
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        return None

def fetch_chapter_resources(subject, grade, chapter):
    """Fetch granular resources (Subtopics + Quiz)"""
    try:
        # Map chapter string "UnitID: Title" -> "Unit 1" style if needed, 
        # but backend should handle the exact string match or ID.
        # For now passing the exact string works with the updated backend.
        payload = {
            "subject": subject,
            "grade": str(grade),
            "chapter": chapter
        }
        res = requests.post(f"{API_URL}/teacher/chapter-resources", json=payload, timeout=60)
        if res.status_code == 200:
            return res.json()
        else:
            st.error(f"❌ Error: {res.text}")
            return None
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        return None

# ================= ANALYTICS UI =================

def render_legacy_dashboard():
    # st.header("📊 Teacher Analytics Dashboard (Advanced)") # Header moved to wrapper
    
    st.subheader("📊 Class Performance")
    
    # 0. Subject Selector
    subjects = fetch_subjects()
    # We need to map Subject Name -> Subject ID for the API
    # Since API expects ID (e.g. btech_data_structures_y2), but fetch_subjects returns names?
    # Actually fetch_subjects returns a list of strings (Subject Names) based on api.py implementation.
    # api.py -> get_subjects -> returns list of strings.
    # But Analytics Service expects subject_id (slug).
    # We need a helper to generate ID from name+grade, OR make sure API handles names.
    # Checking api.py implementation: In /teacher/publish-questions, we generate slug:
    # slug_name = req.subject.lower().replace(" ", "_")
    # subject_id = f"btech_{slug_name}_y{req.grade}"
    # So we should replicate that logic here or update API to accept names. 
    # Let's replicate logic for consistency.
    
    if not subjects:
        st.warning("No subjects found.")
        return

    c_sel, _ = st.columns([1, 2])
    with c_sel:
        selected_subject = st.selectbox("Filter by Subject", ["All Subjects"] + subjects)
        
    subject_query_param = {}
    if selected_subject != "All Subjects":
        # Generate ID (assuming Grade 2 for now as per app default, or we can add grade selector later)
        # For now hardcoding Y2 as per rest of app
        slug = selected_subject.lower().replace(" ", "_")
        subject_id = f"btech_{slug}_y2" 
        subject_query_param = {"subject_id": subject_id}

    # 1. Fetch ALL Data with Filter
    with st.spinner(f"Analyzing {selected_subject}..."):
        try:
            overview = requests.get(f"{API_URL}/teacher/analytics/overview", params=subject_query_param).json()
            perf_dist = requests.get(f"{API_URL}/teacher/analytics/performance", params=subject_query_param).json()
            cohort_dist = requests.get(f"{API_URL}/teacher/analytics/cohort", params=subject_query_param).json()
            leaderboard = requests.get(f"{API_URL}/teacher/analytics/leaderboard", params=subject_query_param).json()
        except Exception as e:
            st.error(f"Failed to load analytics: {e}")
            return

    # 2. Key Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Class Average", f"{overview.get('class_average', 0)}%")
    m2.metric("Total Students", overview.get('total_students', 0))
    m3.metric("At Risk (<50%)", perf_dist.get("Needs Support (<50%)", 0))
    m4.metric("High Performers", perf_dist.get("High Performers (>75%)", 0))
    
    st.divider()

    # 2.5 Cohort Weakness Alert
    weak_areas = overview.get("common_weak_areas", [])
    if weak_areas:
        st.subheader("🚩 Cohort Critical Weaknesses")
        st.caption("Modules where the average cohort score is below 65%.")
        
        # Display as a dataframe with custom column config if possible, or just raw
        st.dataframe(
            weak_areas, 
            column_config={
                "module_name": "Module Name",
                "cohort_average": st.column_config.ProgressColumn(
                    "Avg Score", 
                    format="%.1f%%", 
                    min_value=0, 
                    max_value=100
                ),
                "students_attempted": "Student Count"
            },
            hide_index=True,
            use_container_width=True
        )
        st.divider()

    # 3. Visuals Row 1
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("📉 Performance Bands")
        st.bar_chart(perf_dist)
        st.caption("Distribution of students by average score.")
        
    with c2:
        st.subheader("🚀 Cohort Velocity")
        st.bar_chart(cohort_dist)
        st.caption("Number of modules completed per student.")
        
    st.divider()
    
    # 4. Leaderboards
    st.subheader("🏆 Student Leaderboard")
    l1, l2 = st.columns(2)
    with l1:
        st.markdown("**⭐ Top Performers**")
        if leaderboard.get("top_5"):
            st.dataframe(leaderboard["top_5"], hide_index=True)
        else:
            st.info("No data available.")
            
    with l2:
        st.markdown("**⚠️ Needs Intervention**")
        if leaderboard.get("bottom_5"):
            st.dataframe(leaderboard["bottom_5"], hide_index=True)
        else:
            st.info("No students flagged.")

    st.divider()
    
    # # 5. Module Progress (Original Chart)
    # with st.expander("Detailed Module Breakdown", expanded=False):
    #     mod_data = overview.get("module_progress", [])
    #     if mod_data:
    #         chart_dict = {
    #             d["module"]: {"Completed": d["completed"], "In Progress": d["in_progress"]} 
    #             for d in mod_data
    #         }
    #         st.bar_chart(chart_dict, stack=True)
    #     else:
    #         st.info("No module data available.")

    # st.divider()
    
    # MOVED: Section 6 was here. Now it is below.
    
    # 7. FINAL ASSIGNMENT ANALYTICS (NEW)
    if selected_subject != "All Subjects" and 'subject_id' in subject_query_param:
        st.divider()
        st.subheader("📝 Final Assignment Analytics")
        st.caption(f"Performance on the final exam for {selected_subject}.")
        
        with st.spinner("Loading Exam Stats..."):
             try:
                 exam_res = requests.get(f"{API_URL}/teacher/analytics/exam", params=subject_query_param)
                 if exam_res.status_code == 200:
                     exam_data = exam_res.json()
                     
                     if not exam_data:
                         st.warning("No exam data returned.")
                     else:
                        # Metrics Row
                        em1, em2, em3, em4 = st.columns(4)
                        em1.metric("Submitted", f"{exam_data.get('submitted_count', 0)} / {exam_data.get('total_assigned', 0)}")
                        # em2.metric("Pass Rate (>60%)", f"{exam_data.get('pass_rate', 0)}%")
                        em3.metric("Avg Score", f"{exam_data.get('average_score', 0)}%")
                        
                        # Detailed Table
                        st.markdown("**Student Exam Results**")
                        details = exam_data.get("student_details", [])
                        if details:
                            st.dataframe(
                                details,
                                column_config={
                                    "name": "Student Name",
                                    "score": st.column_config.ProgressColumn(
                                        "Score",
                                        format="%.1f%%",
                                        min_value=0,
                                        max_value=100
                                    ),
                                    "status": st.column_config.SelectboxColumn(
                                        "Status",
                                        options=["completed", "in_progress", "unlocked", "locked"],
                                        disabled=True
                                    )
                                },
                                hide_index=True,
                                use_container_width=True
                            )
                        else:
                            st.info("No student records found for this exam.")
                 else:
                     st.warning("Final Exam has not been assigned or data is unavailable.")
             except Exception as e:
                 st.error(f"Failed to load Exam Analytics: {e}")

    # 8. TEACHER INSIGHTS AGENT (NEW)
    if selected_subject != "All Subjects" and 'subject_id' in subject_query_param:
        st.divider()
        st.subheader("🧠 Teacher Insights")
        st.caption("Analysis of student weak areas to help you plan next week.")
        
        # We can auto-load or button-load. LLM calls cost money/time, so button is safer.
        if st.button("✨ Analyze Weak Areas & Recommend Actions", type="primary"):
            with st.spinner("Agent is analyzing student patterns..."):
                try:
                    insight_res = requests.get(f"{API_URL}/teacher/analytics/insights", params=subject_query_param, timeout=60)
                    if insight_res.status_code == 200:
                        data = insight_res.json()
                        narrative = data.get("insight", "No insights available.")
                        
                        st.markdown("---")
                        st.markdown(narrative) # Render the Agent's Markdown directly
                        st.markdown("---")
                        
                        # Debug: Show raw data toggle
                        with st.expander("Show Raw Data (For Verification)"):
                             st.json(data.get("data", {}))
                    else:
                        st.error(f"Insight Generation Failed: {insight_res.text}")
                except Exception as e:
                    st.error(f"Agent Error: {e}")
    else:
        st.divider()
        st.subheader("🧠 Teacher Insights")
        st.info("👈 Please select a specific **Subject** from the dropdown above to enable AI Insights.")

    st.divider()

    # 6. Student Deep Dive (Existing Logic)
    st.subheader("🔍 Individual Student Drill-down")
    
    # Fetch student list
    try:
        s_res = requests.get(f"{API_URL}/teacher/students")
        students = s_res.json().get("students", [])
    except:
        students = []
        
    student_opts = {s['student_id']: f"{s.get('name', 'Unknown')} ({s['student_id']})" for s in students}
    
    sel_id = st.selectbox("Select Student", options=list(student_opts.keys()), format_func=lambda x: student_opts[x])
    
    if sel_id:
        with st.spinner(f"Loading data for {sel_id}..."):
            try:
                det_res = requests.get(f"{API_URL}/teacher/analytics/student/{sel_id}")
                det = det_res.json()
                
                if det:
                    # Student Metrics
                    sm1, sm2, sm3 = st.columns(3)
                    sm1.metric("Student Average", f"{det.get('average_score', 0)}%")
                    sm2.metric("Overall Progress", f"{det.get('overall_progress', 0)}%")
                    
                    # Weak Areas
                    # wa = det.get("weak_areas", {})
                    # if wa:
                    #     st.markdown("**Weak Areas:**")
                    #     # wa is {topic: count}
                    #     st.json(wa)
                    # else:
                    #      st.success("No weak areas recorded.")
                         
                    # Detailed Module Table
                    st.markdown("#### Module Breakdown")
                    st.dataframe(det.get("modules", []))
                    
            except Exception as e:
                st.error(f"Could not load student details: {e}")

    # MOVED: Section 7 and 8 were here. Now they are above.

def show_analytics_dashboard():
    st.header("📊 Analytics & Outcomes")
    
    t1, t2 = st.tabs(["📉 Class Performance", "🎯 Outcomes (OBE)"])
    
    with t1:
        render_legacy_dashboard()
        
    with t2:
        try:
            from .pages.obe_dashboard import render_obe_dashboard
            render_obe_dashboard()
        except ImportError:
            try:
                from Teacher.pages.obe_dashboard import render_obe_dashboard
                render_obe_dashboard()
            except Exception as e:
                st.error(f"Failed to load OBE Dashboard: {e}")

# ================= MAIN UI =================
def main():
    st.set_page_config(page_title="Teacher Agent | B.Tech", page_icon="🎓", layout="wide")
    
    # Custom CSS - Force Light Mode & Clean Look
    st.markdown("""
    <style>
    .stButton>button { border-radius: 8px; font-weight: 600; }
    .unit-card { border: 1px solid #444; padding: 15px; border-radius: 8px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

    # Initialize Session State
    if 'step' not in st.session_state:
        st.session_state.step = 1
    if 'curriculum_data' not in st.session_state:
        st.session_state.curriculum_data = {}
    if 'selected_chapter' not in st.session_state:
        st.session_state.selected_chapter = None
    if 'lesson_plan' not in st.session_state:
        st.session_state.lesson_plan = None
    if 'full_assessment' not in st.session_state:
        st.session_state.full_assessment = None

    # Header
    st.title("🎓 Teacher Agent: B.Tech Curriculum")

    # Navigation
    menu = st.sidebar.radio("Navigation", ["Lesson Planner", "Analytics Dashboard", "Outcomes Manager"])

    # Import and render outcomes manager if selected
    if menu == "Outcomes Manager":
        try:
            # Try relative import first (cleanest if running as package)
            from .pages.outcomes_manager import render_outcomes_manager
            render_outcomes_manager()
        except ImportError:
            try:
                # Try absolute import
                from Teacher.pages.outcomes_manager import render_outcomes_manager
                render_outcomes_manager()
            except ImportError as e:
                import sys
                st.error(f"Import failed: {e}")
                st.code(f"Sys Path: {sys.path}")
        return

    if menu == "Analytics Dashboard":
        show_analytics_dashboard()
        return

    # --- STEP 1: SELECT CURRICULUM ---
    if st.session_state.step == 1:
        st.header("Step 1: Select Course")
        
        # Load Subjects dynamically
        with st.spinner("Fetching Subjects..."):
            subjects = fetch_subjects()
        
        if not subjects:
            st.warning("⚠️ No subjects found. Ensure API is running.")
            if st.button("🔄 Retry"):
                st.rerun()
            return

        c1, c2 = st.columns([2, 1])
        with c1:
            selected_subject = st.selectbox("Subject", subjects)
        with c2:
            st.markdown("**Grade/Year**")
            st.markdown("📅 Year 2 (B.Tech)")
            selected_grade = "2"

        if st.button("🚀 Load Units", type="primary"):
            with st.spinner(f"Loading curriculum for {selected_subject}..."):
                res_data = fetch_curriculum(selected_subject, selected_grade)
                if res_data and "units" in res_data:
                    st.session_state.curriculum_data = {
                        "subject": selected_subject,
                        "grade": selected_grade,
                        "units": res_data["units"]
                    }
                    st.session_state.full_assessment = None # Reset
                    st.rerun()

        # Display Loaded Curriculum
        if "units" in st.session_state.curriculum_data:
            st.divider()
            st.subheader(f"📚 Units: {st.session_state.curriculum_data['subject']}")
            
            units = st.session_state.curriculum_data['units']
            
            for i, unit in enumerate(units):
                unit_id = unit.get("unit_id", "")
                unit_title = unit.get("unit_title", "Unknown Unit")
                display_title = f"{unit_id}: {unit_title}"
                
                with st.expander(f"📖 {display_title}", expanded=True):
                    # Inline Topics
                    st.markdown("**Key Topics:**")
                    topics = unit.get("topics", [])
                    if topics:
                        t_cols = st.columns(2)
                        for idx, t in enumerate(topics):
                            t_name = t.get("topic_name", "")
                            col = t_cols[idx % 2]
                            col.info(f"• {t_name}")
                    else:
                        st.caption("No specific topics listed.")
                        
                    st.write("")
                    st.write("")
                    if st.button("📝 Plan Lesson", key=f"plan_{i}"):
                        st.session_state.selected_chapter = display_title
                        st.session_state.selected_module_id = unit.get("unit_id") # Capture ID
                        st.session_state.step = 2
                        st.session_state.lesson_plan = None
                        st.rerun()

            st.divider()
            st.markdown("### ⚡ Course Assessment")
            
            # Button Logic
            if st.button("Generate Questions (All Units)", type="primary", use_container_width=True):
                 with st.spinner("Generating comprehensive assessment..."):
                     all_questions = []
                     
                     # --- BATCH OPTIMIZATION (Default) ---
                     req_map = {}
                     for unit in units:
                         unit_title = f"{unit['unit_id']}: {unit['unit_title']}"
                         req_map[unit_title] = 5
                     
                     payload = {
                         "subject": st.session_state.curriculum_data['subject'],
                         "grade": st.session_state.curriculum_data['grade'],
                         "requests": req_map
                     }
                     
                     try:
                         res = requests.post(f"{API_URL}/teacher/batch-chapter-resources", json=payload, timeout=120)
                         if res.status_code == 200:
                             data = res.json()
                             # Parse generic map -> flat list
                             for resource_item in data.get("resources", []):
                                 for q in resource_item.get("questions", []):
                                     q["chapter"] = resource_item["chapter"] # Ensure tag
                                     all_questions.append(q)
                             
                             # Success message removed as per request
                         else:
                             st.error(f"Batch Error: {res.text}")
                     except Exception as e:
                         st.error(f"Batch Connection Error: {e}")
                     
                     st.session_state.full_assessment = all_questions
            
            # Display Full Assessment
            if st.session_state.full_assessment:
                st.success(f"✅ Generated {len(st.session_state.full_assessment)} questions across {len(units)} units")
                
                # --- SELECTION FORM ---
                selected_indices = []
                
                with st.form("publish_form"):
                    st.markdown("### 📋 Review & Publish")
                    st.caption("Select questions to save to the Final Exam Database.")
                    
                    for i, q in enumerate(st.session_state.full_assessment):
                        with st.container():
                            c1, c2 = st.columns([0.05, 0.95])
                            with c1:
                                # Default Select All? Or Let user pick? Let's default True.
                                is_selected = st.checkbox("", value=True, key=f"sel_{i}")
                                if is_selected:
                                    selected_indices.append(i)
                            with c2:
                                st.markdown(f"**Q{i+1}. {q.get('question')}**")
                                st.caption(f"Difficulty: {q.get('difficulty')} | Chapter: {q.get('chapter')}")
                                
                                with st.expander("Show Details"):
                                    st.write(f"**Answer:** {q.get('correct_answer')}")
                                    st.write(f"**Options:** {q.get('options')}")
                        st.divider()
                    
                    submitted = st.form_submit_button("🚀 Publish Selected Questions")
                    
                    replace_flag = st.checkbox("Replace existing final exam questions?", value=True, help="If checked, this will delete ALL previous Local Exam questions for this subject and replace them with the selection.")
                    
                    if submitted:
                        if not selected_indices:
                            st.warning("⚠️ No questions selected.")
                        else:
                            selected_qs = [st.session_state.full_assessment[i] for i in selected_indices]
                            
                            msg = "Overwriting Exam & Publishing..." if replace_flag else "Appending to Exam..."
                            with st.spinner(msg):
                                try:
                                    pub_payload = {
                                        "subject": st.session_state.curriculum_data['subject'],
                                        "grade": st.session_state.curriculum_data['grade'],
                                        "questions": selected_qs,
                                        "replace_existing": replace_flag
                                    }
                                    res = requests.post(f"{API_URL}/teacher/publish-questions", json=pub_payload)
                                    if res.status_code == 200:
                                        data = res.json()
                                        st.success(f"✅ {data['message']}")
                                    else:
                                        st.error(f"❌ Failed: {res.text}")
                                except Exception as e:
                                    st.error(f"❌ Error: {e}")

    # --- STEP 2: LESSON PLANNING ---
    elif st.session_state.step == 2:
        st.markdown(f"### 🪄 Lesson Planner: '{st.session_state.selected_chapter}'")
        
        if st.button("← Back"):
            st.session_state.step = 1
            st.rerun()
            
        st.divider()
        
        c1, c2 = st.columns([1, 2])
        
        with c1:
            st.markdown("#### ⚙️ Configure")
            # Phase 2: Teaching Level
            # interactive_score = st.slider("Interactive Score (1-5)", 1, 5, 3) 
            teaching_level = st.select_slider(
                    "Teaching Level",
                    options=["Beginner", "Intermediate", "Advanced"],
                    value="Intermediate",
                    help="Adjusts the pedagogical voice and depth."
            )
            
            # Dynamic Help Text
            if teaching_level == "Beginner":
                st.caption("ℹ️ Voice: ELI5, Analogies, Visuals. Focus on Concepts.")
            elif teaching_level == "Intermediate":
                st.caption("ℹ️ Voice: Standard B.Tech depth")
            elif teaching_level == "Advanced":
                st.caption("ℹ️ Voice: Deep Dive, Edge Cases, Scalability. Focus on Application.")
            
            preference = st.text_area("Teacher Preference", height=100)
            
            if st.button("✨ Generate Plan", type="primary", use_container_width=True):
                with st.spinner("Generating..."):
                     plan = generate_lesson_plan(
                         st.session_state.curriculum_data['subject'],
                         st.session_state.curriculum_data['grade'],
                         st.session_state.selected_chapter,
                         teaching_level,
                         preference,
                         module_id=st.session_state.get("selected_module_id") # Pass ID
                     )
                    #  st.write(f"🔍 DEBUG: Sent Module ID: {st.session_state.get('selected_module_id')}")
                     st.session_state.lesson_plan = plan

        with c2:
            st.markdown("#### 📝 Lesson Timeline")
            if st.session_state.lesson_plan:
                res = st.session_state.lesson_plan
                
                # --- DISPLAY REASONING LOGS ---
                with st.expander("🧠 Architect Reasoning (Why this plan?)", expanded=True):
                    meta = res.get("meta", {})
                    st.info(f"**Strategy**: {meta.get('why_this_structure', 'N/A')}")
                    st.success(f"**Methodology**: {meta.get('teaching_level', 'Standard')}")
                    
                    st.caption("⏱️ **Time Allocation Logic**:")
                    time_breakdown = meta.get("estimated_time_breakdown", {})
                    t_cols = st.columns(len(time_breakdown)) if time_breakdown else [st]
                    for idx, (k, v) in enumerate(time_breakdown.items()):
                        t_cols[idx % len(t_cols)].metric(k.title(), v)

                st.divider()
                st.info(f"Style: **{res['meta'].get('style', 'Standard')}**")
                
                for item in res.get("timeline", []):
                    # SPECIAL HANDLING: Summary Card (Outcome Achievement)
                    if item.get("type") == "summary":
                        st.success(f"### {item['title']}")
                        content_items = item.get("content", [])
                        
                        # Custom rendering for clarity
                        for c in content_items:
                            t = c.get("term", "")
                            d = c.get("definition", "")
                            st.markdown(f"**{t}**: {d}")
                        
                        st.divider()
                        continue
                        
                    # SPECIAL HANDLING: Overview Phase

                    # Schema Normalization (RAG vs Legacy)
                    title = item.get("title", item.get("section", "Untitled Segment"))
                    duration = item.get("duration", f"{item.get('duration_minutes', '?')} min")
                    reasoning = item.get("reasoning", "")
                    
                    with st.container():
                        st.markdown(f"**{title} ({duration})**")
                        if reasoning:
                            st.caption(reasoning)

                        # --- NEW: CO & Engagement Banner ---
                        co_map = item.get("co_mapping")
                        if co_map:
                             # Display subtle badge
                             codes = ", ".join(co_map.get("codes", []))
                             source = co_map.get("source", "inference")
                             st.caption(f"🎯 **Outcome Alignment**: {codes} (via {source})")
                             
                        eng = item.get("engagement")
                        if eng:
                            with st.expander("💡 Engagement Suggestions (How to Teach)", expanded=True):
                                for e_item in eng:
                                    if isinstance(e_item, dict):
                                        # STRUCTURED ENGAGEMENT (New)
                                        cols = st.columns([1, 4])
                                        with cols[0]:
                                            st.metric("⏱️ Time", f"{e_item.get('duration_minutes', 5)}m")
                                            st.caption(f"**{e_item.get('engagement_type', 'Activity').replace('_', ' ').title()}**")
                                        
                                        with cols[1]:
                                            st.markdown(f"🗣️ **Teacher Says:** *\"{e_item.get('teacher_script', '')}\"*")
                                            st.markdown(f"👥 **Students Do:** {e_item.get('student_action', '')}")
                                            st.info(f"🔑 **Key Realization:** {e_item.get('key_realization', '')}")
                                            st.success(f"✅ **Quick Check:** {e_item.get('quick_check', '')}")
                                    else:
                                        # LEGACY (String)
                                        st.markdown(f"- {e_item}")
                                    st.divider()

                        # Schema Normalization: 'items' (Legacy) vs 'content' (RAG) vs 'sections' (New RAG)
                        raw_content = item.get("items", item.get("content", item.get("sections", [])))
                        
                        # Handle if RAG returned a string content
                        if isinstance(raw_content, str):
                            st.write(raw_content)
                            content_list = []
                        else:
                            content_list = raw_content

                        for content_item in content_list:
                            if isinstance(content_item, dict):
                                # 1. CODE BLOCK
                                if "code" in content_item:
                                    st.markdown(f"**{content_item.get('description', 'Code Example')}:**")
                                    st.code(content_item["code"], language="python")
                                
                                # 2. DEFINITIONS (Term + Def)
                                elif "term" in content_item:
                                    st.markdown(f"🔹 **{content_item['term']}**: {content_item['definition']}")
                                    
                                # 3. QUESTIONS (Q + A)
                                elif "question" in content_item:
                                    with st.expander(f"❓ {content_item['question']}"):
                                        st.write(f"**Answer:** {content_item['answer']}")
                                        
                                # 4. COMPARISON TABLE ROW
                                elif "aspect" in content_item:
                                    # Formatted as a bullet for now, or could use st.table if we aggregated them
                                    # Let's keep it simple: Bold Aspect
                                    st.markdown(f"⚖️ **{content_item['aspect']}**: {content_item.get('algorithm', '')} vs {content_item.get('data_structure', '')}")
                                
                                # 5. VISUALS
                                elif "nodes" in content_item:
                                    st.info(f"🎨 **Visual**: {content_item.get('description')}")
                                    st.caption(f"Nodes: {content_item.get('nodes')} | Edges: {content_item.get('edges')}")

                                # 6. GENERIC SECTIONS (New RAG Template)
                                elif "label" in content_item and "content" in content_item:
                                    st.markdown(f"**{content_item['label']}**")
                                    st.write(content_item['content'])
                                    
                                # Fallback for generic dict
                                else:
                                    st.markdown(f"- {str(content_item)}")
                            else:
                                # Standard string content
                                st.markdown(f"- {content_item}")
                        st.divider()
            else:
                 st.info("👈 Set options and click Generate Plan")

if __name__ == "__main__":
    main()
