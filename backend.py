import os
import openai
import fitz  # PyMuPDF
from typing import List, Optional
from dotenv import load_dotenv
import re
import sqlite3
from datetime import datetime, timedelta
import time
import logging
import threading
from contextlib import contextmanager
# No Streamlit imports in backend - this is a pure logic module

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables (fallback for development)
load_dotenv()

# Global configuration - will be set by app.py
_config = {
    'openai_api_key': None,
    'admin_password': None,
    'max_queries_per_hour': 500,
    'max_tokens_per_day': 100000
}

def set_config(openai_key: str, admin_pw: str = None, max_queries: int = 500, max_tokens: int = 100000):
    """Set configuration from Streamlit secrets or environment variables"""
    global _config
    _config['openai_api_key'] = openai_key
    _config['admin_password'] = admin_pw
    _config['max_queries_per_hour'] = max_queries
    _config['max_tokens_per_day'] = max_tokens
    openai.api_key = openai_key
    logger.info("Configuration updated successfully")

# Rate limiting storage
_user_queries = {}  # {email: [(timestamp, token_count), ...]}
_rate_limit_lock = threading.Lock()

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
# Map logical sections to PDF files in the repo. Add new PDFs to this map as needed.
SECTION_PDFS = {
    "Ch.3": "WHU_BSc_Fall 2024_session 3.pdf",
    "7-Eleven Case 2015": "7eleven case 2015.pdf",
    "Dragon Fire Case": None,  # Interactive case study - no PDF needed
}

def extract_text_pymupdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def split_into_chunks(text: str, min_length: int = 300) -> List[str]:
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
                    temp += ' ' + sent
                else:
                    chunks.append(temp.strip())
                    temp = sent
            if temp:
                chunks.append(temp.strip())
        else:
            chunks.append(para)
    return [c for c in chunks if len(c) > 50]

def get_pdf_chunks(pdf_path: str) -> List[str]:
    text = extract_text_pymupdf(pdf_path)
    return split_into_chunks(text)

_pdf_chunks_by_section = {}
_pdf_embeddings_by_section = {}

def get_available_sections():
    return list(SECTION_PDFS.keys())

def _pdf_path_for_section(section: str):
    filename = SECTION_PDFS.get(section)
    if not filename:
        return None
    return os.path.join(os.path.dirname(__file__), filename)

def ensure_embeddings(section: str = "Ch.3"):
    """Lazily computes chunks and embeddings for a named section."""
    global _pdf_chunks_by_section, _pdf_embeddings_by_section
    if section in _pdf_chunks_by_section and section in _pdf_embeddings_by_section:
        return
    pdf_path = _pdf_path_for_section(section)
    if not pdf_path or not os.path.exists(pdf_path):
        # leave empty lists to avoid None issues downstream
        _pdf_chunks_by_section[section] = []
        _pdf_embeddings_by_section[section] = []
        return
    chunks = get_pdf_chunks(pdf_path)
    _pdf_chunks_by_section[section] = chunks
    if chunks:
        response = openai.embeddings.create(input=chunks, model="text-embedding-ada-002")
        _pdf_embeddings_by_section[section] = [d.embedding for d in response.data]
    else:
        _pdf_embeddings_by_section[section] = []


# --- Simple persistent storage (SQLite) for students, answers, and chats ---
DB_PATH = os.path.join(os.path.dirname(__file__), "student_data.db")

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
            # Don't raise - continue with existing schema
    
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
                    # Fallback to old schema without roll_number
                    logger.warning("Using old schema without roll_number column")
                    cur.execute("INSERT OR REPLACE INTO students(email, name, created_at) VALUES (?, ?, ?)",
                                (email, name, datetime.utcnow().isoformat()))
                else:
                    raise
        logger.info(f"Student saved: {email} (Roll: {roll_number})")
    except Exception as e:
        logger.error(f"Error saving student {email}: {e}")
        raise


def save_answer(email: str, question_idx: int, answer: str):
    email = email.strip().lower()
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            section = getattr(save_answer, 'current_section', 'Ch.3')
            cur.execute("INSERT INTO answers(email, question_idx, answer, section, submitted_at) VALUES (?, ?, ?, ?, ?)",
                        (email, question_idx, answer, section, datetime.utcnow().isoformat()))
        logger.info(f"Answer saved: {email}, Q{question_idx}")
    except Exception as e:
        logger.error(f"Error saving answer for {email}: {e}")
        raise


def save_chat(email: str, question: str, bot_response: str):
    email = email.strip().lower()
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            section = getattr(save_chat, 'current_section', 'Ch.3')
            cur.execute("INSERT INTO chats(email, question, bot_response, section, created_at) VALUES (?, ?, ?, ?, ?)",
                        (email, question, bot_response, section, datetime.utcnow().isoformat()))
        logger.info(f"Chat saved: {email}")
    except Exception as e:
        logger.error(f"Error saving chat for {email}: {e}")
        raise


def get_answers_by_email(email: str):
    email = email.strip().lower()
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            section = getattr(get_answers_by_email, 'current_section', 'Ch.3')
            cur.execute("SELECT question_idx, answer, submitted_at FROM answers WHERE email = ? AND section = ? ORDER BY submitted_at", (email, section))
            rows = cur.fetchall()
        return rows
    except Exception as e:
        logger.error(f"Error getting answers for {email}: {e}")
        return []


def get_chats_by_email(email: str):
    email = email.strip().lower()
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            section = getattr(get_chats_by_email, 'current_section', 'Ch.3')
            cur.execute("SELECT question, bot_response, created_at FROM chats WHERE email = ? AND section = ? ORDER BY created_at", (email, section))
            rows = cur.fetchall()
        return rows
    except Exception as e:
        logger.error(f"Error getting chats for {email}: {e}")
        return []


def get_all_submissions():
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
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT email, name, roll_number, created_at FROM students ORDER BY email")
            rows = cur.fetchall()
        return rows
    except Exception as e:
        logger.error(f"Error getting all students: {e}")
        return []


def save_grade(email: str, question_idx: int, grade: str):
    email = email.strip().lower()
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            section = getattr(save_grade, 'current_section', 'Ch.3')
            cur.execute("INSERT INTO grades(email, question_idx, grade, section, graded_at) VALUES (?, ?, ?, ?, ?)",
                        (email, question_idx, grade, section, datetime.utcnow().isoformat()))
        logger.info(f"Grade saved: {email}, Q{question_idx}")
    except Exception as e:
        logger.error(f"Error saving grade for {email}: {e}")
        raise


def get_grades_by_email(email: str):
    email = email.strip().lower()
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            section = getattr(get_grades_by_email, 'current_section', 'Ch.3')
            cur.execute("SELECT question_idx, grade, graded_at FROM grades WHERE email = ? AND section = ? ORDER BY graded_at", (email, section))
            rows = cur.fetchall()
        return rows
    except Exception as e:
        logger.error(f"Error getting grades for {email}: {e}")
        return []


def get_latest_grade(email: str, question_idx: int):
    email = email.strip().lower()
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            section = getattr(get_latest_grade, 'current_section', 'Ch.3')
            cur.execute("SELECT grade FROM grades WHERE email = ? AND question_idx = ? AND section = ? ORDER BY graded_at DESC LIMIT 1", (email, question_idx, section))
            row = cur.fetchone()
        return row[0] if row else None
    except Exception as e:
        logger.error(f"Error getting latest grade for {email}: {e}")
        return None


# Initialize DB on import
init_db()

# --- RAG Query ---
def cosine_similarity(a, b):
    import numpy as np
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def answer_query(query: str, assignment_context: str = "", section: str = "Ch.3", user_email: str = "") -> str:
    """Answer user query with rate limiting and error handling"""
    try:
        # Check rate limits
        if user_email:
            allowed, message = check_rate_limit(user_email)
            if not allowed:
                return f"{message}. Please try again later."
        
        # Ensure embeddings are available
        ensure_embeddings(section)
        
        # Combine user query and assignment question for better context
        full_query = query
        if assignment_context:
            full_query += f"\nAssignment Question: {assignment_context}"
        
        # Embed the query with error handling
        try:
            query_response = openai.embeddings.create(input=[full_query], model="text-embedding-ada-002")
            query_emb = query_response.data[0].embedding
        except openai.OpenAIError as e:
            logger.error(f"OpenAI embedding error: {e}")
            return "I'm having trouble processing your question right now. Please try again in a few moments."
        except Exception as e:
            logger.error(f"Unexpected error in embedding: {e}")
            return "There was a technical issue. Please try again later."
        
        # Find most similar chunk within the requested section
        emb_list = _pdf_embeddings_by_section.get(section, [])
        chunk_list = _pdf_chunks_by_section.get(section, [])
        
        if not emb_list or not chunk_list:
            best_chunk = ""  # no context available for this section
        else:
            try:
                sims = [cosine_similarity(query_emb, emb) for emb in emb_list]
                best_idx = sims.index(max(sims))
                best_chunk = chunk_list[best_idx]
            except Exception as e:
                logger.error(f"Error in similarity calculation: {e}")
                best_chunk = ""
        
        # Prompt for hints only, not full solutions
        prompt = (
            f"Context: {best_chunk}\nAssignment Question: {assignment_context}\nStudent Query: {query}\nHint:"
        )
        
        # Build section-specific system context
        system_context = "You are a supply chain course assistant. Use the following context to give helpful hints for the assignment question, but do NOT solve it directly. " \
                        "Encourage the student to think and guide them to the right concepts or formulas. " \
                        "Provide data from your understanding if a student asks for it. " \
                        "If the student asks for a solution, only provide hints and steps, not the final answer.\n"
        
        # Add section-specific knowledge
        if section == "Dragon Fire Case":
            system_context += (
                "\nDragon Fire Case Context: Blue Dragon (Austria) is launching an energy drink in China's high-end market. "
                "Key facts: 25 Yuan price point, coca leaf-based (not caffeine), powder shipped from Austria, "
                "mixed with water in China, distributed to bars/clubs/restaurants. "
                "Transportation options: Sea (30-35 days, $2-3k/container), Air (3-5 days, $8-12/kg), "
                "Rail (18-25 days, $4-5k/container). Main Chinese ports: Shanghai, Ningbo, Shenzhen. "
                "Consider: regulatory risks of coca leaf products, temperature sensitivity, premium market requirements, "
                "supply chain disruptions (Suez Canal, port closures, etc.). Guide students through systematic analysis "
                "of volume calculations, mode selection, risk management, and total cost optimization."
            )
        elif section == "7-Eleven Case 2015":
            system_context += (
                "\n7-Eleven Japan Context: 16,000 stores, 158 DCs, Combined Delivery System (CDS), "
                "3 deliveries/day, 10 stores/truck, ¥50,000 per truck/run, 3 temperature zones, "
                "65% fresh food share, ~3 hour DC-store lead time. Compare with US operations and DSD alternatives."
            )
        
        # Make API call with error handling and retries
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{
                        "role": "system", 
                        "content": system_context
                    }, {
                        "role": "user", 
                        "content": prompt
                    }],
                    max_tokens=1000,
                    temperature=0.7
                )
                
                bot_response = response.choices[0].message.content.strip()
                
                # Record the query for rate limiting
                if user_email:
                    tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 150
                    record_query(user_email, tokens_used)
                
                return bot_response
                
            except openai.RateLimitError:
                logger.warning(f"OpenAI rate limit hit, attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return "The AI service is currently busy. Please try again in a few minutes."
                
            except openai.OpenAIError as e:
                logger.error(f"OpenAI API error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return "I'm having trouble connecting to the AI service. Please try again later."
                
            except Exception as e:
                logger.error(f"Unexpected error in answer_query: {e}")
                return "Something went wrong while processing your question. Please try again."
        
        return "Unable to process your question at this time. Please try again later."
        
    except Exception as e:
        logger.error(f"Critical error in answer_query: {e}")
        return "A technical error occurred. Please contact support if this persists."

# --- Assignment Generation ---
def get_assignment_questions(section: str = "Ch.3") -> List[str]:
    """Return assignment questions for a given section.
    Defaults to Ch.3. Add more per-section question sets here.
    """
    if section == "Ch.3":
        # Structured supply chain assignment questions
        questions = [
        # Part A: EOQ
        "Part A: Economic Order Quantity (EOQ)\n\nA retailer sells 52,000 units of printer paper per year.\nOrdering cost per order = €150\nAnnual holding cost = 20% of item cost\nItem cost per unit = €2.\n\n1. Compute the EOQ.\n2. Calculate the total annual cost (ordering + holding + purchasing).\n3. Discuss how EOQ changes if order cost halves or holding cost doubles.\n4. What practical factors could make EOQ deviate from optimal levels (e.g., quantity discounts, batch constraints, uncertainty)?",

    # Part B: Safety Inventory
    "Part B: Safety Inventory\n\nWeekly demand for a component is normally distributed with\nMean = 500 units, Standard deviation = 80 units.\nLead time = 3 weeks. Desired cycle service level = 95%.\n\n1. Compute the safety stock.\n2. Find the reorder point.\n3. How would your answer change if lead time variability increases by 50%?\n4. Interpret what a 95% cycle service level means operationally.",

        # Part C: Newsboy Model
        "Part C: Newsboy Model (Single-Period)\n\nA bakery produces croissants daily.\nCost to produce one croissant = €1.\nSelling price = €2.50.\nUnsold croissants are discarded with no salvage value.\nDaily demand is normally distributed with mean = 200, SD = 40.\n\n1. Determine the critical ratio.\n2. Find the z-value and optimal order quantity.\n3. Compute the expected number of unsold and lost sales.\n4. Explain what would change if leftover croissants could be sold next day at €0.50.\n5. Compare the Newsboy and EOQ models. When is each appropriate in real business contexts?",

        # Integrative Task
        "Optional Integrative Task\n\nYou are a supply chain manager at a stationery company.\nUsing EOQ, Safety Inventory, and the Newsboy Model:\n\nIdentify which model applies to your regular office supplies, fast-moving promotional items, and seasonal products.\n\nJustify your reasoning in 200–300 words."
        ]
        return questions
    elif section == "7-Eleven Case 2015":
        # Full assignment for the 7-Eleven case study (expanded from 7eleven_assignment.md)
        return [
            "Part 1 – Conceptual Foundations:\n\nExplain how distribution network design affects efficiency and responsiveness for Seven-Eleven Japan. Answer the three questions below (≈150–200 words total):\n\n1) Why does Seven-Eleven Japan operate so many stores in dense clusters?\n2) Explain how the Combined Delivery System (CDS) supports efficiency and responsiveness compared to Direct Store Delivery (DSD).\n3) Identify two cost factors and two service factors from the Session 5 framework that are directly impacted by this choice.",

            "Part 2 – Quantitative Case Analysis: Evaluating the Combined Delivery System:\n\nUse the case data provided. For each task provide your calculation and a short interpretation.\n\nTask 2.1 – DC Utilization:\nCompute average stores served per DC. (Show calculation)\nExpected value: 16,000 / 158 ≈ 101.27 (acceptable range: 100–102).\n\nTask 2.2 – Daily Delivery Cost per Store:\nCompute cost per store/day for Japan and U.S. using: (cost per truck/run ÷ stores per truck/run) × deliveries per store/day.\nShow the numeric values and the difference.\nExpected: Japan = (50,000 ÷ 10) × 3 = ¥15,000; U.S. = (60,000 ÷ 8) × 1 = ¥7,500; Difference = ¥7,500 (tolerance ±500).",


            "Task 2.3 – Multi-temperature Deliveries:\nIf each temperature zone requires separate runs, compute the cost per store/day and compare to a hypothetical DSD setup.\nShow calculation for: 3 × (50,000 ÷ 10) × 3 = ¥45,000 per store/day for three separate-zone runs.\nCompare to DSD example: 5 suppliers × ¥7,500 = ¥37,500.\nWrite a short discussion (~100 words) on which is more cost-efficient and why (include considerations: frequency, complexity, coordination).",


            "Task 2.4 – Fresh Food Rationale:\nFresh/fast food ≈ 65% of sales. Explain how this share justifies high delivery frequency and cost (≈80 words).",

            "Part 3 – Guided Chatbot Exploration (Chatbot-assisted inquiry):\n\nGoal: Use the GPT chatbot (preloaded with case) to explore product-level suitability for DSD and potential problems.\n\nInstructions and tasks:\n1) Ask the chatbot at least two of the following prompts (copy the exact prompts you used and the bot replies):\n   - \"Which product categories in Seven-Eleven Japan’s supply chain are most suitable for DSD?\"\n   - \"What problems could arise if suppliers deliver directly to stores?\"\n   - \"How would separating temperature zones affect daily routing and cost?\"\n2) Paste 1–2 chatbot exchanges (max 5 lines each).\n3) Summarize what you learned (≤100 words).\n\nExamples (students may adapt):\nStudent: \"Which product categories are most suitable for DSD?\"\nBot: \"Low-value, low-velocity items with stable demand (e.g., beverages) and items where suppliers already have local distribution can be candidates for DSD because...\"",

            "Part 4 – Strategic Application: Expansion to Germany:\n\nScenario: Seven-Eleven Japan considers entering Germany. Using the Session 5 framework, recommend whether to replicate CDS, adopt hybrid CDS+DSD, or another design. Identify 2–3 promising German regions and justify (consider density, road infrastructure, consumer habits). (≈200 words)",

            "Deliverables & Validation Requirements:\n\n- Part 1: Short written answers (rubric).\n- Part 2: Numeric answers for Tasks 2.1 and 2.2 must include calculations. Automatic validation rules: 2.1 expected ≈101 (±2); 2.2 expected difference ≈¥7,500 (±500). Provide raw numbers and steps.\n- Part 3: Include at least one chatbot interaction snippet.\n- Part 4: Written recommendation with region justification.\n\nStudents: mark each numeric answer clearly to enable auto-checking. Incomplete numeric steps will reduce auto score.",

            "Instructor Notes & Chatbot Context (for graders/developers):\n\nContext prompt (to preload to the chatbot):\n\"You are an SCM case assistant. Use the Seven-Eleven Japan (2015) case data and Session 5 slides to answer questions about CDS, DSD and trade-offs. Key facts: 16,000 stores; 158 DCs; 3 deliveries/day; 10 stores/truck; ¥50,000 per truck/run; 3 temperature zones; 65% fresh food share; avg DC–store lead time ~3 hrs.\"\n\nValidation logic summary:\n- Numeric tolerance: ±500 for yen amounts, ±2 for simple ratios.\n- Require at least one chatbot interaction snippet for Part 3.\n- Auto-check code example (students may include similar snippet in their submission).",

            "Example validation code (for instructors or automated checks):\n```python\nstores_per_dc = 16000 / 158  # 101.27\njapan_cost = (50000 / 10) * 3  # 15000\nus_cost = (60000 / 8) * 1  # 7500\ndifference = japan_cost - us_cost  # 7500\nmulti_temp_cost = 3 * (50000 / 10) * 3  # 45000\n```",

            "Scoring guidance (summary):\n- Part 1: rubric 0–3 (concept clarity, links to framework).\n- Part 2: numeric auto-check for 2.1/2.2 plus written interpretation (rubric).\n- Part 3: relevance and correct use of case context in chatbot snippet + summary (rubric).\n- Part 4: strategic reasoning (rubric).\n\nPlease follow the question ordering when students submit; the admin grader UI will surface numeric fields for auto-checking if students label answers clearly."
        ]
    elif section == "Dragon Fire Case":
        # Interactive supply chain design case
        return [
            "Phase 1: Product & Market Analysis\n\nDesign the supply chain for Dragon Fire energy drink from Austria to China.\n\n**Case Background**: Blue Dragon (Austria) wants to launch Dragon Fire energy drink in China's high-end market (bars, clubs, restaurants). The product uses coca leaf powder (not caffeine) and sells for 25 Yuan (~3€) per drink.\n\n**Your Task**: Complete the product analysis:\n\n1. **Volume Estimation**: If Blue Dragon targets 1 million drinks in Year 1, and each drink needs 10g of powder, calculate:\n   - Total powder needed (kg)\n   - Estimated volume in cubic meters (research appropriate powder density)\n   - Number of standard shipping containers needed (research container sizes)\n\n2. **Product Characteristics**: Identify 3 factors about the powder that will impact transportation choices (consider: shelf life, temperature sensitivity, regulatory restrictions, value density).",

            "Phase 2: Transportation Mode Comparison\n\nCompare different ways to get Dragon Fire powder from Austria to China.\n\n**Available Options**:\n- **Sea Freight**: 30-35 days, $2,000-3,000 per container\n- **Air Freight**: 3-5 days, $8-12 per kg\n- **Rail Freight**: 18-25 days, $4,000-5,000 per container\n- **Multimodal**: Combinations of above\n\n**Your Analysis**:\n\n1. **Cost Calculation**: For your powder volume from Phase 1, calculate the transportation cost for each mode. Show your work.\n\n2. **Mode Evaluation**: Based on the following factors, choose your preferred transportation mode and justify with 3 specific reasons:\n   - Cost efficiency\n   - Speed to market\n   - Reliability\n   - Risk level\n   - Environmental impact",

            "Phase 3: Supply Chain Design\n\nDesign your complete China operation.\n\n**Key Decisions to Make**:\n\n1. **Entry Port Selection**:\n   - Compare Shanghai, Ningbo, and Shenzhen ports\n   - Consider: proximity to target markets, port efficiency, inland transport costs\n   - Choose one port and justify your selection\n\n2. **Mixing/Bottling Facility Location**:\n   - Where in China will you mix powder with water and bottle the drinks?\n   - Consider: labor costs, regulations, proximity to customers, water quality\n   - Identify 2-3 potential cities and rank them\n\n3. **Distribution Strategy**:\n   - How will finished drinks reach bars/clubs in major Chinese cities?\n   - Design your distribution network (regional hubs, direct delivery, etc.)\n   - Calculate approximate delivery radius and frequency\n\n4. **Inventory Planning**:\n   - How much safety stock of powder should you maintain?\n   - Where should inventory be held (port, factory, regional centers)?\n   - Consider seasonal demand variations and lead times\n\n**Deliverable**: Create a simple supply chain map showing: Austria production → transport → China port → mixing facility → distribution → end customers",

            "Phase 4: Risk Management & Scenario Planning\n\nYour supply chain faces a real-world disruption. How will you respond?\n\n**Your Scenario**: You will be assigned one of three possible disruptions. Develop a comprehensive response plan for your assigned scenario.\n\n**Possible Disruptions**:\n1. **Suez Canal Blockage**: A major ship blocks the canal for 3 weeks (like Ever Given 2021)\n2. **COVID-19 Port Closure**: Shanghai port closes for 2 weeks due to outbreak\n3. **Regulatory Challenge**: China restricts coca leaf imports pending safety review\n\n**Your Response Plan** (for your assigned disruption):\n1. **Immediate Actions** (first 48 hours)\n2. **Short-term Mitigation** (1-4 weeks)\n3. **Long-term Adaptation** (1-6 months)\n4. **Cost Impact** (estimated additional costs)\n\n**Risk Prevention**: Design 2 proactive measures to reduce vulnerability to this type of disruption in the future."
        ]
    else:
        # Default fallback
        return ["No assignments available for this section yet."]

