import streamlit as st
import sys
import os

# -----------------------------------------------------------------------------
# PATH SETUP
# -----------------------------------------------------------------------------
# Ensure project root is in sys.path
# This allows imports like 'import Student...' and 'import Teacher...'
def setup_path():
    # Robustly get the directory of THIS file (ui/app.py)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go one level up to get project root
    root_dir = os.path.dirname(current_dir)
    
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
        print(f"✅ Added root to sys.path: {root_dir}")
    else:
        print(f"ℹ️ Root already in sys.path: {root_dir}")

    # Debug: Print sys.path to logs
    print(f"📂 Current Working Directory: {os.getcwd()}")
    print("PYTHONPATH:", sys.path)

setup_path()

# -----------------------------------------------------------------------------
# APP
# -----------------------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="Academic Agent System",
        page_icon="🎓",
        layout="wide"
    )
    
    st.sidebar.title("Navigation")
    role = st.sidebar.radio("Select Role", ["🏠 Home", "👨‍🎓 Student", "👩‍🏫 Teacher"])
    
    if role == "🏠 Home":
        st.title("🎓 Academic Agent System")
        st.markdown("""
        ### Welcome to the Academic Agent System
        
        Please select your role from the sidebar to continue:
        
        - **👨‍🎓 Student**: Access your learning path, chat with AI tutors, and take assessments.
        - **👩‍🏫 Teacher**: Design structured lesson plans, control learning depth, and generate aligned assessments for your class.
        """)
        
    elif role == "👨‍🎓 Student":
        try:
            import Student.ui.streamlit_app as student_app
            student_app.main()
        except ModuleNotFoundError as e:
            st.error(f"Failed to load Student module: {e}")
            st.code(f"Sys Path: {sys.path}")
        
    elif role == "👩‍🏫 Teacher":
        try:
            import Teacher.ui as teacher_app
            teacher_app.main()
        except ModuleNotFoundError as e:
            st.error(f"Failed to load Teacher module: {e}")
            st.code(f"Sys Path: {sys.path}")

if __name__ == "__main__":
    main()
