# 7-Eleven Case 2015 Module - Distribution network analysis
import os
import openai
import numpy as np
from typing import List
from .base import (
    logger, get_pdf_chunks, cosine_similarity, 
    check_rate_limit, record_query
)

# Storage for PDF chunks and embeddings
_pdf_chunks = []
_pdf_embeddings = []

def get_pdf_path():
    """Get path to 7-Eleven case PDF"""
    return os.path.join(os.path.dirname(__file__), "..", "7eleven case 2015.pdf")

def ensure_embeddings():
    """Lazily computes chunks and embeddings for 7-Eleven case PDF"""
    global _pdf_chunks, _pdf_embeddings
    if _pdf_chunks and _pdf_embeddings:
        return
    
    pdf_path = get_pdf_path()
    if not pdf_path or not os.path.exists(pdf_path):
        # leave empty lists to avoid None issues downstream
        _pdf_chunks = []
        _pdf_embeddings = []
        return
    
    chunks = get_pdf_chunks(pdf_path)
    _pdf_chunks = chunks
    if chunks:
        try:
            response = openai.embeddings.create(input=chunks, model="text-embedding-ada-002")
            _pdf_embeddings = [d.embedding for d in response.data]
        except Exception as e:
            logger.error(f"Error creating embeddings for 7-Eleven case: {e}")
            _pdf_embeddings = []
    else:
        _pdf_embeddings = []

def get_assignment_questions() -> List[str]:
    """Return assignment questions for 7-Eleven Case 2015"""
    return [
        "Part 1 – Conceptual Foundations:\n\nExplain how distribution network design affects efficiency and responsiveness for Seven-Eleven Japan. Answer the three questions below (≈150–200 words total):\n\n1) Why does Seven-Eleven Japan operate so many stores in dense clusters?\n2) Explain how the Combined Delivery System (CDS) supports efficiency and responsiveness compared to Direct Store Delivery (DSD).\n3) Identify two cost factors and two service factors from the Session 5 framework that are directly impacted by this choice.",

        "Part 2 – Quantitative Case Analysis: Evaluating the Combined Delivery System:\n\nUse the case data provided. For each task provide your calculation and a short interpretation.\n\nTask 2.1 – DC Utilization:\nCompute average stores served per DC. (Show calculation)\nExpected value: 16,000 / 158 ≈ 101.27 (acceptable range: 100–102).\n\nTask 2.2 – Daily Delivery Cost per Store:\nCompute cost per store/day for Japan and U.S. using: (cost per truck/run ÷ stores per truck/run) × deliveries per store/day.\nShow the numeric values and the difference.\nExpected: Japan = (50,000 ÷ 10) × 3 = ¥15,000; U.S. = (60,000 ÷ 8) × 1 = ¥7,500; Difference = ¥7,500 (tolerance ±500).",

        "Task 2.3 – Multi-temperature Deliveries:\nIf each temperature zone requires separate runs, compute the cost per store/day and compare to a hypothetical DSD setup.\nShow calculation for: 3 × (50,000 ÷ 10) × 3 = ¥45,000 per store/day for three separate-zone runs.\nCompare to DSD example: 5 suppliers × ¥7,500 = ¥37,500.\nWrite a short discussion (~100 words) on which is more cost-efficient and why (include considerations: frequency, complexity, coordination).",

        "Task 2.4 – Fresh Food Rationale:\nFresh/fast food ≈ 65% of sales. Explain how this share justifies high delivery frequency and cost (≈80 words).",

        "Part 3 – Guided Chatbot Exploration (Chatbot-assisted inquiry):\n\nGoal: Use the GPT chatbot (preloaded with case) to explore product-level suitability for DSD and potential problems.\n\nInstructions and tasks:\n1) Ask the chatbot at least two of the following prompts (copy the exact prompts you used and the bot replies):\n   - \"Which product categories in Seven-Eleven Japan's supply chain are most suitable for DSD?\"\n   - \"What problems could arise if suppliers deliver directly to stores?\"\n   - \"How would separating temperature zones affect daily routing and cost?\"\n2) Paste 1–2 chatbot exchanges (max 5 lines each).\n3) Summarize what you learned (≤100 words).\n\nExamples (students may adapt):\nStudent: \"Which product categories are most suitable for DSD?\"\nBot: \"Low-value, low-velocity items with stable demand (e.g., beverages) and items where suppliers already have local distribution can be candidates for DSD because...\"",

        "Part 4 – Strategic Application: Expansion to Germany:\n\nScenario: Seven-Eleven Japan considers entering Germany. Using the Session 5 framework, recommend whether to replicate CDS, adopt hybrid CDS+DSD, or another design. Identify 2–3 promising German regions and justify (consider density, road infrastructure, consumer habits). (≈200 words)",

        "Deliverables & Validation Requirements:\n\n- Part 1: Short written answers (rubric).\n- Part 2: Numeric answers for Tasks 2.1 and 2.2 must include calculations. Automatic validation rules: 2.1 expected ≈101 (±2); 2.2 expected difference ≈¥7,500 (±500). Provide raw numbers and steps.\n- Part 3: Include at least one chatbot interaction snippet.\n- Part 4: Written recommendation with region justification.\n\nStudents: mark each numeric answer clearly to enable auto-checking. Incomplete numeric steps will reduce auto score.",

        "Instructor Notes & Chatbot Context (for graders/developers):\n\nContext prompt (to preload to the chatbot):\n\"You are an SCM case assistant. Use the Seven-Eleven Japan (2015) case data and Session 5 slides to answer questions about CDS, DSD and trade-offs. Key facts: 16,000 stores; 158 DCs; 3 deliveries/day; 10 stores/truck; ¥50,000 per truck/run; 3 temperature zones; 65% fresh food share; avg DC–store lead time ~3 hrs.\"\n\nValidation logic summary:\n- Numeric tolerance: ±500 for yen amounts, ±2 for simple ratios.\n- Require at least one chatbot interaction snippet for Part 3.\n- Auto-check code example (students may include similar snippet in their submission).",

        "Example validation code (for instructors or automated checks):\n```python\nstores_per_dc = 16000 / 158  # 101.27\njapan_cost = (50000 / 10) * 3  # 15000\nus_cost = (60000 / 8) * 1  # 7500\ndifference = japan_cost - us_cost  # 7500\nmulti_temp_cost = 3 * (50000 / 10) * 3  # 45000\n```",

        "Scoring guidance (summary):\n- Part 1: rubric 0–3 (concept clarity, links to framework).\n- Part 2: numeric auto-check for 2.1/2.2 plus written interpretation (rubric).\n- Part 3: relevance and correct use of case context in chatbot snippet + summary (rubric).\n- Part 4: strategic reasoning (rubric).\n\nPlease follow the question ordering when students submit; the admin grader UI will surface numeric fields for auto-checking if students label answers clearly."
    ]

def validate_numeric_answer(task: str, value: float) -> tuple[bool, str]:
    """Validate numeric answers for 7-Eleven case"""
    if task == "2.1":
        expected_2_1 = 16000 / 158
        tol_2_1 = 2
        diff = abs(value - expected_2_1)
        passed = diff <= tol_2_1
        if passed:
            return True, f"Task 2.1 OK — your {value:.2f} is within ±{tol_2_1} of the expected range."
        else:
            return False, "Hint: compute average stores per DC by dividing total stores by number of DCs (i.e. total stores ÷ DCs). Check your division and rounding."
    
    elif task == "2.2_japan":
        expected_japan = (50000 / 10) * 3  # 15000
        tol_yen = 500
        diff = abs(value - expected_japan)
        return diff <= tol_yen, f"Japan cost: {value:.2f} ¥/day"
    
    elif task == "2.2_us":
        expected_us = (60000 / 8) * 1  # 7500
        tol_yen = 500
        diff = abs(value - expected_us)
        return diff <= tol_yen, f"US cost: {value:.2f} ¥/day"
    
    elif task == "2.2_difference":
        expected_diff = 7500
        tol_yen = 500
        diff = abs(value - expected_diff)
        passed = diff <= tol_yen
        if passed:
            return True, "Task 2.2 OK — your values are within the acceptable tolerance."
        else:
            return False, "Hint: For each country compute (cost per truck ÷ stores per truck) × deliveries per store/day to get the per-store/day cost, then compare the two results. Check your arithmetic and units."
    
    return False, "Unknown task"

def answer_query(query: str, assignment_context: str = "", user_email: str = "") -> str:
    """Answer user query for 7-Eleven case with rate limiting and error handling"""
    try:
        # Check rate limits
        if user_email:
            allowed, message = check_rate_limit(user_email)
            if not allowed:
                return f"{message}. Please try again later."
        
        # Ensure embeddings are available
        ensure_embeddings()
        
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
        
        # Find most similar chunk within 7-Eleven case
        if not _pdf_embeddings or not _pdf_chunks:
            best_chunk = ""  # no context available
        else:
            try:
                sims = [cosine_similarity(query_emb, emb) for emb in _pdf_embeddings]
                best_idx = sims.index(max(sims))
                best_chunk = _pdf_chunks[best_idx]
            except Exception as e:
                logger.error(f"Error in similarity calculation: {e}")
                best_chunk = ""
        
        # Prompt for hints only, not full solutions
        prompt = (
            f"Context: {best_chunk}\nAssignment Question: {assignment_context}\nStudent Query: {query}\nHint:"
        )
        
        # 7-Eleven specific system context
        system_context = (
            "You are a supply chain course assistant specializing in distribution network design. "
            "Use the following context to give helpful hints for the assignment question, but do NOT solve it directly. "
            "Encourage the student to think and guide them to the right concepts or formulas. "
            "Provide data from your understanding if a student asks for it. "
            "If the student asks for a solution, only provide hints and steps, not the final answer.\n"
            "7-Eleven Japan Context: 16,000 stores, 158 DCs, Combined Delivery System (CDS), "
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
                    tokens_used = response.usage.total_tokens
                    record_query(user_email, tokens_used)
                
                return bot_response
                
            except openai.RateLimitError:
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return "OpenAI rate limit reached. Please try again in a few minutes."
                
            except openai.OpenAIError as e:
                logger.error(f"OpenAI API error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    continue
                return "Unable to process your question right now. Please try again later."
                
            except Exception as e:
                logger.error(f"Unexpected error in answer_query attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    continue
                break
        
        return "Unable to process your question at this time. Please try again later."
        
    except Exception as e:
        logger.error(f"Critical error in 7-Eleven answer_query: {e}")
        return "A technical error occurred. Please contact support if this persists."

def has_pdf():
    """Check if 7-Eleven case PDF exists"""
    return os.path.exists(get_pdf_path())

def get_section_name():
    """Return the section name"""
    return "7-Eleven Case 2015"