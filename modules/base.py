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

# Rate limiting storage
_user_queries = {}  # {email: [(timestamp, token_count), ...]}
_rate_limit_lock = threading.Lock()

# Make _user_queries accessible for admin dashboard
def get_user_queries():
    """Get user queries data for admin dashboard"""
    return _user_queries

def check_rate_limit(email: str, estimated_tokens: int = 10000) -> tuple[bool, str]:
    """Check if user is within rate limits. Returns (allowed, message)"""
    with _rate_limit_lock:
        current_time = datetime.utcnow()
        hour_ago = current_time - timedelta(hours=1)
        day_ago = current_time - timedelta(days=1)
        
        # Clean old entries
        if email in _user_queries:
            _user_queries[email] = [(ts, tokens) for ts, tokens in _user_queries[email] 
                                   if ts > day_ago]
        else:
            _user_queries[email] = []
        
        user_history = _user_queries[email]
        
        # Check hourly query limit
        recent_queries = [ts for ts, _ in user_history if ts > hour_ago]
        if len(recent_queries) >= _config['max_queries_per_hour']:
            return False, f"Rate limit exceeded: Max {_config['max_queries_per_hour']} queries per hour"
        
        # Check daily token limit
        daily_tokens = sum(tokens for ts, tokens in user_history if ts > day_ago)
        if daily_tokens + estimated_tokens > _config['max_tokens_per_day']:
            return False, f"Token limit exceeded: Max {_config['max_tokens_per_day']} tokens per day"
        
        return True, "OK"

def record_query(email: str, tokens_used: int):
    """Record a query for rate limiting"""
    with _rate_limit_lock:
        if email not in _user_queries:
            _user_queries[email] = []
        _user_queries[email].append((datetime.utcnow(), tokens_used))

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
        conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent access
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
    """Initialize the database with all required tables"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Create students table with original schema first
    cur.execute("""
    CREATE TABLE IF NOT EXISTS students (
        email TEXT PRIMARY KEY,
        name TEXT,
        created_at TEXT
    )
    """)
    
    # Add roll_number column if it doesn't exist (migration)
    try:
        cur.execute("ALTER TABLE students ADD COLUMN roll_number TEXT DEFAULT ''")
        logger.info("Added roll_number column to students table")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            logger.info("roll_number column already exists")
        else:
            logger.error(f"Error adding roll_number column: {e}")
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        question_idx INTEGER,
        answer TEXT,
        section TEXT,
        submitted_at TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        question TEXT,
        bot_response TEXT,
        section TEXT,
        created_at TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS grades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        question_idx INTEGER,
        grade TEXT,
        section TEXT,
        graded_at TEXT
    )
    """)
    conn.commit()

    # Add section columns if missing (for upgrades)
    def ensure_column(table, column, col_def):
        cur.execute(f"PRAGMA table_info({table})")
        cols = [r[1] for r in cur.fetchall()]
        if column not in cols:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")

    ensure_column('answers', 'section', "TEXT DEFAULT 'Ch.3'")
    ensure_column('chats', 'section', "TEXT DEFAULT 'Ch.3'")
    ensure_column('grades', 'section', "TEXT DEFAULT 'Ch.3'")
    conn.close()

def save_student(name: str, email: str, roll_number: str = ""):
    """Save student information to database"""
    email = email.strip().lower()
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            # Try the new schema first, fallback to old schema if needed
            try:
                cur.execute("INSERT OR REPLACE INTO students(email, name, roll_number, created_at) VALUES (?, ?, ?, ?)",
                            (email, name, roll_number, datetime.utcnow().isoformat()))
            except sqlite3.OperationalError as e:
                if "no column named roll_number" in str(e).lower():
                    cur.execute("INSERT OR REPLACE INTO students(email, name, created_at) VALUES (?, ?, ?)",
                                (email, name, datetime.utcnow().isoformat()))
                else:
                    raise
        logger.info(f"Student saved: {email} (Roll: {roll_number})")
    except Exception as e:
        logger.error(f"Error saving student {email}: {e}")
        raise

def save_answer(email: str, question_idx: int, answer: str, section: str = 'Ch.3'):
    """Save answer to database"""
    email = email.strip().lower()
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO answers(email, question_idx, answer, section, submitted_at) VALUES (?, ?, ?, ?, ?)",
                        (email, question_idx, answer, section, datetime.utcnow().isoformat()))
        logger.info(f"Answer saved: {email}, Q{question_idx}")
    except Exception as e:
        logger.error(f"Error saving answer for {email}: {e}")
        raise

def save_chat(email: str, question: str, bot_response: str, section: str = 'Ch.3'):
    """Save chat to database"""
    email = email.strip().lower()
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO chats(email, question, bot_response, section, created_at) VALUES (?, ?, ?, ?, ?)",
                        (email, question, bot_response, section, datetime.utcnow().isoformat()))
        logger.info(f"Chat saved: {email}")
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
            cur.execute("SELECT email, name, roll_number, created_at FROM students ORDER BY email")
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