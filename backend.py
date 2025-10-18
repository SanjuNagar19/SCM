import os
import openai
import fitz  # PyMuPDF
from typing import List
from dotenv import load_dotenv
import re
import sqlite3
from datetime import datetime
# No Streamlit imports in backend - this is a pure logic module

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
PDF_PATH = "./WHU_BSc_Fall 2024_session 3.pdf"

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

_pdf_chunks = None
_pdf_embeddings = None

def ensure_embeddings():
    global _pdf_chunks, _pdf_embeddings
    if _pdf_chunks is None:
        _pdf_chunks = get_pdf_chunks(PDF_PATH)
    if _pdf_embeddings is None:
        response = openai.embeddings.create(input=_pdf_chunks, model="text-embedding-ada-002")
        _pdf_embeddings = [d.embedding for d in response.data]


# --- Simple persistent storage (SQLite) for students, answers, and chats ---
DB_PATH = os.path.join(os.path.dirname(__file__), "student_data.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS students (
        email TEXT PRIMARY KEY,
        name TEXT,
        created_at TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        question_idx INTEGER,
        answer TEXT,
        submitted_at TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        question TEXT,
        bot_response TEXT,
        created_at TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS grades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        question_idx INTEGER,
        grade TEXT,
        graded_at TEXT
    )
    """)
    conn.commit()
    conn.close()


def save_student(name: str, email: str):
    email = email.strip().lower()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO students(email, name, created_at) VALUES (?, ?, ?)",
                (email, name, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def save_answer(email: str, question_idx: int, answer: str):
    email = email.strip().lower()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO answers(email, question_idx, answer, submitted_at) VALUES (?, ?, ?, ?)",
                (email, question_idx, answer, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def save_chat(email: str, question: str, bot_response: str):
    email = email.strip().lower()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO chats(email, question, bot_response, created_at) VALUES (?, ?, ?, ?)",
                (email, question, bot_response, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def get_answers_by_email(email: str):
    email = email.strip().lower()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT question_idx, answer, submitted_at FROM answers WHERE email = ? ORDER BY submitted_at", (email,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_chats_by_email(email: str):
    email = email.strip().lower()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT question, bot_response, created_at FROM chats WHERE email = ? ORDER BY created_at", (email,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_all_submissions():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT email, question_idx, answer, submitted_at FROM answers ORDER BY email, submitted_at")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_all_students():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT email, name, created_at FROM students ORDER BY email")
    rows = cur.fetchall()
    conn.close()
    return rows


def save_grade(email: str, question_idx: int, grade: str):
    email = email.strip().lower()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO grades(email, question_idx, grade, graded_at) VALUES (?, ?, ?, ?)",
                (email, question_idx, grade, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def get_grades_by_email(email: str):
    email = email.strip().lower()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT question_idx, grade, graded_at FROM grades WHERE email = ? ORDER BY graded_at", (email,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_latest_grade(email: str, question_idx: int):
    email = email.strip().lower()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT grade FROM grades WHERE email = ? AND question_idx = ? ORDER BY graded_at DESC LIMIT 1", (email, question_idx))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


# Initialize DB on import
init_db()

# --- RAG Query ---
def cosine_similarity(a, b):
    import numpy as np
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def answer_query(query: str, assignment_context: str = "") -> str:
    ensure_embeddings()
    # Combine user query and assignment question for better context
    full_query = query
    if assignment_context:
        full_query += f"\nAssignment Question: {assignment_context}"
    # Embed the query
    query_emb = openai.embeddings.create(input=[full_query], model="text-embedding-ada-002").data[0].embedding
    # Find most similar chunk
    sims = [cosine_similarity(query_emb, emb) for emb in _pdf_embeddings]
    best_idx = sims.index(max(sims))
    best_chunk = _pdf_chunks[best_idx]
    # Prompt for hints only, not full solutions
    prompt = (
        f"Context: {best_chunk}\nAssignment Question: {assignment_context}\nStudent Query: {query}\nHint:"
    )
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "You are a supply chain course assistant. Use the following context to give helpful hints for the assignment question, but do NOT solve it directly. "
        "Encourage the student to think and guide them to the right concepts or formulas. "
        "If the student asks for a solution, only provide hints and steps, not the final answer.\n"},
                  {"role": "user", "content": prompt}],
        max_tokens=300
    )
    return response.choices[0].message.content.strip()

# --- Assignment Generation ---
def get_assignment_questions() -> List[str]:
    # Structured supply chain assignment questions
    questions = [
        # Part A: EOQ
        "Part A: Economic Order Quantity (EOQ)\n\nA retailer sells 52,000 units of printer paper per year.\nOrdering cost per order = €150\nAnnual holding cost = 20% of item cost\nItem cost per unit = €2.\n\n1. Compute the EOQ.\n2. Calculate the total annual cost (ordering + holding + purchasing).\n3. Discuss how EOQ changes if order cost halves or holding cost doubles.\n4. What practical factors could make EOQ deviate from optimal levels (e.g., quantity discounts, batch constraints, uncertainty)?",

        # Part B: Safety Inventory
        "Part B: Safety Inventory\n\nWeekly demand for a component is normally distributed with\nMean = 500 units, Standard deviation = 80 units.\nLead time = 3 weeks. Desired cycle service level = 95%.\n\n1. Compute the safety stock.\n2. Find the reorder point.\n3. How would your answer change if lead time variability increases by 50%?\n4. Interpret what a 95% cycle service level means operationally.\n5. What’s the trade-off between higher service levels and working capital tied in inventory?",

        # Part C: Newsboy Model
        "Part C: Newsboy Model (Single-Period)\n\nA bakery produces croissants daily.\nCost to produce one croissant = €1.\nSelling price = €2.50.\nUnsold croissants are discarded with no salvage value.\nDaily demand is normally distributed with mean = 200, SD = 40.\n\n1. Determine the critical ratio.\n2. Find the z-value and optimal order quantity.\n3. Compute the expected number of unsold and lost sales.\n4. Explain what would change if leftover croissants could be sold next day at €0.50.\n5. Compare the Newsboy and EOQ models. When is each appropriate in real business contexts?",

        # Integrative Task
        "🧩 Optional Integrative Task\n\nYou are a supply chain manager at a stationery company.\nUsing EOQ, Safety Inventory, and the Newsboy Model:\n\nIdentify which model applies to your regular office supplies, fast-moving promotional items, and seasonal products.\n\nJustify your reasoning in 200–300 words."
    ]
    return questions

