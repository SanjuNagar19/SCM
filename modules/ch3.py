# Ch.3 Module - Economic Order Quantity and related content
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
    """Get path to Ch.3 PDF"""
    return os.path.join(os.path.dirname(__file__), "..", "WHU_BSc_Fall 2024_session 3.pdf")

def ensure_embeddings():
    """Lazily computes chunks and embeddings for Ch.3 PDF"""
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
            logger.error(f"Error creating embeddings for Ch.3: {e}")
            _pdf_embeddings = []
    else:
        _pdf_embeddings = []

def get_assignment_questions() -> List[str]:
    """Return assignment questions for Ch.3"""
    return [
        # Part A: EOQ
        "Part A: Economic Order Quantity (EOQ)\n\nA retailer sells 52,000 units of printer paper per year.\nOrdering cost per order = €150\nAnnual holding cost = 20% of item cost\nItem cost per unit = €2.\n\n1. Compute the EOQ.\n2. Calculate the total annual cost (ordering + holding + purchasing).\n3. Discuss how EOQ changes if order cost halves or holding cost doubles.\n4. What practical factors could make EOQ deviate from optimal levels (e.g., quantity discounts, batch constraints, uncertainty)?",

        # Part B: Safety Inventory
        "Part B: Safety Inventory\n\nWeekly demand for a component is normally distributed with\nMean = 500 units, Standard deviation = 80 units.\nLead time = 3 weeks. Desired cycle service level = 95%.\n\n1. Compute the safety stock.\n2. Find the reorder point.\n3. How would your answer change if lead time variability increases by 50%?\n4. Interpret what a 95% cycle service level means operationally.",

        # Part C: Newsboy Model
        "Part C: Newsboy Model (Single-Period)\n\nA bakery produces croissants daily.\nCost to produce one croissant = €1.\nSelling price = €2.50.\nUnsold croissants are discarded with no salvage value.\nDaily demand is normally distributed with mean = 200, SD = 40.\n\n1. Determine the critical ratio.\n2. Find the z-value and optimal order quantity.\n3. Compute the expected number of unsold and lost sales.\n4. Explain what would change if leftover croissants could be sold next day at €0.50.\n5. Compare the Newsboy and EOQ models. When is each appropriate in real business contexts?",

        # Integrative Task
        "Optional Integrative Task\n\nYou are a supply chain manager at a stationery company.\nUsing EOQ, Safety Inventory, and the Newsboy Model:\n\nIdentify which model applies to your regular office supplies, fast-moving promotional items, and seasonal products.\n\nJustify your reasoning in 200–300 words."
    ]

def answer_query(query: str, assignment_context: str = "", user_email: str = "") -> str:
    """Answer user query for Ch.3 with rate limiting and error handling"""
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
        
        # Find most similar chunk within Ch.3
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
        
        # Ch.3 specific system context
        system_context = (
            "You are a supply chain course assistant specializing in inventory management models. "
            "Use the following context to give helpful hints for the assignment question, but do NOT solve it directly. "
            "Encourage the student to think and guide them to the right concepts or formulas. "
            "Provide data from your understanding if a student asks for it. "
            "If the student asks for a solution, only provide hints and steps, not the final answer.\n"
            "Focus on EOQ (Economic Order Quantity), Safety Stock, and Newsboy Model concepts."
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
        logger.error(f"Critical error in Ch.3 answer_query: {e}")
        return "A technical error occurred. Please contact support if this persists."

def has_pdf():
    """Check if Ch.3 PDF exists"""
    return os.path.exists(get_pdf_path())

def get_section_name():
    """Return the section name"""
    return "Ch.3"