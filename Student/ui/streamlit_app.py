
import streamlit as st
import sys
import os
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from ui.api_client import APIClient

# -----------------------------------------------------------------------------
# APP CONFIGURATION & STATE
# -----------------------------------------------------------------------------

# Config moved to __main__ block

# Initialize API Client (Cached)
@st.cache_resource
def get_api_client():
    return APIClient()

def main():
    st.title("Student Agent System")
    
    api_client = get_api_client()

    # Initialize Session State
    if "student_id" not in st.session_state:
        st.session_state["student_id"] = ""

    if "subject_id" not in st.session_state: 
        st.session_state["subject_id"] = None

    if "assessment_state" not in st.session_state:
        st.session_state["assessment_state"] = None
    
    # st.info(f"DEBUG: Current Subject ID: {st.session_state['subject_id']}") # DEBUG LINE
    
    # -----------------------------------------------------------------------------
    # SIDEBAR: STUDENT & CURRICULUM
    # -----------------------------------------------------------------------------
    
    with st.sidebar:
        st.header("Student Profile")
        
        # 1. Student ID
        new_student_id = st.text_input("Student ID", value=st.session_state["student_id"], key="student_id_input", placeholder="Enter ID")
        if new_student_id != st.session_state["student_id"]:
            st.session_state["student_id"] = new_student_id
            st.session_state["chat_history"] = []
            st.session_state["assessment_state"] = None
            st.rerun()
        
        # 2. Grade Selection (Empty Default)
        # Use session state to persist manual entry but default is ""
        if "grade_val" not in st.session_state:
             st.session_state["grade_val"] = ""
             
        new_grade = st.text_input("Grade", value=st.session_state["grade_val"], key="grade_input", placeholder="e.g. 9 or 2")
        
        # Detect Grade Change
        if new_grade != st.session_state["grade_val"]:
             st.session_state["grade_val"] = new_grade
             st.session_state["subject_id"] = None # Reset subject
             st.rerun()

        # 3. Subject Selection (Only if Grade is present)
        if st.session_state["grade_val"]:
             try:
                 subjects = api_client.get_subjects_by_grade(st.session_state["grade_val"])
             except Exception as e:
                 st.error(f"Error fetching subjects: {e}")
                 subjects = []
             
             if subjects:
                 # Map name -> id for usability
                 # Create options list 
                 subj_map = {s["subject_name"]: s["subject_id"] for s in subjects}
                 options = list(subj_map.keys())
                 
                 # Find current index
                 current_idx = 0
                 # Try to preserve selection if valid
                 if st.session_state["subject_id"] in subj_map.values():
                      for i, name in enumerate(options):
                           if subj_map[name] == st.session_state["subject_id"]:
                                current_idx = i
                                break
                 
                 selected_name = st.selectbox("Select Subject", options=options, index=current_idx)
                 
                 # Update State
                 if selected_name:
                      new_sub_id = subj_map[selected_name]
                      if new_sub_id != st.session_state["subject_id"]:
                           st.session_state["subject_id"] = new_sub_id
                           st.session_state["assessment_state"] = None # Reset assessment
                           st.rerun()
             else:
                 st.warning(f"No subjects found for Grade {st.session_state['grade_val']}")
                 st.session_state["subject_id"] = None

    # 🛑 BLOCKING VALIDATION 🛑
    if not st.session_state["student_id"]:
        st.info("👋 Welcome! Please enter a **Student ID** in the sidebar to begin.")
        st.stop()
        
    if not st.session_state["grade_val"]:
        st.info("Please enter a **Grade** to load subjects.")
        st.stop()

    if not st.session_state["subject_id"]:
        st.warning("Please select a **Subject** from the sidebar.")
        st.stop()

    # Ensure student exists in DB via API (Register Logic)
    try:
        api_client.register_student(
            st.session_state["student_id"], 
            st.session_state["subject_id"],
            grade=st.session_state["grade_val"]
        )
    except Exception as e:
        st.error(f"Failed to connect to API: {e}")
        st.stop()

    st.header("Learning Path") # Renamed from Curriculum
    
    # Fetch Data from API
    try:
        modules = api_client.get_modules(st.session_state["subject_id"])
        progress = api_client.get_progress(st.session_state["student_id"])
    except Exception as e:
        st.error(f"API Error: {e}")
        modules = []
        progress = []

    prog_map = {p['module_id']: p['status'] for p in progress}
    
    # Filter/Select Module
    module_options = []
    default_index = 0
    
    for idx, m in enumerate(modules):
        mid = m['module_id']
        status = prog_map.get(mid, "locked")
        # Visual Indicators for new status
        icon = "🔒" if status == "locked" else "✅" if status == "completed" else "🔓" # Unlocked is now open/play
        label = f"{icon} {m['module_name']}"
        module_options.append((mid, label, status))
        if status == "unlocked" and default_index == 0: # Default to first unlocked
             default_index = idx
        elif status == "completed":
             pass # Keep looking for active one? Default logic is simple here.

    if not module_options:
        st.warning("No modules found.")
        st.stop()

    selected_module_tuple = st.radio(
        "Select Module",
        module_options,
        format_func=lambda x: x[1],
        index=default_index
    )
    
    selected_module_id = selected_module_tuple[0]
    selected_module_status = selected_module_tuple[2]
    
    st.markdown("---")
    if st.button("🔄 Reset Assessment State"):
        st.session_state["assessment_state"] = None
        st.rerun()


    # -----------------------------------------------------------------------------
    # MAIN CONTENT
    # -----------------------------------------------------------------------------
    
    tab_learn, tab_assess, tab_analytics = st.tabs(["🧠 Learn", "📝 Assessment", "📊 Analytics"])
    
    # --- 🧠 LEARN TAB ---
    with tab_learn:
        # Use Label from selection (which contains Name) or resolve it
        # selected_module_tuple format: (id, label, status)
        st.subheader(f"Module: {selected_module_tuple[1]}") 
        
        if selected_module_status == "locked":
            st.warning("This module is locked. Complete the previous modules first.")
        else:
            chat_container = st.container()
            
            # Simple chat history in session state
            if "chat_history" not in st.session_state:
                st.session_state["chat_history"] = []
                
            for role, text in st.session_state["chat_history"]:
                with st.chat_message(role):
                    st.write(text)
    
            user_query = st.chat_input("Ask your tutor a question...")
            
            if user_query:
                # User Message
                st.session_state["chat_history"].append(("user", user_query))
                with st.chat_message("user"):
                    st.write(user_query)
                
                # Agent Response
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        try:
                            result = api_client.learn(
                                student_id=st.session_state["student_id"],
                                message=user_query,
                                context={"module_id": selected_module_id}
                            )
                            # API returns {"response": "...", "metadata": ...}
                            response = result["response"]
                            st.write(response)
                            st.session_state["chat_history"].append(("assistant", response))
                        except Exception as e:
                            st.error(f"Error: {e}")
    
    # --- 📝 ASSESSMENT TAB ---
    with tab_assess:
        # Resolve Module Name for Header (from selected tuple)
        # selected_module_tuple = (id, label, status)
        # label format: "✅ Trigonometry"
        # We can extract name or just use label.
        st.subheader(f"Assessment: {selected_module_tuple[1]}") # Use Label
    
        if selected_module_status == "locked":
            st.warning("Locked.")
        elif selected_module_status == "completed":
            st.success("You have already passed this module! You can retry to improve your score.")
            if st.button("Retake Assessment"):
                st.session_state["assessment_state"] = None
                st.rerun()
        
        # Initialize Assessment Loop State
        if st.session_state["assessment_state"] is None:
            st.session_state["assessment_state"] = {
                "active": False,
                "current_question_index": 0,
                "questions": [], # List of dicts {text, options, id} - handled by agent
                "score": 0,
                "difficulty": "medium",
                "history": [], # {question, answer, feedback, correct}
                "complete": False
            }
    
        state = st.session_state["assessment_state"]
        TARGET_QUESTIONS = 6
    
        if not state["active"] and not state["complete"]:
            st.info("Total Questions: 6 (Standard) or All (Final Exam)  \nDifficulty adjusts based on your answers  \n Correct → harder questions  \n Incorrect → easier questions  \n This helps identify your actual skill level, not just memorization")
            if st.button("Start Assessment"):
                state["active"] = True
                
                # CHECK IF FINAL EXAM
                is_final = "final" in selected_module_id.lower() or "assessment" in selected_module_tuple[1].lower() 
                # Better check: "Final Assessment" in label or specific ID pattern
                
                state["is_final"] = is_final  # Store flag in state

                if is_final:
                    with st.spinner("Loading Final Assessment Questions..."):
                        try:
                            final_qs = api_client.get_final_questions(selected_module_id)
                            # final_qs is list of dicts.
                            state["questions"] = final_qs 
                            # Need to set target questions len
                            # TARGET_QUESTIONS will be dynamic for final 
                        except Exception as e:
                            st.error(f"Failed to load final questions: {e}")
                            state["active"] = False
                            
                st.rerun()
    
        # ASSESSMENT LOOP
        if state["active"] and not state["complete"]:
            # Recalculate Target for Final (Pre-loaded), else keep 6
            if state.get("is_final", False) and state["questions"]: # Only for Final
                 TARGET_QUESTIONS = len(state["questions"])

            
            idx = state["current_question_index"]
            
            # Bound check
            if idx >= TARGET_QUESTIONS:
                 state["complete"] = True
                 st.rerun()
            
            st.progress((idx) / TARGET_QUESTIONS, text=f"Question {idx+1} of {TARGET_QUESTIONS}")
            
            # 1. Generate Question (ONLY IF NOT PRE-LOADED)
            if len(state['questions']) <= idx:
                with st.spinner("Agent is creating a targeted question..."):
                    try:
                        q_res = api_client.generate_question(
                            student_id=st.session_state["student_id"],
                            module_id=selected_module_id,
                            difficulty=state["difficulty"]
                        )
                        state["questions"].append(q_res) # Store full object
                    except Exception as e:
                        st.error(f"Failed to generate question: {e}")
                        st.stop()
            
            current_q_data = state["questions"][idx]
            # Handle both string (legacy) and dict (new) formats
            if isinstance(current_q_data, str):
                 current_q_text = current_q_data
                 current_q_id = None
            else:
                 current_q_text = current_q_data["question"]
                 current_q_id = current_q_data.get("question_id")
                 
                 # NEW: Append Options if present (Specific for Final/Batch mode)
                 opts = current_q_data.get("options")
                 if opts and isinstance(opts, list):
                     formatted_opts_list = []
                     letters = ['A', 'B', 'C', 'D']
                     for i, opt in enumerate(opts):
                         if i < len(letters):
                             formatted_opts_list.append(f"{letters[i]}) {opt}")
                     
                     formatted_opts = "\n\n".join(formatted_opts_list)
                     current_q_text += f"\n\n{formatted_opts}"
            
            # 2. Display Question
            st.markdown(f"**Q{idx+1}:**")
            st.code(current_q_text, language="markdown") 
            
            # 3. Answer Input
            user_choice = st.radio(
                "Select your answer:",
                ["A", "B", "C", "D"],
                key=f"q_{idx}",
                index=None
            )
            
            if st.button("Submit Answer", type="primary"):
                if not user_choice:
                    st.warning("Please select an option.")
                else:
                    # 4. Evaluate via API
                    with st.spinner("Grading..."):
                        try:
                            eval_res = api_client.evaluate_answer(
                                student_id=st.session_state["student_id"],
                                question=current_q_text,
                                answer=user_choice,
                                question_id=current_q_id
                            )
                            
                            feedback = eval_res["feedback"]
                            is_correct = eval_res["is_correct"]
                            
                            st.session_state["last_feedback"] = feedback 
                            
                            if is_correct:
                                state["score"] += 1
                                state["difficulty"] = "hard"
                                st.toast("Correct! 🎉", icon="✅")
                            else:
                                state["difficulty"] = "easy"
                                st.toast("Incorrect.", icon="❌")
                            
                            state["history"].append({
                                "question": current_q_text,
                                "answer": user_choice,
                                "feedback": feedback,
                                "correct": is_correct
                            })
                            
                            # Move Next
                            state["current_question_index"] += 1
                            if state["current_question_index"] >= TARGET_QUESTIONS:
                                state["complete"] = True
                                state["active"] = False
                            
                            st.rerun()
                        except Exception as e:
                            st.error(f"Evaluation Error: {e}")
    
        # COMPLETION
        if state["complete"]:
            # Calculate Stats
            questions = state["questions"]
            history = state["history"]
            
            easy_attempted = 0
            hard_attempted = 0
            weak_topics = set()
            strong_topics = set()
            attempts_payload = []
            
            for idx, h in enumerate(history):
                if idx >= len(questions): break 
                q_data = questions[idx]
                is_correct = h["correct"]
                
                # Extract Metadata
                if isinstance(q_data, str):
                    diff = "medium"
                    tid = None
                    qid = None
                else:
                    diff = q_data.get("difficulty", "medium")
                    tid = q_data.get("topic_id")
                    qid = q_data.get("question_id")
                    
                # Stats
                # Fix: Treat 'medium' as 'medium/hard' contribution for now, or split properly. 
                # User asked for "entry level as hard" -> Assuming "medium" counts towards "Hard" bucket?
                # Or simply: Total Questions = Easy + Hard
                # If question is NOT easy, count as Hard.
                if diff == "easy": 
                    easy_attempted += 1
                else: 
                    hard_attempted += 1 # Medium + Hard
                
                # Weakness logic
                if not is_correct and tid: 
                    # Resolve Name
                    t_name = tid
                    try:
                        t_data = api_client.get_topic(tid)
                        if t_data: t_name = t_data.get("topic_name", tid)
                    except: pass
                    weak_topics.add(t_name)

                if is_correct and diff == "hard" and tid: 
                     # Resolve Name
                    t_name = tid
                    try:
                        t_data = api_client.get_topic(tid)
                        if t_data: t_name = t_data.get("topic_name", tid)
                    except: pass
                    strong_topics.add(t_name)
                
                # Payload
                attempts_payload.append({
                    "question_id": qid,
                    "student_answer": h["answer"],
                    "is_correct": is_correct
                })


            # FIX: Use actual question count, as TARGET_QUESTIONS might reset on rerun
            total_questions_count = len(questions) if questions else TARGET_QUESTIONS
            final_score = state["score"] / total_questions_count if total_questions_count > 0 else 0

            passed = final_score >= 0.6
            status_txt = "PASSED" if passed else "FAILED"
            color = "green" if passed else "red"
            
            st.markdown(f"## Assessment Complete")
            st.markdown(f"### Score: :{color}[{final_score:.0%}] - {status_txt}")
            
            # Analytics Display
            col1, col2 = st.columns(2)
            col1.metric("Easy Questions", easy_attempted)
            col2.metric("Hard Questions", hard_attempted)
            
            if weak_topics:
                st.error(f"**Focus Areas (Weak):** {', '.join(weak_topics)}")
            # if strong_topics:
            #     st.success(f"**Strengths:** {', '.join(strong_topics)}")

            # --- 💡 AI Suggestions ---
            st.subheader("💡 Personalized Study Plan")
            with st.spinner("AI Tutor is analyzing your results..."):
                if "ai_suggestion" not in st.session_state:
                     try:
                        # Construct context
                        perf_context = f"Student just completed assessment for {selected_module_id}. Score: {final_score:.0%}. Passed: {passed}. Weak Areas: {list(weak_topics)}. History: {str(history)}"
                        prompt = "Based on this assessment performance, provide 3 specific study tips or topics to review. Be encouraging but direct."
                        
                        sugg = api_client.learn(
                            student_id=st.session_state["student_id"],
                            message=prompt,
                            context={"module_id": selected_module_id, "system_instruction": "You are a study coach. Analyze the performance."}
                        )
                        st.session_state["ai_suggestion"] = sugg["response"]
                     except Exception as e:
                        st.session_state["ai_suggestion"] = "Could not generate suggestions at this time."
            
            st.info(st.session_state["ai_suggestion"])

            if st.button("Record Result & Finish"):
                try:
                    api_client.record_assessment(
                        student_id=st.session_state["student_id"], 
                        module_id=selected_module_id, 
                        score=final_score, 
                        passed=passed,
                        attempts=attempts_payload # Pass the detailed history for analytics
                    )
                    st.success("Progress saved!")
                    st.session_state["assessment_state"] = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving result: {e}")
                
            with st.expander("View Detailed Report"):
                 for i, item in enumerate(state["history"]):
                     icon = "✅" if item["correct"] else "❌"
                     st.markdown(f"**Q{i+1}** {icon}")
                     st.text(item["question"])
                     st.caption(f"Your Answer: {item['answer']}")
                     st.info(f"Feedback: {item['feedback']}")
    
    # --- 📊 ANALYTICS TAB ---
    with tab_analytics:
        st.subheader("Student Analytics Report")
        
        if st.button("Generate Analytics Report"):
            with st.spinner("Analyzing performance..."):
                try:
                    res = api_client.get_analytics(
                        student_id=st.session_state["student_id"],
                        subject_id=st.session_state["subject_id"] # Added subject_id
                    )
                    
                    # API returns wrapper: {student_id, analytics: {...}, explanation: ...}
                    data = res["analytics"]
                    explanation = res["explanation"]
                    
                    # 1. Key Metrics
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Overall Progress", f"{data.get('overall_progress', 0)*100:.0f}%")
                    col2.metric("Avg Score", f"{data.get('average_score', 0)*100:.0f}%")
                    col3.metric("Modules Completed", data.get('completed_modules', 0))
                    # col4.metric("Hard Qs Aced", data.get("hard_questions_attempts", 0))
    
                    # 2. Module Performance Chart
                    st.subheader("Module Performance")
                    breakdown = data.get("module_breakdown", [])
                    if breakdown:
                        import pandas as pd
                        df = pd.DataFrame(breakdown)
                        if not df.empty:
                             # Clean up for chart
                            # Use module_name if available, else module_id
                            if "module_name" in df.columns:
                                chart_data = df[["module_name", "score"]].set_index("module_name")
                            else:
                                chart_data = df[["module_id", "score"]].set_index("module_id")
                            st.bar_chart(chart_data)
                    
                    # # 3. Weak Areas
                    # weakness_map = data.get("weak_areas_map", {})
                    # if weakness_map:
                    #     st.subheader("Top Weak Areas (by frequency)")
                    #     # Convert map to DataFrame for chart
                    #     import pandas as pd
                        
                    #     rows = []
                    #     for tid, info in weakness_map.items():
                    #          # Use Name if resolved
                    #          rows.append({"Topic": info.get("name", tid), "Incorrect Answers": info.get("count", 0)})
                            
                    #     if rows:
                    #         df_weak = pd.DataFrame(rows).sort_values("Incorrect Answers", ascending=True)
                    #         st.bar_chart(df_weak.set_index("Topic"))
                    
                    # # Fallback (Legacy)
                    # elif data.get("weak_areas"):
                    #     st.error(f"⚠️ Focus Areas: {', '.join(data.get('weak_areas'))}")
                    
                    # 4. Agent Insight
                    with st.expander("📝 Deeper Analysis", expanded=True):
                        st.write(explanation)
                        
                except Exception as e:
                    st.error(f"Failed to fetch analytics: {e}")

if __name__ == "__main__":
    st.set_page_config(page_title="Student Agent System", layout="wide")
    main()
