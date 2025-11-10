# Dragon Fire Case Module - Interactive supply chain design case
import hashlib
import openai
from typing import List, Dict, Any
from .base import (
    logger, check_rate_limit, record_query
)

def get_assignment_questions() -> List[str]:
    """Return assignment questions for Dragon Fire Case"""
    return [
        "Phase 1: Product & Market Analysis\n\nDesign the supply chain for Dragon Fire energy drink from Austria to China.\n\n**Case Background**: Blue Dragon (Austria) wants to launch Dragon Fire energy drink in China's high-end market (bars, clubs, restaurants). The product uses coca leaf powder (not caffeine) and sells for 25 Yuan (~3€) per drink.\n\n**Your Task**: Complete the product analysis:\n\n1. **Volume Estimation**: If Blue Dragon targets 1 million drinks in Year 1, and each drink needs 10g of powder, calculate:\n   - Total powder needed (kg)\n   - Estimated volume in cubic meters (research appropriate powder density)\n   - Number of standard shipping containers needed (research container sizes)\n\n2. **Product Characteristics**: Identify 3 factors about the powder that will impact transportation choices (consider: shelf life, temperature sensitivity, regulatory restrictions, value density).",

        "Phase 2: Transportation Mode Comparison\n\nCompare different ways to get Dragon Fire powder from Austria to China.\n\n**Available Options**:\n- **Sea Freight**: 30-35 days, $2,000-3,000 per container\n- **Air Freight**: 3-5 days, $8-12 per kg\n- **Rail Freight**: 18-25 days, $4,000-5,000 per container\n- **Multimodal**: Combinations of above\n\n**Your Analysis**:\n\n1. **Cost Calculation**: For your powder volume from Phase 1, calculate the transportation cost for each mode. Show your work.\n\n2. **Mode Evaluation**: Based on the following factors, choose your preferred transportation mode and justify with 3 specific reasons:\n   - Cost efficiency\n   - Speed to market\n   - Reliability\n   - Risk level\n   - Environmental impact",

        "Phase 3: Supply Chain Design\n\nDesign your complete China operation.\n\n**Key Decisions to Make**:\n\n1. **Entry Port Selection**:\n   - Compare Shanghai, Ningbo, and Shenzhen ports\n   - Consider: proximity to target markets, port efficiency, inland transport costs\n   - Choose one port and justify your selection\n\n2. **Mixing/Bottling Facility Location**:\n   - Where in China will you mix powder with water and bottle the drinks?\n   - Consider: labor costs, regulations, proximity to customers, water quality\n   - Identify 2-3 potential cities and rank them\n\n3. **Distribution Strategy**:\n   - How will finished drinks reach bars/clubs in major Chinese cities?\n   - Design your distribution network (regional hubs, direct delivery, etc.)\n   - Calculate approximate delivery radius and frequency\n\n4. **Inventory Planning**:\n   - How much safety stock of powder should you maintain?\n   - Where should inventory be held (port, factory, regional centers)?\n   - Consider seasonal demand variations and lead times\n\n**Deliverable**: Create a simple supply chain map showing: Austria production → transport → China port → mixing facility → distribution → end customers",

        "Phase 4: Risk Management & Scenario Planning\n\nYour supply chain faces a real-world disruption. How will you respond?\n\n**Your Scenario**: You will be assigned one of three possible disruptions. Develop a comprehensive response plan for your assigned scenario.\n\n**Possible Disruptions**:\n1. **Suez Canal Blockage**: A major ship blocks the canal for 3 weeks (like Ever Given 2021)\n2. **COVID-19 Port Closure**: Shanghai port closes for 2 weeks due to outbreak\n3. **Regulatory Challenge**: China restricts coca leaf imports pending safety review\n\n**Your Response Plan** (for your assigned disruption):\n1. **Immediate Actions** (first 48 hours)\n2. **Short-term Mitigation** (1-4 weeks)\n3. **Long-term Adaptation** (1-6 months)\n4. **Cost Impact** (estimated additional costs)\n\n**Risk Prevention**: Design 2 proactive measures to reduce vulnerability to this type of disruption in the future."
    ]

def get_disruption_scenarios() -> Dict[int, Dict[str, Any]]:
    """Return the three disruption scenarios for Phase 4"""
    return {
        1: {
            "title": "Suez Canal Blockage",
            "description": "A major ship blocks the Suez Canal for 3 weeks (like Ever Given in 2021). This affects all sea freight shipments from Europe to Asia.",
            "impacts": [
                "Sea freight delays of 3+ weeks",
                "Alternative routes around Africa add 2 weeks and 20% cost",
                "Air freight capacity becomes scarce and expensive",
                "Customer inventory runs low"
            ]
        },
        2: {
            "title": "COVID-19 Port Closure",
            "description": "Shanghai port closes for 2 weeks due to COVID outbreak. This is China's largest port handling 25% of container traffic.",
            "impacts": [
                "All Shanghai shipments diverted to other ports",
                "Secondary ports become congested",
                "Inland transport costs increase from alternative ports",
                "Customs clearance delays at backup ports"
            ]
        },
        3: {
            "title": "Regulatory Challenge",
            "description": "China suddenly restricts coca leaf imports pending safety review. This affects all coca-based products entering China.",
            "impacts": [
                "All Dragon Fire shipments blocked at border",
                "Need alternative product formulation",
                "Existing inventory may be confiscated",
                "Market launch delayed indefinitely"
            ]
        }
    }

def assign_scenario(student_email: str) -> Dict[str, Any]:
    """Assign a scenario to a student based on their email hash"""
    scenarios = get_disruption_scenarios()
    # Use hash of email to ensure same student always gets same scenario
    hash_value = int(hashlib.md5(student_email.encode()).hexdigest(), 16)
    scenario_number = (hash_value % 3) + 1
    return scenarios[scenario_number]

def calculate_volume_metrics(drinks_target: int, powder_per_drink: float, powder_density: float, container_volume: float) -> Dict[str, float]:
    """Calculate volume metrics for Phase 1"""
    total_powder_kg = (drinks_target * powder_per_drink) / 1000
    total_volume_m3 = (total_powder_kg / powder_density) / 1000
    containers_needed = total_volume_m3 / container_volume
    
    return {
        "total_powder_kg": total_powder_kg,
        "total_volume_m3": total_volume_m3,
        "containers_needed": containers_needed
    }

def calculate_transport_costs(containers: float, total_kg: float, costs: Dict[str, float]) -> Dict[str, float]:
    """Calculate transportation costs for Phase 2"""
    sea_total = containers * costs.get('sea_per_container', 0)
    air_total = total_kg * costs.get('air_per_kg', 0)
    rail_total = containers * costs.get('rail_per_container', 0)
    
    return {
        "sea_total": sea_total,
        "air_total": air_total,
        "rail_total": rail_total
    }

def answer_query(query: str, assignment_context: str = "", user_email: str = "") -> str:
    """Answer user query for Dragon Fire case with rate limiting and error handling"""
    try:
        # Check rate limits
        if user_email:
            allowed, message = check_rate_limit(user_email)
            if not allowed:
                return f"{message}. Please try again later."
        
        # No PDF context for Dragon Fire case - it's interactive
        
        # Prompt for hints only, not full solutions
        prompt = (
            f"Assignment Question: {assignment_context}\nStudent Query: {query}\nHint:"
        )
        
        # Dragon Fire specific system context
        system_context = (
            "You are a supply chain course assistant specializing in international supply chain design. "
            "Use the following context to give helpful hints for the assignment question, but do NOT solve it directly. "
            "Encourage the student to think and guide them to the right concepts or formulas. "
            "Provide data from your understanding if a student asks for it. "
            "If the student asks for a solution, only provide hints and steps, not the final answer.\n"
            "Dragon Fire Case Context: Blue Dragon (Austria) is launching an energy drink in China's high-end market. "
            "Key facts: 25 Yuan price point, coca leaf-based (not caffeine), powder shipped from Austria, "
            "mixed with water in China, distributed to bars/clubs/restaurants. "
            "Transportation options: Sea (30-35 days, $2-3k/container), Air (3-5 days, $8-12/kg), "
            "Rail (18-25 days, $4-5k/container). Main Chinese ports: Shanghai, Ningbo, Shenzhen. "
            "Consider: regulatory risks of coca leaf products, temperature sensitivity, premium market requirements, "
            "supply chain disruptions (Suez Canal, port closures, etc.). Guide students through systematic analysis "
            "of volume calculations, mode selection, risk management, and total cost optimization."
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
        logger.error(f"Critical error in Dragon Fire answer_query: {e}")
        return "A technical error occurred. Please contact support if this persists."

def has_pdf():
    """Dragon Fire case has no PDF - it's interactive"""
    return False

def get_section_name():
    """Return the section name"""
    return "Dragon Fire Case"