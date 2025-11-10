# Modular Backend - Main entry point for supply chain learning modules
from typing import List, Optional, Dict, Any
from modules.base import (
    set_config, 
    check_rate_limit, 
    record_query, 
    clear_rate_limits, 
    get_rate_limit_status,
    save_student,
    save_answer,
    save_chat,
    get_answers_by_email,
    get_chats_by_email,
    get_all_submissions,
    get_all_students,
    save_grade,
    get_grades_by_email,
    get_latest_grade,
    get_user_queries,
    logger
)

# Import all modules
from modules import ch3, seven_eleven, dragon_fire

# Section registry - maps section names to their modules
SECTION_MODULES = {
    "Ch.3": ch3,
    "7-Eleven Case 2015": seven_eleven,
    "Dragon Fire Case": dragon_fire
}

# Section visibility configuration - set to False to hide from students
SECTION_VISIBILITY = {
    "Ch.3": False,                    # Visible to students
    "7-Eleven Case 2015": False,      # Visible to students  
    "Dragon Fire Case": True,       # Hidden from students
}

# Optional: Section status with reasons (for admin dashboard)
SECTION_STATUS = {
    "Ch.3": {"visible": True, "reason": "Active assignment"},
    "7-Eleven Case 2015": {"visible": True, "reason": "Active case study"},
    "Dragon Fire Case": {"visible": False, "reason": "In development - not ready for students"},
}

def get_available_sections() -> List[str]:
    """Get list of available sections (only visible ones)"""
    return [section for section, visible in SECTION_VISIBILITY.items() 
            if visible and section in SECTION_MODULES]

def get_all_sections() -> List[str]:
    """Get all sections (including hidden ones) - for admin use"""
    return list(SECTION_MODULES.keys())

def get_section_status(section: str) -> Dict[str, Any]:
    """Get detailed status of a section - for admin use"""
    if section in SECTION_STATUS:
        return SECTION_STATUS[section]
    elif section in SECTION_MODULES:
        return {"visible": SECTION_VISIBILITY.get(section, True), "reason": "No specific reason"}
    else:
        return {"visible": False, "reason": "Section not found"}

def set_section_visibility(section: str, visible: bool, reason: str = ""):
    """Admin function to change section visibility"""
    if section in SECTION_MODULES:
        SECTION_VISIBILITY[section] = visible
        SECTION_STATUS[section] = {"visible": visible, "reason": reason}
        logger.info(f"Section '{section}' visibility set to {visible}. Reason: {reason}")
        return True
    return False

def get_assignment_questions(section: str = "Ch.3") -> List[str]:
    """Return assignment questions for a given section"""
    module = SECTION_MODULES.get(section)
    if module and hasattr(module, 'get_assignment_questions'):
        return module.get_assignment_questions()
    else:
        return ["No assignments available for this section yet."]

def answer_query(query: str, assignment_context: str = "", section: str = "Ch.3", user_email: str = "") -> str:
    """Answer user query using the appropriate section module"""
    module = SECTION_MODULES.get(section)
    if module and hasattr(module, 'answer_query'):
        return module.answer_query(query, assignment_context, user_email)
    else:
        return f"Section '{section}' is not available."

# Section-specific functions for Dragon Fire case
def get_disruption_scenarios() -> Dict[int, Dict[str, Any]]:
    """Get disruption scenarios for Dragon Fire case"""
    return dragon_fire.get_disruption_scenarios()

def assign_scenario(student_email: str) -> Dict[str, Any]:
    """Assign a scenario to a student for Dragon Fire case"""
    return dragon_fire.assign_scenario(student_email)

def calculate_volume_metrics(drinks_target: int, powder_per_drink: float, powder_density: float, container_volume: float) -> Dict[str, float]:
    """Calculate volume metrics for Dragon Fire Phase 1"""
    # Call with 4 parameters only to match current app.py call
    return dragon_fire.calculate_volume_metrics(drinks_target, powder_per_drink, powder_density, container_volume)

def get_container_research_info() -> str:
    """Get container research information for students"""
    return dragon_fire.get_container_research_info()

def get_container_specifications_display() -> Dict[str, Any]:
    """Get detailed container specifications for research"""
    return dragon_fire.get_container_specifications_display()

def save_student_container_research(student_email: str, weight_capacity_kg: float, volume_capacity_m3: float, research_notes: str = "") -> Dict[str, Any]:
    """Save and validate student's container research for learning assessment"""
    validation = dragon_fire.validate_student_container_research(weight_capacity_kg, volume_capacity_m3)
    
    return {
        "student_email": student_email,
        "researched_weight_capacity_kg": weight_capacity_kg,
        "researched_volume_capacity_m3": volume_capacity_m3,
        "research_notes": research_notes,
        "validation": validation
    }

def validate_container_research(weight_capacity_kg: float, volume_capacity_m3: float) -> Dict[str, Any]:
    """Validate student's container research and provide feedback"""
    return dragon_fire.validate_student_container_research(weight_capacity_kg, volume_capacity_m3)

def calculate_transport_costs(containers: float, total_kg: float, costs: Dict[str, float]) -> Dict[str, float]:
    """Calculate transportation costs for Dragon Fire Phase 2"""
    return dragon_fire.calculate_transport_costs(containers, total_kg, costs)

def calculate_transport_costs_enhanced(
    containers: float, 
    total_kg: float, 
    total_volume_m3: float,
    costs: Dict[str, float],
    cost_of_capital_annual: float = 0.10
) -> Dict[str, Any]:
    """Enhanced transportation cost calculation with cost of capital and analysis factors"""
    return dragon_fire.calculate_transport_costs_enhanced(
        containers, total_kg, total_volume_m3, costs, cost_of_capital_annual
    )

# Section-specific functions for 7-Eleven case
def validate_numeric_answer(task: str, value: float) -> tuple[bool, str]:
    """Validate numeric answers for 7-Eleven case"""
    return seven_eleven.validate_numeric_answer(task, value)

# Utility functions
def get_section_module(section: str):
    """Get the module for a specific section"""
    return SECTION_MODULES.get(section)

def has_pdf(section: str) -> bool:
    """Check if a section has associated PDF"""
    module = SECTION_MODULES.get(section)
    if module and hasattr(module, 'has_pdf'):
        return module.has_pdf()
    return False

# Backwards compatibility - maintain the global section variables used by app.py
_current_section = 'Ch.3'

def set_current_section(section: str):
    """Set current section for backwards compatibility"""
    global _current_section
    _current_section = section

def get_current_section() -> str:
    """Get current section for backwards compatibility"""
    return _current_section

# Export convenience functions for database operations that need section context
def save_answer_with_section(email: str, question_idx: int, answer: str, section: str = None):
    """Save answer with section context"""
    section = section or _current_section
    save_answer(email, question_idx, answer, section)

def save_chat_with_section(email: str, question: str, bot_response: str, section: str = None):
    """Save chat with section context"""
    section = section or _current_section
    save_chat(email, question, bot_response, section)

def save_grade_with_section(email: str, question_idx: int, grade: str, section: str = None):
    """Save grade with section context"""
    section = section or _current_section
    save_grade(email, question_idx, grade, section)

def get_answers_by_email_with_section(email: str, section: str = None):
    """Get answers with section context"""
    section = section or _current_section
    return get_answers_by_email(email, section)

def get_chats_by_email_with_section(email: str, section: str = None):
    """Get chats with section context"""
    section = section or _current_section
    return get_chats_by_email(email, section)

def get_grades_by_email_with_section(email: str, section: str = None):
    """Get grades with section context"""
    section = section or _current_section
    return get_grades_by_email(email, section)

def get_latest_grade_with_section(email: str, question_idx: int, section: str = None):
    """Get latest grade with section context"""
    section = section or _current_section
    return get_latest_grade(email, question_idx, section)

# Expose _user_queries for admin dashboard compatibility
_user_queries = get_user_queries()