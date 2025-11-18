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
    clear_rate_limits,
    get_rate_limit_status,
    # Module-specific functions
    validate_numeric_answer,
    assign_scenario,
    get_disruption_scenarios,
    calculate_volume_metrics,
    calculate_transport_costs,
    collect_phase2_inputs,
    # Section management
    set_current_section,
)
import pandas as pd
import os
import time
import hashlib
import hmac
import secrets
import logging

# Setup logging
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Supply Chain Learning", layout="wide")

# --- Security Functions ---
# Admin login attempt tracking for rate limiting
if 'admin_login_attempts' not in st.session_state:
    st.session_state['admin_login_attempts'] = {}
if 'admin_session_token' not in st.session_state:
    st.session_state['admin_session_token'] = None

def check_admin_rate_limit(client_id="default"):
    """Check admin login rate limiting (prevent brute force)"""
    current_time = time.time()
    attempts = st.session_state['admin_login_attempts'].get(client_id, [])
    
    # Remove attempts older than 15 minutes
    recent_attempts = [t for t in attempts if current_time - t < 900]
    st.session_state['admin_login_attempts'][client_id] = recent_attempts
    
    # Allow max 5 attempts per 15 minutes
    if len(recent_attempts) >= 5:
        return False, f"Too many login attempts. Please wait {int(900 - (current_time - min(recent_attempts)))} seconds."
    
    return True, ""

def record_admin_attempt(client_id="default"):
    """Record an admin login attempt"""
    if client_id not in st.session_state['admin_login_attempts']:
        st.session_state['admin_login_attempts'][client_id] = []
    st.session_state['admin_login_attempts'][client_id].append(time.time())

def secure_admin_login(provided_password, correct_password):
    """Secure admin authentication with constant-time comparison"""
    try:
        # Generate salt for this session if not exists
        if 'admin_salt' not in st.session_state:
            st.session_state['admin_salt'] = secrets.token_hex(32)
        
        salt = st.session_state['admin_salt']
        
        # Create hashes with salt
        provided_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode(), salt.encode(), 100000)
        correct_hash = hashlib.pbkdf2_hmac('sha256', correct_password.encode(), salt.encode(), 100000)
        
        # Constant time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(provided_hash, correct_hash)
        
        if is_valid:
            # Generate secure session token
            st.session_state['admin_session_token'] = secrets.token_hex(32)
            
        return is_valid
    except Exception as e:
        # Log error but don't expose details to user
        st.error("Authentication error. Please try again.")
        return False

# --- Configuration Setup ---
def setup_config():
    """Setup configuration from Streamlit secrets or environment variables"""
    try:
        # Try to get from Streamlit secrets first (production)
        if hasattr(st, 'secrets') and 'OPENAI_API_KEY' in st.secrets:
            openai_key = st.secrets['OPENAI_API_KEY']
            admin_pw = st.secrets.get('ADMIN_PW', 'admin123')
            max_queries = st.secrets.get('MAX_QUERIES_PER_HOUR', 100)
            max_tokens = st.secrets.get('MAX_TOKENS_PER_DAY', 500000)
            
            # Force high limits for development
            max_queries = 100
            max_tokens = 500000
        else:
            # Fallback to environment variables (development)
            openai_key = os.getenv('OPENAI_API_KEY')
            admin_pw = os.getenv('ADMIN_PW', 'admin123')
            max_queries = int(os.getenv('MAX_QUERIES_PER_HOUR', '100'))
            max_tokens = int(os.getenv('MAX_TOKENS_PER_DAY', '500000'))
            
            # Force high limits for development
            max_queries = 100
            max_tokens = 500000
        
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
        
        /* ROBUST SIDEBAR RECOVERY - Multiple selectors for different Streamlit versions */
        /* Target collapsed sidebar with multiple possible classes */
        .css-1d391kg, .css-1cypcdb, .css-17eq0hr, section[data-testid="stSidebar"][aria-expanded="false"] {
            background: var(--whu-primary) !important;
            width: 3rem !important;
            min-width: 3rem !important;
            max-width: 3rem !important;
            position: fixed !important;
            left: 0 !important;
            z-index: 999999 !important;
        }
        
        /* Style the expand button with multiple selectors */
        .css-1d391kg button, .css-1cypcdb button, .css-17eq0hr button,
        section[data-testid="stSidebar"][aria-expanded="false"] button {
            background: var(--whu-primary) !important;
            color: white !important;
            width: 100% !important;
            height: 60px !important;
            border-radius: 0 8px 8px 0 !important;
            font-size: 18px !important;
            border: none !important;
            cursor: pointer !important;
            transition: all 0.3s ease !important;
        }
        
        .css-1d391kg button:hover, .css-1cypcdb button:hover, .css-17eq0hr button:hover,
        section[data-testid="stSidebar"][aria-expanded="false"] button:hover {
            background: rgba(5,70,150,0.8) !important;
            transform: scale(1.05) !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
        }
        
        /* Add visual indicators when sidebar is collapsed */
        .css-1d391kg::after, .css-1cypcdb::after, .css-17eq0hr::after {
            content: "Menu";
            position: absolute;
            top: 120px;
            left: 50%;
            transform: translateX(-50%) rotate(-90deg);
            font-size: 12px;
            background: white;
            padding: 4px 8px;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            white-space: nowrap;
            color: var(--whu-primary);
            font-weight: bold;
        }
        
        /* Force sidebar to always be accessible - emergency recovery */
        .css-1d391kg, .css-1cypcdb, .css-17eq0hr {
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
        }
        
        /* Enhanced visibility for the collapsed state */
        section[data-testid="stSidebar"] {
            transition: all 0.3s ease !important;
        }
        
        /* Emergency sidebar toggle button if all else fails */
        .emergency-sidebar-toggle {
            position: fixed;
            top: 20px;
            left: 10px;
            z-index: 9999999;
            background: var(--whu-primary);
            color: white;
            padding: 10px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            display: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
)

# JavaScript solution to handle browser local storage sidebar state
st.markdown(
    """
    <script>
    // Force sidebar recovery on page load
    document.addEventListener('DOMContentLoaded', function() {
        // Clear any stored sidebar state to prevent permanent collapse
        if (typeof(Storage) !== "undefined") {
            // Clear Streamlit sidebar state from localStorage
            Object.keys(localStorage).forEach(key => {
                if (key.includes('sidebar') || key.includes('stSidebar')) {
                    localStorage.removeItem(key);
                }
            });
        }
        
        // Add emergency toggle button if sidebar is not accessible
        setTimeout(function() {
            var sidebar = document.querySelector('[data-testid="stSidebar"]');
            var collapsedSidebar = document.querySelector('.css-1d391kg, .css-1cypcdb, .css-17eq0hr');
            
            if (!sidebar || (collapsedSidebar && collapsedSidebar.offsetWidth < 50)) {
                var emergencyBtn = document.createElement('div');
                emergencyBtn.className = 'emergency-sidebar-toggle';
                emergencyBtn.innerHTML = '📋 Menu';
                emergencyBtn.style.display = 'block';
                emergencyBtn.onclick = function() {
                    // Try to trigger sidebar expansion
                    var buttons = document.querySelectorAll('[data-testid="stSidebar"] button, .css-1d391kg button, .css-1cypcdb button');
                    buttons.forEach(btn => btn.click());
                };
                document.body.appendChild(emergencyBtn);
            }
        }, 1000);
    });
    
    // Monitor for sidebar collapse and ensure it remains accessible
    setInterval(function() {
        var sidebar = document.querySelector('[data-testid="stSidebar"]');
        if (sidebar) {
            var rect = sidebar.getBoundingClientRect();
            if (rect.width < 100) {
                // Sidebar is collapsed, ensure the expand button is visible and styled
                var expandBtn = sidebar.querySelector('button');
                if (expandBtn) {
                    expandBtn.style.background = 'rgb(5,70,150)';
                    expandBtn.style.color = 'white';
                    expandBtn.style.height = '60px';
                    expandBtn.style.borderRadius = '0 8px 8px 0';
                    expandBtn.style.fontSize = '18px';
                    expandBtn.title = 'Click to expand sidebar with Admin Login and Chat';
                }
            }
        }
    }, 2000);
    </script>
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

# Check admin session timeout (30 minutes) and validate session token
if st.session_state.get('admin_logged_in') and st.session_state.get('admin_login_time'):
    if time.time() - st.session_state['admin_login_time'] > 1800:  # 30 minutes
        st.session_state['admin_logged_in'] = False
        st.session_state['admin_login_time'] = None
        st.session_state['admin_session_token'] = None
        st.warning("Admin session expired. Please log in again.")
    elif not st.session_state.get('admin_session_token'):
        # Session token missing - possible session hijacking attempt
        st.session_state['admin_logged_in'] = False
        st.session_state['admin_login_time'] = None
        st.error("Session security error. Please log in again.")

# --- Sidebar Admin Login/Logout ---
with st.sidebar:
    st.sidebar.header("Administration")
    if st.session_state.get('admin_logged_in'):
        st.success("Admin logged in")
        remaining_time = 30 - (time.time() - st.session_state.get('admin_login_time', 0)) / 60
        if remaining_time > 0:
            st.caption(f"Session expires in {remaining_time:.0f} minutes")
        if st.button("Logout"):
            # Secure logout - clear all admin session data
            st.session_state['admin_logged_in'] = False
            st.session_state['admin_login_time'] = None
            st.session_state['admin_session_token'] = None
            # Clear any cached admin data
            for key in list(st.session_state.keys()):
                if key.startswith('admin_') and key != 'admin_login_mode':
                    del st.session_state[key]
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
                # Check rate limiting first
                client_id = f"admin_{st.session_state.get('session_id', 'unknown')}"
                can_attempt, rate_msg = check_admin_rate_limit(client_id)
                
                if not can_attempt:
                    st.error(rate_msg)
                else:
                    # Record the attempt
                    record_admin_attempt(client_id)
                    
                    if not pw:
                        st.error("Please enter a password")
                    else:
                        # Get admin password from configuration
                        admin_pw = None
                        try:
                            if hasattr(st, 'secrets') and 'ADMIN_PW' in st.secrets:
                                admin_pw = st.secrets['ADMIN_PW']
                            else:
                                admin_pw = os.getenv("ADMIN_PW", "admin123")
                        except Exception:
                            admin_pw = os.getenv("ADMIN_PW", "admin123")
                        
                        if admin_pw and secure_admin_login(pw, admin_pw):
                            st.session_state['admin_logged_in'] = True
                            st.session_state['admin_login_mode'] = False
                            st.session_state['admin_login_time'] = time.time()
                            # Clear successful login attempts
                            st.session_state['admin_login_attempts'].pop(client_id, None)
                            st.success("Successfully logged in as admin")
                            st.rerun()
                        else:
                            st.error("Invalid admin password")
                            # Small delay to slow down brute force attempts
                            time.sleep(2)
            if st.button("Cancel", key="sidebar_admin_cancel"):
                st.session_state['admin_login_mode'] = False
                st.rerun()

# --- Chatbot Section (always available in sidebar for non-admins) ---
if not st.session_state.get('admin_logged_in'):
    st.sidebar.markdown("---")
    st.sidebar.header("Course Chatbot")
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []
    if 'user_question' not in st.session_state:
        st.session_state['user_question'] = ""
    
    # Only show chat if student info is complete
    if st.session_state.get('info_complete'):
        user_question = st.sidebar.text_area(
            "Ask a question about the current assignment question or course PDF:",
            value=st.session_state['user_question'],
            key="chat_input_unique"
        )
        if st.sidebar.button("Send"):
            if user_question:
                try:
                    # Get current assignment context
                    if 'question_idx' in st.session_state and 'selected_section' in st.session_state:
                        questions = get_assignment_questions(st.session_state['selected_section'])
                        current_idx = st.session_state['question_idx']
                        assignment_context = questions[current_idx] if questions and current_idx < len(questions) else ""
                    else:
                        assignment_context = ""
                    
                    answer = answer_query(
                        user_question, 
                        assignment_context, 
                        section=st.session_state.get('selected_section', 'Ch.3'),
                        user_email=st.session_state.get('student_email', '')
                    )
                    st.session_state['chat_history'].insert(0, (user_question, answer))  # Add to top
                    # persist chat
                    try:
                        save_chat(st.session_state.get('student_email', ''), user_question, answer)
                    except Exception as e:
                        # Log error but don't interrupt user experience
                        logger.error(f"Failed to save chat: {e}")
                    st.session_state['user_question'] = ""  # Clear input immediately
                    st.rerun()
                except Exception as e:
                    st.sidebar.error("Sorry, I encountered an error processing your question. Please try again.")
                    logger.error(f"Chat error for {st.session_state.get('student_email', 'unknown')}: {e}")
            else:
                st.sidebar.write("Please enter a question.")
        st.sidebar.markdown("---")
        st.sidebar.subheader("Chat History")
        for q, a in st.session_state['chat_history']:
            st.sidebar.markdown(f"**You:** {q}")
            st.sidebar.markdown(f"**Bot:** {a}")
    else:
        st.sidebar.info("Complete student information to access the chatbot")

# --- Student Info Page ---
def student_info_page():
    st.title("Supply Chain Learning")
    
    # Add sidebar hint
 
    
    st.header("Student Information")
    name = st.text_input("Enter your name:", value=st.session_state['student_name'], key="student_name_input")
    email = st.text_input("Enter your email:", value=st.session_state['student_email'], key="student_email_input")
    submit = st.button("Submit")
    if submit:
        st.session_state['student_name'] = name
        st.session_state['student_email'] = email
        
        # Import validation functions
        from modules.base import validate_email, validate_name
        
        # Validate inputs
        name_valid, name_msg = validate_name(name)
        email_valid, email_msg = validate_email(email)
        
        if name_valid and email_valid:
            st.session_state['info_complete'] = True
            # persist student with validated data
            try:
                save_student(name_msg, email_msg)  # Use validated/cleaned data
                st.success(f"✅ Welcome {name_msg}! You have been successfully logged in.")
                st.rerun()
            except ValueError as e:
                st.error(f"Registration error: {str(e)}")
                st.session_state['info_complete'] = False
            except Exception as e:
                st.error("Registration failed. Please try again.")
                st.session_state['info_complete'] = False
        else:
            st.session_state['info_complete'] = False
            if not name_valid:
                st.error(f"Name error: {name_msg}")
            if not email_valid:
                st.error(f"Email error: {email_msg}")
    st.markdown("---")

# --- Assignment Page ---
def assignment_page():
    st.title("Supply Chain Learning")
    
    # Add collapsible sidebar recovery hint
    
    st.markdown("---")
    
    # Section selector (Chapter / Case study) - Show first
    sections = get_available_sections()
    if 'selected_section' not in st.session_state:
        st.session_state['selected_section'] = ""  # Start with no selection
    
    selected_section = st.selectbox("Select section:", options=[""] + sections, index=0 if not st.session_state['selected_section'] else sections.index(st.session_state['selected_section']) + 1 if st.session_state['selected_section'] in sections else 0)
    
    # If no section is selected, show selection prompt
    if not selected_section:
        st.info("Please select a section above to begin working on assignments.")
        return
    
    # Update session state with selection
    st.session_state['selected_section'] = selected_section
    st.caption(f"Current section: {selected_section}")
    
    # Section-specific content starts here
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
        # Clear the chat input widget state
        if "chat_input_unique" in st.session_state:
            del st.session_state["chat_input_unique"]
    
    # tell backend which section we're working with (used for DB queries)
    set_current_section(selected_section)
    
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
                    passed, message = validate_numeric_answer("2.1", val_2_1)
                    if passed:
                        st.success(message)
                        st.session_state['auto_2_1_pass'] = True
                    else:
                        st.info(message)
                    # save numeric answer as text for this question
                    save_answer(st.session_state.get('student_email', ''), current_idx, f"2.1:{val_2_1:.2f} -> {'PASS' if passed else 'FAIL'}")

                # Task 2.2 – Daily Delivery Cost per Store (Japan vs US)
                st.write("Task 2.2 - Enter Japan cost per store/day and US cost per store/day")
                val_japan = st.number_input("Japan cost (¥)", value=0.0, format="%.2f", key="auto_2_2_japan")
                val_us = st.number_input("US cost (¥)", value=0.0, format="%.2f", key="auto_2_2_us")
                if st.button("Check Task 2.2"):
                    # Validate both values
                    passed_japan, msg_japan = validate_numeric_answer("2.2_japan", val_japan)
                    passed_us, msg_us = validate_numeric_answer("2.2_us", val_us)
                    passed_diff, msg_diff = validate_numeric_answer("2.2_difference", val_japan - val_us)
                    
                    if passed_japan and passed_us and passed_diff:
                        st.success("Task 2.2 OK — your values are within the acceptable tolerance.")
                        st.session_state['auto_2_2_pass'] = True
                    else:
                        st.info("Hint: For each country compute (cost per truck ÷ stores per truck) × deliveries per store/day to get the per-store/day cost, then compare the two results. Check your arithmetic and units.")
                    save_answer(st.session_state.get('student_email', ''), current_idx, f"2.2: Japan {val_japan:.2f}, US {val_us:.2f} -> {'PASS' if (passed_japan and passed_us and passed_diff) else 'FAIL'}")
    
    # --- Dragon Fire Case Interactive Tools ---
    elif st.session_state.get('selected_section') == 'Dragon Fire Case':
        # Add interactive calculation tools for different phases
        if current_idx == 0:  # Phase 1: Product & Market Analysis
                
                with st.expander("Volume & Container Calculator", expanded=True):
                    st.markdown("**Calculate powder volume and containers needed**")
                    st.info("Research and input appropriate values for density and container sizes")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        drinks_target = st.number_input("Target drinks (Year 1)", min_value=1, value=None, placeholder="Enter target drinks")
                        powder_per_drink = st.number_input("Powder per drink (grams)", min_value=1, value=None, placeholder="Enter grams per drink")
                    
                    with col2:
                        powder_density = st.number_input("Powder density (kg/L)", min_value=0.1, max_value=2.0, value=None, placeholder="Research and enter density")
                        container_volume = st.number_input("Container volume (m³)", min_value=1, max_value=100, value=None, placeholder="Research container sizes")
                
                    # Save Phase 1 inputs button (always available)
                    if st.button("Save Phase 1 Inputs"):
                        if drinks_target and powder_per_drink and powder_density and container_volume:
                            # Create input summary
                            input_summary = f"Drinks Target: {drinks_target:,}, Powder per drink: {powder_per_drink}g, Density: {powder_density} kg/L, Container Volume: {container_volume} m³"
                            save_answer(st.session_state.get('student_email', ''), current_idx, input_summary)
                            st.success("Phase 1 inputs saved successfully!")
                        else:
                            st.warning("Please enter values for all fields before saving")
                
                # Only show calculations if all values are provided
                if drinks_target and powder_per_drink and powder_density and container_volume:
                    # Use modular calculation function
                    metrics = calculate_volume_metrics(drinks_target, powder_per_drink, powder_density, container_volume)
                    
                    st.markdown("**Results:**")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Powder", f"{metrics['total_powder_kg']:,.0f} kg")
                    with col2:
                        st.metric("Volume Needed", f"{metrics['total_volume_m3']:.1f} m³")
                    with col3:
                        st.metric("Containers", f"{metrics['containers_needed']:.1f}")
                    
                    # Additional save option for calculated results
                    calc_result = f"Volume Calculator Results: {drinks_target:,} drinks → {metrics['total_powder_kg']:,.0f} kg → {metrics['total_volume_m3']:.1f} m³ → {metrics['containers_needed']:.1f} containers"
                    if st.button("Save Calculation Results"):
                        save_answer(st.session_state.get('student_email', ''), 99, calc_result)  # Special index for calculations
                        st.success("Calculation results saved!")
                else:
                    st.info("Please fill in all values to see calculations")
        
        elif current_idx == 1:  # Phase 2: Transportation Mode Comparison
            st.info("**Enter your analysis values and perform transportation mode comparison")
            
            # Add input collection for Phase 2
            with st.expander("Transportation Analysis Inputs", expanded=True):
                st.markdown("**Enter your values for transportation mode analysis:**")
                
                col1, col2 = st.columns(2)
                with col1:
                    containers = st.number_input("Number of containers:", value=0.0, min_value=0.0, format="%.2f", key="phase2_containers")
                    total_weight = st.number_input("Total weight (kg):", value=0.0, min_value=0.0, format="%.2f", key="phase2_weight")
                    total_volume = st.number_input("Total volume (m³):", value=0.0, min_value=0.0, format="%.3f", key="phase2_volume")
                
                with col2:
                    wacc_rate = st.number_input("WACC rate (as decimal, e.g., 0.15 for 15%):", value=0.15, min_value=0.01, max_value=0.30, format="%.3f", key="phase2_wacc")
                    transport_cost = st.number_input("Transport cost (€) for selected mode:", value=0.0, min_value=0.0, format="%.2f", key="phase2_transport_cost")
                    total_cost = st.number_input("Total cost (€) including capital cost:", value=0.0, min_value=0.0, format="%.2f", key="phase2_total_cost")
                
                # Mode selection for context
                selected_mode = st.selectbox("Selected transportation mode:", 
                                           options=["", "Sea Freight", "Air Freight", "Rail Freight"], 
                                           key="phase2_selected_mode")
                
                # Save inputs button
                if st.button("Save Phase 2 Inputs"):
                    if containers > 0 and total_weight > 0 and total_volume > 0 and wacc_rate > 0:
                        # Use the modular function to validate and process inputs
                        result = collect_phase2_inputs(containers, total_weight, total_volume, wacc_rate)
                        
                        if result["validation"]["valid"]:
                            # Enhanced input summary including new fields
                            input_summary = f"Containers: {containers:.2f}, Weight: {total_weight:.2f} kg, Volume: {total_volume:.3f} m³, WACC: {wacc_rate:.3f} ({wacc_rate*100:.1f}%)"
                            if selected_mode:
                                input_summary += f", Selected Mode: {selected_mode}"
                            if transport_cost > 0:
                                input_summary += f", Transport Cost: €{transport_cost:.2f}"
                            if total_cost > 0:
                                input_summary += f", Total Cost: €{total_cost:.2f}"
                            
                            save_answer(st.session_state.get('student_email', ''), current_idx, input_summary)
                            st.success("Phase 2 inputs saved successfully!")
                        else:
                            for error in result["validation"]["errors"]:
                                st.error(error)
                    else:
                        st.warning("Please enter valid values for all required fields (containers, weight, volume, WACC must be greater than 0)")
        
        
        elif current_idx == 3:  # Phase 4: Risk Management & Scenario Planning
            # Offer students a selectable disruption scenario and show details
            student_email = st.session_state.get('student_email', '')

            # Load the scenarios from the module
            scenarios_dict = get_disruption_scenarios()
            scenarios = list(scenarios_dict.values())  # Convert to list for iteration
            assigned = assign_scenario(student_email) if student_email else None

            # Build selectbox options (use titles as the visible label)
            option_titles = [s.get('title', f"Scenario {s.get('id', idx+1)}") for idx, s in enumerate(scenarios)]
            default_index = 0
            if assigned:
                try:
                    default_index = option_titles.index(assigned.get('title'))
                except ValueError:
                    default_index = 0

            st.info("Choose a disruption scenario for Phase 4. A deterministic assignment is shown as the default, but you may select another scenario.")

            selected_title = st.selectbox("Select disruption scenario:", options=option_titles, index=default_index, key="dragon_q4_scenario")
            # Map selected title back to scenario dict
            selected_scenario = next((s for s in scenarios if s.get('title') == selected_title), scenarios[0])

            # Show details inline
            with st.expander("Scenario Details", expanded=True):
                st.markdown(f"**Situation**: {selected_scenario.get('description', '')}")
                st.markdown("**Key Impacts**:")
                for impact in selected_scenario.get('impacts', []):
                    st.markdown(f"• {impact}")

            # Auto-save selection when student has email and selection changes
            if student_email:
                # Check if this is a new selection by comparing with last saved
                last_saved_key = f"dragon_q4_last_saved_{student_email}"
                if st.session_state.get(last_saved_key) != selected_title:
                    # Build a concise saved text entry
                    impacts_text = "\n".join([f"- {i}" for i in selected_scenario.get('impacts', [])])
                    saved_text = f"Selected Scenario: {selected_scenario.get('title')}\n\n{selected_scenario.get('description', '')}\n\nKey Impacts:\n{impacts_text}"
                    try:
                        save_answer(student_email, current_idx, saved_text)
                        st.session_state[last_saved_key] = selected_title
                        st.success("✓ Scenario selection auto-saved.")
                    except Exception as e:
                        st.error("Failed to auto-save scenario selection.")
                        logger.error(f"Failed to save scenario selection for {student_email}: {e}")
            else:
                st.warning("Please complete your student information (name & email) before your scenario selection can be saved.")
    
    # For all sections except Dragon Fire Case Phase 1 Q1, show the regular text area for answers
    if not (st.session_state.get('selected_section') == 'Dragon Fire Case' and current_idx == 0):
        answer_box = st.text_area(f"Your answer to Q{current_idx+1}", key=f"ans_{current_idx}")
    else:
        # For Dragon Fire Phase 1 Q1, no text box - students use the calculator above
        answer_box = ""  # Empty string to maintain variable consistency
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Previous"):
            if current_idx > 0:
                st.session_state['question_idx'] -= 1
                # Clear chat history when moving to new question
                st.session_state['chat_history'] = []
                st.session_state['user_question'] = ""
                # Clear the chat input widget state
                if "chat_input_unique" in st.session_state:
                    del st.session_state["chat_input_unique"]
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
                    current_answer = st.session_state.get(f"ans_{current_idx}", "")
                    
                    # Save answer with error handling
                    if current_answer.strip():
                        try:
                            # For Dragon Fire Phase 2, combine input data with text area if both exist
                            if (st.session_state.get('selected_section') == 'Dragon Fire Case' and current_idx == 1):
                                # Check if Phase 2 inputs were already saved
                                from backend import get_answers_by_email
                                existing_answers = get_answers_by_email(st.session_state.get('student_email', ''))
                                phase2_input_saved = any(ans[0] == current_idx and 'Containers:' in ans[1] for ans in existing_answers)
                                
                                if phase2_input_saved and current_answer.strip():
                                    # Combine the existing input data with the text area analysis
                                    phase2_inputs = next((ans[1] for ans in existing_answers if ans[0] == current_idx and 'Containers:' in ans[1]), "")
                                    combined_answer = f"{phase2_inputs}\n\n**Analysis:**\n{current_answer}"
                                    save_answer(st.session_state.get('student_email', ''), current_idx, combined_answer)
                                elif current_answer.strip():
                                    # Just save the text area if no inputs were saved
                                    save_answer(st.session_state.get('student_email', ''), current_idx, current_answer)
                            else:
                                # For all other questions, save normally
                                save_answer(st.session_state.get('student_email', ''), current_idx, current_answer)
                        except Exception as e:
                            st.error("Failed to save your answer. Please try again.")
                            logger.error(f"Failed to save answer for {st.session_state.get('student_email', 'unknown')}: {e}")
                            st.stop()  # Don't proceed if save failed
                    
                    st.session_state['question_idx'] += 1
                    # Clear chat history when moving to new question
                    st.session_state['chat_history'] = []
                    st.session_state['user_question'] = ""
                    # Clear the chat input widget state
                    if "chat_input_unique" in st.session_state:
                        del st.session_state["chat_input_unique"]
                    st.rerun()
            else:
                # Show disabled-style button with warning
                if st.button("Next (Validation Required)", disabled=False, help="Complete numeric validation first"):
                    st.error('**Validation Required**: You must pass the numeric auto-validation for Tasks 2.1 and 2.2 before proceeding to the next question.')
                    st.info('**Tip**: Scroll up to the "Auto-validate numeric tasks" section and complete both Task 2.1 and Task 2.2 validations.')
        else:
            # Last question - show final submit button instead of completion message
            if st.button("Submit Final Assignment", type="primary"):
                # Save current answer with special handling for Dragon Fire Phase 2
                current_answer = st.session_state.get(f"ans_{current_idx}", "")
                
                if current_answer.strip():
                    try:
                        if (st.session_state.get('selected_section') == 'Dragon Fire Case' and current_idx == 1):
                            # Check if Phase 2 inputs were already saved
                            from backend import get_answers_by_email
                            existing_answers = get_answers_by_email(st.session_state.get('student_email', ''))
                            phase2_input_saved = any(ans[0] == current_idx and 'Containers:' in ans[1] for ans in existing_answers)
                            
                            if phase2_input_saved and current_answer.strip():
                                # Combine the existing input data with the text area analysis
                                phase2_inputs = next((ans[1] for ans in existing_answers if ans[0] == current_idx and 'Containers:' in ans[1]), "")
                                combined_answer = f"{phase2_inputs}\n\n**Analysis:**\n{current_answer}"
                                save_answer(st.session_state.get('student_email', ''), current_idx, combined_answer)
                            elif current_answer.strip():
                                # Just save the text area if no inputs were saved
                                save_answer(st.session_state.get('student_email', ''), current_idx, current_answer)
                        else:
                            # For all other questions, save normally
                            save_answer(st.session_state.get('student_email', ''), current_idx, current_answer)
                    except Exception as e:
                        st.error("Failed to save your final answer. Please try again.")
                        logger.error(f"Failed to save final answer for {st.session_state.get('student_email', 'unknown')}: {e}")
                        st.stop()
                
                # Mark assignment as completed
                st.session_state[f'assignment_completed_{st.session_state.get("selected_section", "Ch.3")}'] = True
                
                # Show completion message
                st.success("Assignment submitted successfully! You can now close the window!")
                
                # Optional: move to a completion state or reset
                time.sleep(2)
                st.rerun()
            
            
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
            pass  # Assignment completed silently
        
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
            time.sleep(1)
            st.rerun()
        
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
                        
                        # Display question directly without expander
                        st.markdown(f"### Question {qidx + 1} (Latest Submission)")
                        
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
                            grade_options = ["", "5", "4.5", "4", "3.5", "3", "2.5", "2", "1.5", "1", "0.5", "0"]
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
                                    try:
                                        save_grade(student_email, qidx, new_grade)
                                        st.success("Grade saved!")
                                        time.sleep(1)
                                        st.rerun()
                                    except Exception as e:
                                        st.error("Failed to save grade. Please try again.")
                                        logger.error(f"Failed to save grade for {student_email}: {e}")
                                else:
                                    st.warning("Please select a grade first.")
                        
                        with col3:
                            if current_grade:
                                st.metric("Current Grade", current_grade)
                            else:
                                st.info("No grade yet")
                        
                        # Add separator between questions
                        st.markdown("---")
    
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
        student_map = {s[0].strip().lower(): s[1] for s in students}  # email -> name mapping
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
            chats = get_chats_by_email(email_clean, section if section != "All" else 'Ch.3')
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
        student_name = next((name for email, name, _ in students if email == selected), "Unknown")
        st.subheader(f"Quick View: {student_name} - ({selected})")
        
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
