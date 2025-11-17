# Base module with common functionality
import os
import fitz  # PyMuPDF
import sqlite3
import threading
import logging
import re
import numpy as np
import openai
from typing import List, Optional
from dotenv import load_dotenv
from datetime import datetime, timedelta
from contextlib import contextmanager
import html

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables (fallback for development)
load_dotenv()

# Global configuration - will be set by app.py
_config = {
    'openai_api_key': None,
    'admin_password': None,
    'max_queries_per_hour': 100,
    'max_tokens_per_day': 500000
}

def set_config(openai_key: str, admin_pw: str = None, max_queries: int = 100, max_tokens: int = 500000):
    """Set configuration from Streamlit secrets or environment variables"""
    global _config
    _config['openai_api_key'] = openai_key
    _config['admin_password'] = admin_pw
    _config['max_queries_per_hour'] = max_queries
    _config['max_tokens_per_day'] = max_tokens
    openai.api_key = openai_key
    logger.info(f"Configuration updated: max_queries={max_queries}, max_tokens={max_tokens}")

# --- Input Validation and Sanitization ---
def validate_email(email: str) -> tuple[bool, str]:
    """Validate WHU email address"""
    if not email or not isinstance(email, str):
        return False, "Email is required"
    
    email = email.strip().lower()
    
    # Length check
    if len(email) > 100:
        return False, "Email address too long"
    
    # Basic email format validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@whu\.edu$'
    if not re.match(email_pattern, email):
        return False, "Please use a valid WHU email address ending with @whu.edu"
    
    return True, email

def validate_name(name: str) -> tuple[bool, str]:
    """Validate and sanitize student name"""
    if not name or not isinstance(name, str):
        return False, "Name is required"
    
    # Remove HTML and dangerous characters
    name = html.escape(name.strip())
    
    # Length check
    if len(name) < 2:
        return False, "Name must be at least 2 characters long"
    if len(name) > 100:
        return False, "Name too long (max 100 characters)"
    
    # Character validation - allow letters, spaces, hyphens, apostrophes
    if not re.match(r"^[a-zA-Z\s'-]+$", name):
        return False, "Name can only contain letters, spaces, hyphens, and apostrophes"
    
    return True, name

def validate_text_input(text: str, max_length: int = 10000, field_name: str = "Input") -> tuple[bool, str]:
    """Validate and sanitize text input (answers, chat messages)"""
    if not text or not isinstance(text, str):
        return False, f"{field_name} cannot be empty"
    
    # Length check to prevent DOS attacks
    if len(text) > max_length:
        return False, f"{field_name} too long (max {max_length} characters)"
    
    # Remove potential script injection
    text = html.escape(text.strip())
    
    # Check for suspicious patterns
    suspicious_patterns = [
        r'<script.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe',
        r'<object',
        r'<embed'
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            logger.warning(f"Suspicious content detected in {field_name}: {pattern}")
            return False, f"{field_name} contains invalid content"
    
    return True, text

def sanitize_for_db(value: str, max_length: int = None) -> str:
    """Sanitize value for database storage"""
    if not value:
        return ""
    
    # HTML escape
    value = html.escape(str(value).strip())
    
    # Limit length if specified
    if max_length and len(value) > max_length:
        value = value[:max_length]
    
    return value

# Rate limiting storage
_user_queries = {}  # {email: [(timestamp, token_count), ...]}
_ip_queries = {}    # {ip: [(timestamp, endpoint), ...]}
_rate_limit_lock = threading.Lock()

# Make _user_queries accessible for admin dashboard
def get_user_queries():
    """Get user queries data for admin dashboard"""
    return _user_queries

def check_rate_limit(email: str, estimated_tokens: int = 10000, ip_address: str = None) -> tuple[bool, str]:
    """Enhanced rate limiting with both email and IP-based checks"""
    with _rate_limit_lock:
        current_time = datetime.utcnow()
        hour_ago = current_time - timedelta(hours=1)
        day_ago = current_time - timedelta(days=1)
        
        # Clean old entries for email
        if email in _user_queries:
            _user_queries[email] = [(ts, tokens) for ts, tokens in _user_queries[email] 
                                   if ts > day_ago]
        else:
            _user_queries[email] = []
        
        user_history = _user_queries[email]
        
        # Check email-based limits
        recent_queries = [ts for ts, _ in user_history if ts > hour_ago]
        if len(recent_queries) >= _config['max_queries_per_hour']:
            return False, f"Rate limit exceeded: Max {_config['max_queries_per_hour']} queries per hour"
        
        # Check daily token limit
        daily_tokens = sum(tokens for ts, tokens in user_history if ts > day_ago)
        if daily_tokens + estimated_tokens > _config['max_tokens_per_day']:
            return False, f"Token limit exceeded: Max {_config['max_tokens_per_day']} tokens per day"
        
        # IP-based rate limiting if IP provided
        if ip_address:
            if ip_address not in _ip_queries:
                _ip_queries[ip_address] = []
            
            # Clean old IP entries
            _ip_queries[ip_address] = [(ts, endpoint) for ts, endpoint in _ip_queries[ip_address] 
                                      if ts > hour_ago]
            
            # Check IP rate limit (more permissive than email-based)
            ip_recent = len(_ip_queries[ip_address])
            if ip_recent >= _config['max_queries_per_hour'] * 3:  # 3x limit for IP
                return False, "IP rate limit exceeded. Please try again later."
        
        return True, "OK"

def record_query(email: str, tokens_used: int, ip_address: str = None):
    """Record a query for rate limiting"""
    with _rate_limit_lock:
        if email not in _user_queries:
            _user_queries[email] = []
        _user_queries[email].append((datetime.utcnow(), tokens_used))
        
        # Record IP activity if provided
        if ip_address:
            if ip_address not in _ip_queries:
                _ip_queries[ip_address] = []
            _ip_queries[ip_address].append((datetime.utcnow(), "query"))

def clear_rate_limits(email: str = None):
    """Clear rate limiting data - for testing/admin purposes"""
    with _rate_limit_lock:
        if email:
            _user_queries.pop(email, None)
        else:
            _user_queries.clear()
    logger.info(f"Rate limits cleared for {'all users' if not email else email}")

def get_rate_limit_status(email: str) -> dict:
    """Get current rate limit status for debugging"""
    with _rate_limit_lock:
        if email not in _user_queries:
            return {"queries_today": 0, "tokens_today": 0, "queries_hour": 0}
        
        current_time = datetime.utcnow()
        hour_ago = current_time - timedelta(hours=1)
        day_ago = current_time - timedelta(days=1)
        
        user_history = _user_queries[email]
        recent_queries = [ts for ts, _ in user_history if ts > hour_ago]
        daily_tokens = sum(tokens for ts, tokens in user_history if ts > day_ago)
        total_queries = len([ts for ts, _ in user_history if ts > day_ago])
        
        return {
            "queries_hour": len(recent_queries),
            "queries_today": total_queries,
            "tokens_today": daily_tokens,
            "max_queries_hour": _config['max_queries_per_hour'],
            "max_tokens_day": _config['max_tokens_per_day']
        }

# PDF processing utilities
def extract_text_pymupdf(pdf_path: str) -> str:
    """Extract text from PDF using PyMuPDF"""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def split_into_chunks(text: str, min_length: int = 300) -> List[str]:
    """Split text into chunks for embedding"""
    # Split by paragraphs, then sentences if needed
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    chunks = []
    for para in paragraphs:
        if len(para) < min_length:
            # Further split by sentences
            sentences = re.split(r'(?<=[.!?]) +', para)
            temp = ''
            for sent in sentences:
                if len(temp) + len(sent) < min_length:
                    temp += sent + ' '
                else:
                    if temp:
                        chunks.append(temp.strip())
                    temp = sent + ' '
            if temp:
                chunks.append(temp.strip())
        else:
            chunks.append(para)
    return [c for c in chunks if len(c) > 50]

def get_pdf_chunks(pdf_path: str) -> List[str]:
    """Get chunks from PDF file"""
    text = extract_text_pymupdf(pdf_path)
    return split_into_chunks(text)

def cosine_similarity(a, b):
    """Calculate cosine similarity between two vectors"""
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# --- Database operations ---
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "student_data.db")

@contextmanager
def get_db_connection():
    """Context manager for database connections with proper error handling"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        # Enhanced security settings
        conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent access
        conn.execute("PRAGMA synchronous=NORMAL")  # Balance performance/safety
        conn.execute("PRAGMA temp_store=memory")  # Store temp data in memory
        conn.execute("PRAGMA mmap_size=268435456")  # 256MB memory-mapped I/O
        conn.execute("PRAGMA foreign_keys=ON")  # Enable foreign key constraints
        yield conn
        conn.commit()
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()

def init_db():
    """Initialize the database with all required tables and security constraints"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Create students table with constraints
    cur.execute("""
    CREATE TABLE IF NOT EXISTS students (
        email TEXT PRIMARY KEY CHECK(
            length(email) <= 100 AND 
            email LIKE '%@whu.edu' AND
            length(email) > 7
        ),
        name TEXT CHECK(length(name) >= 2 AND length(name) <= 100),
        created_at TEXT NOT NULL
    )
    """)

    # Create answers table with constraints
    cur.execute("""
    CREATE TABLE IF NOT EXISTS answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL CHECK(
            length(email) <= 100 AND 
            email LIKE '%@whu.edu'
        ),
        question_idx INTEGER NOT NULL CHECK(question_idx >= 0 AND question_idx < 100),
        answer TEXT NOT NULL CHECK(length(answer) <= 50000),
        section TEXT DEFAULT 'Ch.3' CHECK(length(section) <= 50),
        submitted_at TEXT NOT NULL,
        FOREIGN KEY (email) REFERENCES students(email)
    )
    """)
    
    # Create chats table with constraints
    cur.execute("""
    CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL CHECK(
            length(email) <= 100 AND 
            email LIKE '%@whu.edu'
        ),
        question TEXT NOT NULL CHECK(length(question) <= 5000),
        bot_response TEXT CHECK(length(bot_response) <= 20000),
        section TEXT DEFAULT 'Ch.3' CHECK(length(section) <= 50),
        created_at TEXT NOT NULL,
        FOREIGN KEY (email) REFERENCES students(email)
    )
    """)
    
    # Create grades table with constraints
    cur.execute("""
    CREATE TABLE IF NOT EXISTS grades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL CHECK(
            length(email) <= 100 AND 
            email LIKE '%@whu.edu'
        ),
        question_idx INTEGER NOT NULL CHECK(question_idx >= 0 AND question_idx < 100),
        grade TEXT NOT NULL CHECK(grade IN ('0', '0.5', '1', '1.5', '2', '2.5', '3', '3.5', '4', '4.5', '5')),
        section TEXT DEFAULT 'Ch.3' CHECK(length(section) <= 50),
        graded_at TEXT NOT NULL,
        FOREIGN KEY (email) REFERENCES students(email)
    )
    """)
    
    # Create indices for better performance
    cur.execute("CREATE INDEX IF NOT EXISTS idx_answers_email_section ON answers(email, section)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_chats_email_section ON chats(email, section)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_grades_email_section ON grades(email, section)")
    
    conn.commit()

    # Add section columns if missing (for upgrades) - but handle errors gracefully
    def ensure_column(table, column, col_def):
        try:
            cur.execute(f"PRAGMA table_info({table})")
            cols = [r[1] for r in cur.fetchall()]
            if column not in cols:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
                logger.info(f"Added column {column} to table {table}")
        except sqlite3.Error as e:
            logger.warning(f"Could not add column {column} to {table}: {e}")

    ensure_column('answers', 'section', "TEXT DEFAULT 'Ch.3'")
    ensure_column('chats', 'section', "TEXT DEFAULT 'Ch.3'")
    ensure_column('grades', 'section', "TEXT DEFAULT 'Ch.3'")
    
    conn.commit()
    conn.close()

def save_student(name: str, email: str):
    """Save student information to database with validation"""
    try:
        # Validate inputs
        email_valid, email_clean = validate_email(email)
        if not email_valid:
            logger.error(f"Invalid email provided: {email}")
            raise ValueError(f"Invalid email: {email_clean}")
        
        name_valid, name_clean = validate_name(name)
        if not name_valid:
            logger.error(f"Invalid name provided: {name}")
            raise ValueError(f"Invalid name: {name_clean}")
        
        with get_db_connection() as conn:
            cur = conn.cursor()
            # Try the new schema first, fallback to old schema if needed
            try:
                cur.execute("INSERT OR REPLACE INTO students(email, name, roll_number, created_at) VALUES (?, ?, ?, ?)",
                            (email_clean, name_clean, "", datetime.utcnow().isoformat()))
            except sqlite3.OperationalError as e:
                if "no column named roll_number" in str(e).lower():
                    cur.execute("INSERT OR REPLACE INTO students(email, name, created_at) VALUES (?, ?, ?)",
                                (email_clean, name_clean, datetime.utcnow().isoformat()))
                else:
                    raise
        logger.info(f"Student saved: {email_clean}")
    except Exception as e:
        logger.error(f"Error saving student {email}: {e}")
        raise

def save_answer(email: str, question_idx: int, answer: str, section: str = 'Ch.3'):
    """Save answer to database with validation"""
    try:
        # Validate email
        email_valid, email_clean = validate_email(email)
        if not email_valid:
            logger.error(f"Invalid email in save_answer: {email}")
            raise ValueError(f"Invalid email: {email_clean}")
        
        # Validate answer content
        answer_valid, answer_clean = validate_text_input(answer, max_length=50000, field_name="Answer")
        if not answer_valid:
            logger.error(f"Invalid answer content for {email}")
            raise ValueError(f"Invalid answer: {answer_clean}")
        
        # Validate question index
        if not isinstance(question_idx, int) or question_idx < 0 or question_idx > 100:
            logger.error(f"Invalid question index: {question_idx}")
            raise ValueError("Invalid question index")
        
        # Sanitize section name
        section = sanitize_for_db(section, max_length=50)
        
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO answers(email, question_idx, answer, section, submitted_at) VALUES (?, ?, ?, ?, ?)",
                        (email_clean, question_idx, answer_clean, section, datetime.utcnow().isoformat()))
        logger.info(f"Answer saved: {email_clean}, Q{question_idx}")
    except Exception as e:
        logger.error(f"Error saving answer for {email}: {e}")
        raise

def save_chat(email: str, question: str, bot_response: str, section: str = 'Ch.3'):
    """Save chat to database with validation"""
    try:
        # Validate email
        email_valid, email_clean = validate_email(email)
        if not email_valid:
            logger.error(f"Invalid email in save_chat: {email}")
            raise ValueError(f"Invalid email: {email_clean}")
        
        # Validate question content
        question_valid, question_clean = validate_text_input(question, max_length=5000, field_name="Question")
        if not question_valid:
            logger.error(f"Invalid question content for {email}")
            raise ValueError(f"Invalid question: {question_clean}")
        
        # Validate bot response (more lenient as it's system-generated)
        bot_response = sanitize_for_db(bot_response, max_length=20000)
        
        # Sanitize section name
        section = sanitize_for_db(section, max_length=50)
        
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO chats(email, question, bot_response, section, created_at) VALUES (?, ?, ?, ?, ?)",
                        (email_clean, question_clean, bot_response, section, datetime.utcnow().isoformat()))
        logger.info(f"Chat saved: {email_clean}")
    except Exception as e:
        logger.error(f"Error saving chat for {email}: {e}")
        raise

def get_answers_by_email(email: str, section: str = 'Ch.3'):
    """Get answers for a specific email and section"""
    email = email.strip().lower()
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT question_idx, answer, submitted_at FROM answers WHERE email = ? AND section = ? ORDER BY submitted_at", (email, section))
            rows = cur.fetchall()
        return rows
    except Exception as e:
        logger.error(f"Error getting answers for {email}: {e}")
        return []

def get_chats_by_email(email: str, section: str = 'Ch.3'):
    """Get chats for a specific email and section"""
    email = email.strip().lower()
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT question, bot_response, created_at FROM chats WHERE email = ? AND section = ? ORDER BY created_at", (email, section))
            rows = cur.fetchall()
        return rows
    except Exception as e:
        logger.error(f"Error getting chats for {email}: {e}")
        return []

def get_all_submissions():
    """Get all submissions from database"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT email, question_idx, answer, section, submitted_at FROM answers ORDER BY email, section, submitted_at")
            rows = cur.fetchall()
        return rows
    except Exception as e:
        logger.error(f"Error getting all submissions: {e}")
        return []

def get_all_students():
    """Get all students from database"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT email, name, created_at FROM students ORDER BY email")
            rows = cur.fetchall()
        return rows
    except Exception as e:
        logger.error(f"Error getting all students: {e}")
        return []

def save_grade(email: str, question_idx: int, grade: str, section: str = 'Ch.3'):
    """Save grade to database"""
    email = email.strip().lower()
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO grades(email, question_idx, grade, section, graded_at) VALUES (?, ?, ?, ?, ?)",
                        (email, question_idx, grade, section, datetime.utcnow().isoformat()))
        logger.info(f"Grade saved: {email}, Q{question_idx}")
    except Exception as e:
        logger.error(f"Error saving grade for {email}: {e}")
        raise

def get_grades_by_email(email: str, section: str = 'Ch.3'):
    """Get grades for a specific email and section"""
    email = email.strip().lower()
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT question_idx, grade, graded_at FROM grades WHERE email = ? AND section = ? ORDER BY graded_at", (email, section))
            rows = cur.fetchall()
        return rows
    except Exception as e:
        logger.error(f"Error getting grades for {email}: {e}")
        return []

def get_latest_grade(email: str, question_idx: int, section: str = 'Ch.3'):
    """Get latest grade for a specific question"""
    email = email.strip().lower()
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT grade FROM grades WHERE email = ? AND question_idx = ? AND section = ? ORDER BY graded_at DESC LIMIT 1", (email, question_idx, section))
            row = cur.fetchone()
        return row[0] if row else None
    except Exception as e:
        logger.error(f"Error getting latest grade for {email}: {e}")
        return None

# Initialize DB on import
init_db()