import streamlit as st
from backend import (
    answer_query,
    get_available_sections,
    get_assignment_questions,
    save_student,
    save_answer,
    save_chat,
    get_all_students,
    get_answers_by_email,
    save_grade,
    get_grades_by_email,
    get_latest_grade,
    get_all_submissions,
    get_chats_by_email,
    set_config,
)
import pandas as pd
import os
import time

st.set_page_config(page_title="Supply Chain Learning", layout="wide")

# --- Configuration Setup ---
def setup_config():
    """Setup configuration from Streamlit secrets or environment variables"""
    try:
        # Try to get from Streamlit secrets first (production)
        if hasattr(st, 'secrets') and 'OPENAI_API_KEY' in st.secrets:
            openai_key = st.secrets['OPENAI_API_KEY']
            admin_pw = st.secrets.get('ADMIN_PW', 'admin123')
            max_queries = st.secrets.get('MAX_QUERIES_PER_HOUR', 10)
            max_tokens = st.secrets.get('MAX_TOKENS_PER_DAY', 5000)
        else:
            # Fallback to environment variables (development)
            openai_key = os.getenv('OPENAI_API_KEY')
            admin_pw = os.getenv('ADMIN_PW', 'admin123')
            max_queries = int(os.getenv('MAX_QUERIES_PER_HOUR', '10'))
            max_tokens = int(os.getenv('MAX_TOKENS_PER_DAY', '5000'))
        
        if not openai_key:
            st.error("OpenAI API key not configured. Please set up Streamlit secrets or environment variables.")
            st.stop()
        
        # Configure backend
        set_config(openai_key, admin_pw, max_queries, max_tokens)
        
    except Exception as e:
        st.error(f"Configuration error: {e}")
        st.stop()

# Setup configuration on app start
setup_config()

# --- WHU theme CSS and banner (brand color updated) ---
st.markdown(
    """
    <style>
    :root { --whu-primary: rgb(5,70,150); --whu-secondary: #f6f6f6; --whu-accent: #FFC20E; }
        /* hide Streamlit header */
        header {visibility: hidden;}
        .top-band {background:var(--whu-primary); color:white; padding:14px 22px; border-radius:6px; margin-bottom:12px}
    .course-band {background: linear-gradient(90deg, var(--whu-primary), rgba(5,70,150,0.8)); color:white; padding:8px 12px; border-radius:6px; font-weight:600; display:inline-block}
        .card {background:white; padding:16px; border-radius:8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom:12px}
        .small-muted {color:#666; font-size:13px}
    .stButton>button { background-color: var(--whu-primary) !important; color: white !important; border-radius:6px; }
        .streamlit-expanderHeader { font-weight:600 }
        </style>
        """,
        unsafe_allow_html=True,
)

st.markdown(
        """
        <div class="top-band">
            <div style="display:flex;align-items:center;justify-content:space-between;">
                <div style="font-size:20px;font-weight:700">Logistik 2025 — Supply Chain Learning</div>
                <div style="font-size:14px;opacity:0.95">WHU</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
)

# --- Navigation State ---
if 'info_complete' not in st.session_state:
    st.session_state['info_complete'] = False
if 'student_name' not in st.session_state:
    st.session_state['student_name'] = ""
if 'student_email' not in st.session_state:
    st.session_state['student_email'] = ""
if 'admin_login_mode' not in st.session_state:
    st.session_state['admin_login_mode'] = False
if 'admin_logged_in' not in st.session_state:
    st.session_state['admin_logged_in'] = False
if 'admin_login_time' not in st.session_state:
    st.session_state['admin_login_time'] = None

# Check admin session timeout (30 minutes)
if st.session_state.get('admin_logged_in') and st.session_state.get('admin_login_time'):
    if time.time() - st.session_state['admin_login_time'] > 1800:  # 30 minutes
        st.session_state['admin_logged_in'] = False
        st.session_state['admin_login_time'] = None
        st.warning("Admin session expired. Please log in again.")

# --- Sidebar Admin Login/Logout ---
with st.sidebar:
    st.sidebar.header("Administration")
    if st.session_state.get('admin_logged_in'):
        st.success("Admin logged in")
        remaining_time = 30 - (time.time() - st.session_state.get('admin_login_time', 0)) / 60
        if remaining_time > 0:
            st.caption(f"Session expires in {remaining_time:.0f} minutes")
        if st.button("Logout"):
            st.session_state['admin_logged_in'] = False
            st.session_state['admin_login_time'] = None
            st.success("Successfully logged out")
            st.rerun()
    else:
        if not st.session_state.get('admin_login_mode'):
            if st.button("Admin Login"):
                st.session_state['admin_login_mode'] = True
                st.rerun()
        else:
            pw = st.text_input("Admin password:", type="password", key="sidebar_admin_pw")
            if st.button("Login", key="sidebar_login_button"):
                # Get admin password from configuration
                admin_pw = None
                try:
                    if hasattr(st, 'secrets') and 'ADMIN_PW' in st.secrets:
                        admin_pw = st.secrets['ADMIN_PW']
                    else:
                        admin_pw = os.getenv("ADMIN_PW", "admin123")
                except Exception:
                    admin_pw = os.getenv("ADMIN_PW", "admin123")
                
                if pw and admin_pw and pw == admin_pw:
                    st.session_state['admin_logged_in'] = True
                    st.session_state['admin_login_mode'] = False
                    st.session_state['admin_login_time'] = time.time()
                    st.success("Successfully logged in as admin")
                    st.rerun()
                else:
                    st.error("Invalid admin password")
                    time.sleep(1)  # Prevent brute force attempts
            if st.button("Cancel", key="sidebar_admin_cancel"):
                st.session_state['admin_login_mode'] = False
                st.rerun()

# --- Student Info Page ---
def student_info_page():
    st.title("Supply Chain Learning")
    st.header("Student Information")
    name = st.text_input("Enter your name:", value=st.session_state['student_name'], key="student_name_input")
    email = st.text_input("Enter your email:", value=st.session_state['student_email'], key="student_email_input")
    submit = st.button("Submit")
    if submit:
        st.session_state['student_name'] = name
        st.session_state['student_email'] = email
        email_clean = email.strip().lower()
        if name and email_clean.endswith("@whu.edu"):
            st.session_state['info_complete'] = True
            # persist student
            save_student(name, email_clean)
            st.rerun()
        else:
            st.session_state['info_complete'] = False
            st.warning("Please enter your name and a valid WHU email (ending with @whu.edu) to start the assignment.")

    st.markdown("---")

# --- Assignment Page ---
def assignment_page():
    st.title("Supply Chain Learning")
    st.markdown("---")
    # Section selector (Chapter / Case study)
    sections = get_available_sections()
    if 'selected_section' not in st.session_state:
        st.session_state['selected_section'] = sections[0] if sections else "Ch.3"
    selected_section = st.selectbox("Select section:", options=sections, index=sections.index(st.session_state['selected_section']) if st.session_state['selected_section'] in sections else 0)
    st.session_state['selected_section'] = selected_section
    st.caption(f"Current section: {selected_section}")
    st.header("Assignment")
    # Load questions for the selected section
    questions = get_assignment_questions(selected_section)
    # If section changed since last visit, reset question index and clear chat
    if st.session_state.get('last_section') != selected_section:
        st.session_state['question_idx'] = 0
        st.session_state['last_section'] = selected_section
        # Clear chat history when changing sections
        st.session_state['chat_history'] = []
        st.session_state['user_question'] = ""
    # tell backend which section we're working with (used for DB queries)
    import backend as _backend
    _backend.save_answer.current_section = selected_section
    _backend.save_chat.current_section = selected_section
    _backend.save_grade.current_section = selected_section
    _backend.get_answers_by_email.current_section = selected_section
    _backend.get_chats_by_email.current_section = selected_section
    _backend.get_grades_by_email.current_section = selected_section
    _backend.get_latest_grade.current_section = selected_section
    if 'question_idx' not in st.session_state:
        st.session_state['question_idx'] = 0
    num_questions = len(questions)
    current_idx = st.session_state['question_idx']
    assignment_context = questions[current_idx] if questions else ""
    st.write(f"**Q{current_idx+1}:** {assignment_context}")
    # --- Auto-validation for 7-Eleven numeric tasks (only show on Part 2) ---
    if st.session_state.get('selected_section') == '7-Eleven Case 2015' and current_idx == 1:
        # For Part 2 of 7-Eleven case, we use specific numeric inputs instead of the general text area
        st.info("**Part 2 - Quantitative Analysis**: Use the numeric validation tools below instead of the text area.")
        
        with st.expander("Auto-validate numeric tasks (Part 2)", expanded=True):
            st.write("Enter your numeric answers below for automatic checking.")
            
            # Validation status indicators
            col_status1, col_status2 = st.columns(2)
            with col_status1:
                if st.session_state.get('auto_2_1_pass', False):
                    st.success("Task 2.1 - Validated")
                else:
                    st.warning("Task 2.1 - Pending validation")
            with col_status2:
                if st.session_state.get('auto_2_2_pass', False):
                    st.success("Task 2.2 - Validated")
                else:
                    st.warning("Task 2.2 - Pending validation")
            
            st.markdown("---")
            
            # Task 2.1 – DC Utilization
            val_2_1 = st.number_input("Task 2.1 - Average stores per DC", value=0.0, format="%.2f", key="auto_2_1")
            if st.button("Check Task 2.1"):
                expected_2_1 = 16000 / 158
                tol_2_1 = 2
                diff = abs(val_2_1 - expected_2_1)
                passed = diff <= tol_2_1
                if passed:
                    st.success(f"Task 2.1 OK — your {val_2_1:.2f} is within ±{tol_2_1} of the expected range.")
                    st.session_state['auto_2_1_pass'] = True
                else:
                    # Provide a hint without revealing the expected value
                    st.info("Hint: compute average stores per DC by dividing total stores by number of DCs (i.e. total stores ÷ DCs). Check your division and rounding.")
                # save numeric answer as text for this question
                save_answer(st.session_state.get('student_email', ''), current_idx, f"2.1:{val_2_1:.2f} -> {'PASS' if passed else 'FAIL'}")

            # Task 2.2 – Daily Delivery Cost per Store (Japan vs US)
            st.write("Task 2.2 - Enter Japan cost per store/day and US cost per store/day")
            val_japan = st.number_input("Japan cost (¥)", value=0.0, format="%.2f", key="auto_2_2_japan")
            val_us = st.number_input("US cost (¥)", value=0.0, format="%.2f", key="auto_2_2_us")
            if st.button("Check Task 2.2"):
                expected_japan = (50000 / 10) * 3
                expected_us = (60000 / 8) * 1
                expected_diff = expected_japan - expected_us
                tol_yen = 500
                diff_j = abs(val_japan - expected_japan)
                diff_u = abs(val_us - expected_us)
                diff_diff = abs((val_japan - val_us) - expected_diff)
                passed = (diff_j <= tol_yen) and (diff_u <= tol_yen) and (diff_diff <= tol_yen)
                if passed:
                    st.success("Task 2.2 OK — your values are within the acceptable tolerance.")
                    st.session_state['auto_2_2_pass'] = True
                else:
                    # Provide step hints without revealing exact expected numbers
                    st.info("Hint: For each country compute (cost per truck ÷ stores per truck) × deliveries per store/day to get the per-store/day cost, then compare the two results. Check your arithmetic and units.")
                save_answer(st.session_state.get('student_email', ''), current_idx, f"2.2: Japan {val_japan:.2f}, US {val_us:.2f} -> {'PASS' if passed else 'FAIL'}")
    else:
        # For all other questions, show the regular text area
        answer_box = st.text_area(f"Your answer to Q{current_idx+1}", key=f"ans_{current_idx}")
    if st.button("Submit Answer"):
        # save current answer to DB
        save_answer(st.session_state.get('student_email', ''), current_idx, st.session_state.get(f"ans_{current_idx}", ""))
        st.success("Answer saved.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Previous"):
            if current_idx > 0:
                st.session_state['question_idx'] -= 1
                # Clear chat history when moving to new question
                st.session_state['chat_history'] = []
                st.session_state['user_question'] = ""
                st.rerun()
    with col2:
        if current_idx < num_questions - 1:
            # Check if we can proceed (for 7-Eleven Part 2 validation)
            can_proceed = True
            if st.session_state.get('selected_section') == '7-Eleven Case 2015' and current_idx == 1:
                auto_ok = st.session_state.get('auto_2_1_pass', False) and st.session_state.get('auto_2_2_pass', False)
                if not auto_ok:
                    can_proceed = False
            
            # Show Next button with appropriate behavior
            if can_proceed:
                if st.button("Next"):
                    # save current answer before moving on
                    save_answer(st.session_state.get('student_email', ''), current_idx, st.session_state.get(f"ans_{current_idx}", ""))
                    st.session_state['question_idx'] += 1
                    # Clear chat history when moving to new question
                    st.session_state['chat_history'] = []
                    st.session_state['user_question'] = ""
                    st.rerun()
            else:
                # Show disabled-style button with warning
                if st.button("Next (Validation Required)", disabled=False, help="Complete numeric validation first"):
                    st.error('**Validation Required**: You must pass the numeric auto-validation for Tasks 2.1 and 2.2 before proceeding to the next question.')
                    st.info('**Tip**: Scroll up to the "Auto-validate numeric tasks" section and complete both Task 2.1 and Task 2.2 validations.')
        else:
            # Last question - show final submit button instead of completion message
            if st.button("Submit Final Assignment", type="primary"):
                # Save current answer
                save_answer(st.session_state.get('student_email', ''), current_idx, st.session_state.get(f"ans_{current_idx}", ""))
                
                st.success(" **Assignment Submitted Successfully!**")
                st.balloons()
                st.info("**What's next:**\n- Review your answers using the Previous button\n- Use the chatbot for any final questions\n- End your session using the logout button below")
                
                # Optional: Mark assignment as completed
                st.session_state[f'assignment_completed_{st.session_state.get("selected_section", "Ch.3")}'] = True
            
            
    st.info("Use the chatbot in the sidebar to get help with assignment questions!")
    
    st.markdown("---")
    
    # --- Student Session Section (moved from sidebar) ---
    st.header("Student Session")
    if st.session_state.get('student_name') and st.session_state.get('student_email'):
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"Logged in as: {st.session_state['student_name']}")
            st.caption(f"Email: {st.session_state['student_email']}")
        
        with col2:
            # Show current progress
            if 'question_idx' in st.session_state and 'selected_section' in st.session_state:
                questions = get_assignment_questions(st.session_state['selected_section'])
                progress = min(st.session_state['question_idx'] + 1, len(questions))
                st.info(f"Progress: {progress}/{len(questions)} questions")
        
        # Assignment completion status
        if st.session_state.get('question_idx', 0) >= len(get_assignment_questions(st.session_state.get('selected_section', 'Ch.3'))):
            st.success("Assignment completed!")
            st.balloons()
        
        # Logout button
        if st.button("End Session & Logout", type="primary"):
            # Clear student session data
            st.session_state['info_complete'] = False
            st.session_state['student_name'] = ""
            st.session_state['student_email'] = ""
            st.session_state['question_idx'] = 0
            st.session_state['chat_history'] = []
            st.session_state['user_question'] = ""
            
            # Clear any cached answers
            for key in list(st.session_state.keys()):
                if key.startswith('ans_'):
                    del st.session_state[key]
            
            st.success("Successfully logged out!")
            st.balloons()
            time.sleep(1)
            st.rerun()
    
    # --- Chatbot Section (in sidebar) ---
    st.sidebar.header("Course Chatbot")
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []
    if 'user_question' not in st.session_state:
        st.session_state['user_question'] = ""
    user_question = st.sidebar.text_area(
        "Ask a question about the current assignment question or course PDF:",
        value=st.session_state['user_question'],
        key="chat_input_unique"
    )
    if st.sidebar.button("Send"):
        if user_question:
            answer = answer_query(
                user_question, 
                assignment_context, 
                section=st.session_state.get('selected_section', 'Ch.3'),
                user_email=st.session_state.get('student_email', '')
            )
            st.session_state['chat_history'].insert(0, (user_question, answer))  # Add to top
            # persist chat
            save_chat(st.session_state.get('student_email', ''), user_question, answer)
            st.session_state['user_question'] = ""  # Clear input immediately
            st.rerun()
        else:
            st.sidebar.write("Please enter a question.")
    st.sidebar.markdown("---")
    st.sidebar.subheader("Chat History")
    for q, a in st.session_state['chat_history']:
        st.sidebar.markdown(f"**You:** {q}")
        st.sidebar.markdown(f"**Bot:** {a}")
# --- Admin Page ---
def admin_page():
    st.title("Admin - System Monitoring & Grading")
    st.markdown("---")
    
    # Monitoring Dashboard
    col1, col2, col3 = st.columns(3)
    
    with col1:
        students = get_all_students()
        st.metric("Total Students", len(students))
    
    with col2:
        submissions = get_all_submissions()
        st.metric("Total Submissions", len(submissions))
    
    with col3:
        chats = []
        for student_email, _, _ in students:
            chats.extend(get_chats_by_email(student_email))
        st.metric("Total Chat Interactions", len(chats))
    
    # Rate limiting status
    st.subheader("Rate Limiting Status")
    from backend import _user_queries
    active_users = len([email for email in _user_queries.keys() if _user_queries[email]])
    st.info(f"Active users with query history: {active_users}")
    
    # Recent activity
    st.subheader("Recent Activity")
    if submissions:
        recent_submissions = sorted(submissions, key=lambda x: x[4], reverse=True)[:10]
        df_recent = pd.DataFrame(recent_submissions, 
                               columns=['Email', 'Question', 'Answer', 'Section', 'Submitted'])
        st.dataframe(df_recent, use_container_width=True)
    
    st.markdown("---")
    
    # Manual Grading Interface
    st.header("Manual Grading Interface")
    
    # Tabs for different grading views
    tab1, tab2, tab3 = st.tabs(["Grade by Student", " Grade Overview", "Section Statistics"])
    
    with tab1:
        st.subheader("Grade Individual Student Submissions")
        
        # Student selection
        students = get_all_students()
        if not students:
            st.info("No students have registered yet.")
        else:
            student_options = [f"{name} ({email})" for email, name, _ in students]
            selected_student = st.selectbox("Select a student to grade:", [""] + student_options)
            
            if selected_student:
                # Extract email from selection
                student_email = selected_student.split("(")[1].split(")")[0]
                student_name = selected_student.split(" (")[0]
                
                st.markdown(f"**Grading submissions for:** {student_name} ({student_email})")
                
                # Section filter
                sections = get_available_sections()
                selected_section = st.selectbox("Filter by section:", ["All Sections"] + sections, key="grade_section")
                
                # Get answers for this student
                answers = get_answers_by_email(student_email)
                
                if not answers:
                    st.info("This student has not submitted any answers yet.")
                else:
                    # Group answers by question index and get latest submission only
                    questions_data = {}
                    for qidx, ans, submitted_at in answers:
                        if qidx not in questions_data:
                            questions_data[qidx] = (ans, submitted_at)
                        else:
                            # Keep the latest submission (assuming newer submissions have later timestamps)
                            current_time = questions_data[qidx][1]
                            if submitted_at > current_time:
                                questions_data[qidx] = (ans, submitted_at)
                    
                    # Display each question for grading (latest submission only)
                    for qidx in sorted(questions_data.keys()):
                        ans, submitted_at = questions_data[qidx]
                        
                        with st.expander(f"Question {qidx + 1} (Latest Submission)", expanded=False):
                            # Show question text
                            questions = get_assignment_questions(selected_section if selected_section != "All Sections" else "Ch.3")
                            if qidx < len(questions):
                                st.markdown("**Question:**")
                                st.info(questions[qidx][:200] + "..." if len(questions[qidx]) > 200 else questions[qidx])
                            
                            # Show latest submission only
                            st.markdown(f"**Latest Submission (submitted: {submitted_at}):**")
                            st.text_area("Student Answer:", value=ans, height=100, disabled=True, key=f"ans_display_{qidx}_latest")
                            
                            # Current grade
                            current_grade = get_latest_grade(student_email, qidx)
                            
                            # Grading interface
                            col1, col2, col3 = st.columns([2, 1, 1])
                            
                            with col1:
                                grade_options = ["", "A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "F", "Pass", "Fail", "Incomplete"]
                                current_idx = grade_options.index(current_grade) if current_grade in grade_options else 0
                                new_grade = st.selectbox(
                                    "Grade:", 
                                    options=grade_options,
                                    index=current_idx,
                                    key=f"grade_select_{student_email}_{qidx}_latest"
                                )
                            
                            with col2:
                                if st.button(f"Save Grade", key=f"save_grade_{student_email}_{qidx}_latest"):
                                    if new_grade:
                                        save_grade(student_email, qidx, new_grade)
                                        st.success("Grade saved!")
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.warning("Please select a grade first.")
                            
                            with col3:
                                if current_grade:
                                    st.metric("Current Grade", current_grade)
                                else:
                                    st.info("No grade yet")
    
    with tab2:
        st.subheader("Grading Overview")
        
        # Section filter for overview
        overview_section = st.selectbox("View grades for section:", ["All Sections"] + get_available_sections(), key="overview_section")
        
        # Create grading overview table
        students = get_all_students()
        if students:
            grading_data = []
            
            for email, name, _ in students:
                answers = get_answers_by_email(email)
                student_row = {"Name": name, "Email": email}
                
                # Get unique question indices
                question_indices = set()
                for qidx, _, _ in answers:
                    question_indices.add(qidx)
                
                # For each question, get the latest grade
                for qidx in sorted(question_indices):
                    grade = get_latest_grade(email, qidx)
                    student_row[f"Q{qidx + 1}"] = grade if grade else "Not Graded"
                
                grading_data.append(student_row)
            
            if grading_data:
                df_grades = pd.DataFrame(grading_data)
                st.dataframe(df_grades, use_container_width=True)
                
                # Export grades
                if st.button("Export Grades as CSV"):
                    csv = df_grades.to_csv(index=False)
                    st.download_button(
                        label="Download Grades CSV",
                        data=csv,
                        file_name=f"grades_{overview_section.replace(' ', '_')}.csv",
                        mime="text/csv"
                    )
            else:
                st.info("No graded submissions found.")
        else:
            st.info("No students registered yet.")
    
    with tab3:
        st.subheader("Section Statistics")
        
        # Statistics for each section
        sections = get_available_sections()
        
        for section in sections:
            with st.expander(f"{section} Statistics"):
                students = get_all_students()
                section_stats = {
                    "total_students": len(students),
                    "students_with_submissions": 0,
                    "total_submissions": 0,
                    "graded_submissions": 0,
                    "grade_distribution": {}
                }
                
                for email, name, _ in students:
                    answers = get_answers_by_email(email)
                    if answers:
                        section_stats["students_with_submissions"] += 1
                        section_stats["total_submissions"] += len(answers)
                        
                        # Count graded submissions
                        for qidx, _, _ in answers:
                            grade = get_latest_grade(email, qidx)
                            if grade:
                                section_stats["graded_submissions"] += 1
                                if grade in section_stats["grade_distribution"]:
                                    section_stats["grade_distribution"][grade] += 1
                                else:
                                    section_stats["grade_distribution"][grade] = 1
                
                # Display statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Students", section_stats["total_students"])
                with col2:
                    st.metric("Students with Submissions", section_stats["students_with_submissions"])
                with col3:
                    st.metric("Total Submissions", section_stats["total_submissions"])
                
                col4, col5 = st.columns(2)
                with col4:
                    st.metric("Graded Submissions", section_stats["graded_submissions"])
                with col5:
                    if section_stats["total_submissions"] > 0:
                        grading_progress = (section_stats["graded_submissions"] / section_stats["total_submissions"]) * 100
                        st.metric("Grading Progress", f"{grading_progress:.1f}%")
                
                # Grade distribution
                if section_stats["grade_distribution"]:
                    st.markdown("**Grade Distribution:**")
                    grade_df = pd.DataFrame(list(section_stats["grade_distribution"].items()), 
                                          columns=["Grade", "Count"])
                    st.bar_chart(grade_df.set_index("Grade"))
    
    st.markdown("---")
    
    # Export all data as CSV
    import io, csv, json
    section = st.selectbox("Select section to export:", options=["All"] + get_available_sections())
    if st.button("Export all data to CSV"):
        students = get_all_students()
        student_map = {s[0].strip().lower(): s[1] for s in students}
        submissions = get_all_submissions()  # list of (email, question_idx, answer, submitted_at)
        # Build CSV rows
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["email", "name", "question_idx", "answer", "answer_submitted_at", "latest_grade", "grade_graded_at", "chat_history_json"])
        for email, qidx, ans, sec, submitted_at in submissions:
            email_clean = email.strip().lower()
            name = student_map.get(email_clean, "")
            # latest grade for this question
            # only include grades for the chosen section (if any)
            if section != "All" and sec != section:
                continue
            latest = get_latest_grade(email_clean, qidx)
            grade_row = None
            if latest:
                grade_row = latest
                # we don't have graded_at from get_latest_grade; fetch all grades for email
                grades = get_grades_by_email(email_clean)
                grade_time = ""
                for g_qidx, g_val, g_time in grades:
                    if g_qidx == qidx and g_val == latest:
                        grade_time = g_time
                        break
            else:
                grade_row = ""
                grade_time = ""
            # chat history aggregated
            # fetch chat history for the selected section
            _import_backend = __import__('backend')
            _import_backend.get_chats_by_email.current_section = section if section != "All" else 'Ch.3'
            chats = get_chats_by_email(email_clean)
            chat_list = []
            for q_text, bot_resp, created_at in chats:
                chat_list.append({"q": q_text, "bot": bot_resp, "at": created_at})
            chat_json = json.dumps(chat_list, ensure_ascii=False)
            writer.writerow([email_clean, name, qidx, ans, submitted_at, grade_row, grade_time, chat_json])
        data = buf.getvalue()
        buf.close()
        st.download_button("Download CSV", data=data, file_name="submissions_export.csv", mime="text/csv")
    
    st.markdown("---")
    st.header("Quick Student Lookup")
    st.info("**Tip**: Use the 'Manual Grading Interface' tabs above for comprehensive grading features.")
    
    # Quick lookup for student data
    students = get_all_students()
    emails = [s[0] for s in students]
    selected = st.selectbox("Quick lookup - Select student email:", options=[""] + emails, key="quick_lookup")
    
    if selected:
        # Find student name
        student_name = next((name for email, name, _ in students if email == selected), "Unknown")
        st.subheader(f"Quick View: {student_name} ({selected})")
        
        # Show summary
        answers = get_answers_by_email(selected)
        chats = get_chats_by_email(selected)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Submissions", len(answers))
        with col2:
            graded_count = sum(1 for qidx, _, _ in answers if get_latest_grade(selected, qidx))
            st.metric("Graded", graded_count)
        with col3:
            st.metric("Chat Messages", len(chats))
        
        # Recent submissions preview
        if answers:
            st.markdown("**Recent Submissions (preview):**")
            recent_answers = sorted(answers, key=lambda x: x[2], reverse=True)[:3]
            for qidx, ans, submitted_at in recent_answers:
                grade = get_latest_grade(selected, qidx)
                grade_display = f" - Grade: {grade}" if grade else " - Not graded"
                st.markdown(f"• **Q{qidx+1}** ({submitted_at}){grade_display}")
                st.text(ans[:100] + "..." if len(ans) > 100 else ans)
        
        # Chat history preview
        if chats:
            st.markdown("**Recent Chat (preview):**")
            recent_chats = sorted(chats, key=lambda x: x[2], reverse=True)[:2]
            for q, bot_resp, created_at in recent_chats:
                st.markdown(f"*{created_at}* - **Student:** {q[:80]}{'...' if len(q) > 80 else ''}")
                st.markdown(f"**Bot:** {bot_resp[:80]}{'...' if len(bot_resp) > 80 else ''}")
        
        st.info("For detailed grading, use the 'Grade by Student' tab above.")


# --- Main App Flow ---
if st.session_state.get('admin_logged_in'):
    admin_page()
else:
    if not st.session_state['info_complete']:
        student_info_page()
        st.stop()
    else:
        assignment_page()
