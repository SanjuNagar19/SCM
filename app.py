import streamlit as st
from backend import (
    answer_query,
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
)
import os

st.set_page_config(page_title="Supply Chain Learning System", layout="wide")

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

# --- Sidebar Admin Login/Logout ---
with st.sidebar:
    st.sidebar.header("Administration")
    if st.session_state.get('admin_logged_in'):
        if st.button("Logout"):
            st.session_state['admin_logged_in'] = False
            st.rerun()
    else:
        if not st.session_state.get('admin_login_mode'):
            if st.button("Admin Login"):
                st.session_state['admin_login_mode'] = True
                st.rerun()
        else:
            pw = st.text_input("Admin password:", type="password", key="sidebar_admin_pw")
            if st.button("Login", key="sidebar_login_button"):
                admin_pw = os.getenv("ADMIN_PW")
                try:
                    secret_pw = st.secrets.get("ADMIN_PW") if hasattr(st, 'secrets') else None
                except Exception:
                    secret_pw = None
                if not admin_pw and secret_pw:
                    admin_pw = secret_pw
                if pw and admin_pw and pw == admin_pw:
                    st.session_state['admin_logged_in'] = True
                    st.session_state['admin_login_mode'] = False
                    st.rerun()
                else:
                    st.error("Invalid admin password")
            if st.button("Cancel", key="sidebar_admin_cancel"):
                st.session_state['admin_login_mode'] = False
                st.rerun()

# --- Student Info Page ---
def student_info_page():
    st.title("Supply Chain Learning System")
    st.header("Student Information")
    name = st.text_input("Enter your name:", value=st.session_state['student_name'], key="student_name_input")
    email = st.text_input("Enter your email:", value=st.session_state['student_email'], key="student_email_input")
    submit = st.button("Submit")
    if submit:
        st.session_state['student_name'] = name
        st.session_state['student_email'] = email
        email_clean = email.strip().lower()
        if name and email_clean.endswith(".whu.edu"):
            st.session_state['info_complete'] = True
            # persist student
            save_student(name, email_clean)
            st.rerun()
        else:
            st.session_state['info_complete'] = False
            st.warning("Please enter your name and a valid WHU email (ending with .whu.edu) to start the assignment.")

    st.markdown("---")

# --- Assignment Page ---
def assignment_page():
    st.title("Supply Chain Learning System")
    st.markdown("---")
    st.header("Assignment")
    questions = get_assignment_questions()
    if 'question_idx' not in st.session_state:
        st.session_state['question_idx'] = 0
    num_questions = len(questions)
    current_idx = st.session_state['question_idx']
    assignment_context = questions[current_idx] if questions else ""
    st.write(f"**Q{current_idx+1}:** {assignment_context}")
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
                st.rerun()
    with col2:
        if st.button("Next"):
            if current_idx < num_questions - 1:
                # save current answer before moving on
                save_answer(st.session_state.get('student_email', ''), current_idx, st.session_state.get(f"ans_{current_idx}", ""))
                st.session_state['question_idx'] += 1
                st.rerun()
    st.info("Use the chatbot in the sidebar to get help with assignment questions!")
    # --- Chatbot Section ---
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
            answer = answer_query(user_question, assignment_context)
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
    st.title("Admin - Submissions & Grading")
    st.markdown("---")
    # Export all data as CSV
    import io, csv, json
    if st.button("Export all data to CSV"):
        students = get_all_students()
        student_map = {s[0].strip().lower(): s[1] for s in students}
        submissions = get_all_submissions()  # list of (email, question_idx, answer, submitted_at)
        # Build CSV rows
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["email", "name", "question_idx", "answer", "answer_submitted_at", "latest_grade", "grade_graded_at", "chat_history_json"])
        for email, qidx, ans, submitted_at in submissions:
            email_clean = email.strip().lower()
            name = student_map.get(email_clean, "")
            # latest grade for this question
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
    # Admin UI assumes admin_logged_in is already True
    students = get_all_students()
    emails = [s[0] for s in students]
    selected = st.selectbox("Select student email:", options=[""] + emails)
    if selected:
        st.subheader(f"Submissions for {selected}")
        answers = get_answers_by_email(selected)
        # show each submission; use submitted_at in key to avoid duplicate keys
        for qidx, ans, submitted_at in answers:
            st.markdown(f"**Q{qidx+1} (submitted {submitted_at}):**")
            st.write(ans)
            # sanitize timestamp for key
            ts_key = submitted_at.replace(' ', '_').replace(':', '-').replace('.', '-') if submitted_at else str(qidx)
            current_grade = get_latest_grade(selected, qidx)
            grade_key = f"grade_{selected}_{qidx}_{ts_key}"
            new_grade = st.text_input(f"Grade for Q{qidx+1}", value=current_grade or "", key=grade_key)
            save_key = f"save_{selected}_{qidx}_{ts_key}"
            if st.button(f"Save Grade Q{qidx+1}", key=save_key):
                save_grade(selected, qidx, new_grade)
                st.success("Grade saved")

        # Chat history for this student
        st.markdown("---")
        st.subheader("Chat History")
        chats = get_chats_by_email(selected)
        if chats:
            for q, bot_resp, created_at in chats:
                st.markdown(f"*{created_at}* - **Student:** {q}")
                st.markdown(f"**Bot:** {bot_resp}")
        else:
            st.write("No chat history for this student.")


# --- Main App Flow ---
if st.session_state.get('admin_logged_in'):
    admin_page()
else:
    if not st.session_state['info_complete']:
        student_info_page()
        st.stop()
    else:
        assignment_page()
