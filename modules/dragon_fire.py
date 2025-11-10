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
        "Phase 1: Market and Volume Estimation\n\nDesign the supply chain for Dragon Fire energy drink from Germany to China.\n\n**Case Background**: Blue Dragon (German startup) wants to launch Dragon Fire energy drink in China as their first market. Initially targeting bars and restaurants only (no supermarkets yet) at 25 Yuan (~3.30€) per drink, with future supermarket price of 10 Yuan (~1.30€). Two variants: with sugar and sugar-free.\n\n**Your Task**: Conduct a Market and volume estimate:\n\n1. **Sales Estimation**: Based on the case description, you need to provide an estimate of how many units of drinks Blue Dragon will sell in Year 1.\n   You also need to provide a reasonable estimate for how many grams of powder each unit will require.\n\n"
        "2. Aparrt from weight, volume is also essential, so the density of the powder is needed to calculate space requirements.\n   Please use the tool to derive:\n   - Total powder needed (kg)\n   - Estimated weight and volume limit of a 40ft container in kg payload and in cubic meters (research appropriate powder density)\n   - Number of standard shipping containers needed when using rail or sea transportation",

        "Phase 2: Transportation Mode Comparison\n\nCompare different ways to get Dragon Fire powder from Germany to China.\n\n**Available Options**:\n- **Sea Freight**: 30 days, €400 per 40ft container\n- **Air Freight**: 3 days, €1.50 per kg\n- **Rail Freight**: 15 days, €3,000 per 40ft container\n- **Multimodal**: Combinations of above\n\n**Your Analysis**:\n\n1. **Cost Calculation**: For your powder volume from Phase 1, calculate the transportation cost for each mode. Show your work in Euros.\n\n2. **Mode Evaluation**: Given this is a startup with unproven market demand, choose your preferred transportation mode and justify with 3 specific reasons considering:\n   - Cost efficiency vs. market uncertainty\n   - Speed to market for product launch\n   - Financial risk management\n   - Flexibility for demand changes",

        "Phase 3: Supply Chain Design\n\nDesign your complete China operation for this startup market entry.\n\n**Key Decisions to Make**:\n\n1. **Entry Port Selection**:\n   - Compare Shanghai, Ningbo, and Shenzhen ports\n   - Consider: proximity to target bar/restaurant markets, port efficiency, inland transport costs\n   - Choose one port and justify your selection\n\n2. **Mixing/Bottling Facility Location**:\n   - Where in China will you mix powder with water and bottle/can the drinks?\n   - Consider: labor costs, regulations, proximity to bars/restaurants, water quality, startup budget constraints\n   - Identify 2-3 potential cities and rank them\n\n3. **Distribution Strategy**:\n   - How will finished drinks reach bars/clubs/restaurants in major Chinese cities?\n   - Design your distribution network considering limited initial market (no supermarkets)\n   - Calculate approximate delivery radius and frequency for bar/restaurant channel\n\n4. **Inventory Planning for Startup**:\n   - How much safety stock should a startup maintain with unproven demand?\n   - Where should inventory be held (port, factory, regional centers)?\n   - Consider cash flow constraints and demand uncertainty\n\n**Deliverable**: Create a simple supply chain map showing: Germany production → transport → China port → mixing facility → distribution → bars/restaurants",

        "Phase 4: Risk Management & Scenario Planning\n\nYour startup supply chain faces a real-world disruption. How will you respond?\n\n**Your Scenario**: You will be assigned one of three possible disruptions. Develop a comprehensive response plan for your assigned scenario.\n\n**Possible Disruptions**:\n1. **Suez Canal Blockage**: A major ship blocks the canal for 3 weeks (like Ever Given 2021)\n2. **Disease Outbreak**: All ports except the Shanghai port close for 2 weeks due to a disease outbreak\n3. **Regulatory Challenge**: China prohibits the import of sugar, which is contained in the powder, pending food safety review\n\n**Your Response Plan** (for your assigned disruption):\n1. **Immediate Actions** (first 48 hours) - consider startup's limited resources\n2. **Short-term Mitigation** (1-4 weeks) - cash flow and customer retention focus\n3. **Long-term Adaptation** (1-6 months) - strategic pivots for startup survival\n4. **Cost Impact** (estimated additional costs and impact on startup budget)\n\n**Risk Prevention**: Design 2 proactive measures to reduce vulnerability considering startup constraints and limited market presence."
    ]

def get_disruption_scenarios() -> Dict[int, Dict[str, Any]]:
    """Return the three disruption scenarios for Phase 4"""
    return {
        1: {
            "title": "Suez Canal Blockage",
            "description": "A major ship blocks the Suez Canal for 3 weeks (like Ever Given in 2021). This affects all sea freight shipments from Europe to Asia.",
            "impacts": [
                "Sea freight delays of 3+ weeks",
                "Alternative routes around Africa add 2 weeks and significant cost",
                "Air freight capacity becomes scarce and expensive",
                "Startup's limited inventory runs out, threatening market launch"
            ]
        },
        2: {
            "title": "Disease Outbreak",
            "description": "All ports except the Shanghai port close for 2 weeks due to a disease outbreak. This forces all shipments to be redirected to Shanghai.",
            "impacts": [
                "All shipments diverted to Shanghai port only",
                "Shanghai port becomes heavily congested with increased traffic",
                "Longer waiting times and increased port handling costs",
                "Startup's limited cash flow strained by additional costs and delays"
            ]
        },
        3: {
            "title": "Regulatory Challenge", 
            "description": "China prohibits the import of sugar, which is contained in the powder, pending food safety review. This affects all imported products containing sugar.",
            "impacts": [
                "All Dragon Fire shipments with sugar variant blocked at border",
                "Need to reformulate products or obtain new certifications",
                "Existing sugar-containing inventory held in customs or rejected",
                "Market launch delayed, affecting startup's funding and timeline"
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

def get_powder_density_guidance() -> Dict[str, Any]:
    """Provide guidance for powder density research"""
    return {
        "typical_ranges": {
            "protein_powder": "400-600 kg/m³",
            "sugar_powder": "600-800 kg/m³", 
            "vitamin_mineral_mix": "300-500 kg/m³",
            "energy_drink_powder_mix": "450-650 kg/m³"
        },
        "factors_affecting_density": [
            "Particle size and distribution",
            "Moisture content", 
            "Compaction during transport",
            "Ingredient composition (sugar vs sugar-free)",
            "Processing method (spray-dried, freeze-dried, etc.)"
        ],
        "research_tips": [
            "Consider the specific ingredients in energy drink powder",
            "Account for both sugar and sugar-free variants",
            "Look for industry standards for beverage powder densities",
            "Consider packaging method (loose vs compressed)"
        ],
        "recommended_range": {
            "min_kg_m3": 450,
            "max_kg_m3": 650,
            "typical_kg_m3": 550
        }
    }

def get_container_specifications() -> Dict[str, Any]:
    """Return standard 40ft container specifications"""
    return {
        "container_type": "40ft High Cube Container",
        "external_dimensions": {
            "length_m": 12.192,
            "width_m": 2.438,
            "height_m": 2.896
        },
        "internal_dimensions": {
            "length_m": 12.032,
            "width_m": 2.352,
            "height_m": 2.385
        },
        "capacity": {
            "max_payload_kg": 26000,  # Maximum weight capacity
            "max_volume_m3": 67.3,    # Internal volume
            "tare_weight_kg": 4200    # Empty container weight
        },
        "notes": [
            "Payload capacity may vary by shipping line",
            "Actual usable volume depends on cargo packaging",
            "Weight distribution must comply with axle load limits"
        ]
    }

def calculate_volume_metrics_with_estimates(
    drinks_estimate: int, 
    powder_per_drink_grams: float, 
    powder_density_kg_m3: float,
    container_weight_limit_kg: float = None,
    container_volume_limit_m3: float = None
) -> Dict[str, Any]:
    """Calculate volume metrics allowing students to input their own container research"""
    
    # Get standard container specifications as default
    standard_specs = get_container_specifications()["capacity"]
    
    # Use student research or defaults
    weight_limit = container_weight_limit_kg if container_weight_limit_kg else standard_specs["max_payload_kg"]
    volume_limit = container_volume_limit_m3 if container_volume_limit_m3 else standard_specs["max_volume_m3"]
    
    # Calculate total requirements
    total_powder_kg = (drinks_estimate * powder_per_drink_grams) / 1000
    total_volume_m3 = total_powder_kg / powder_density_kg_m3
    
    # Calculate containers needed based on both constraints
    containers_by_weight = total_powder_kg / weight_limit
    containers_by_volume = total_volume_m3 / volume_limit
    containers_needed = max(containers_by_weight, containers_by_volume)
    
    # Determine limiting factor
    limiting_factor = "weight" if containers_by_weight > containers_by_volume else "volume"
    
    return {
        "input_parameters": {
            "drinks_estimate": drinks_estimate,
            "powder_per_drink_grams": powder_per_drink_grams,
            "powder_density_kg_m3": powder_density_kg_m3,
            "container_weight_limit_kg": weight_limit,
            "container_volume_limit_m3": volume_limit,
            "used_student_research": {
                "weight_limit": container_weight_limit_kg is not None,
                "volume_limit": container_volume_limit_m3 is not None
            }
        },
        "calculations": {
            "total_powder_kg": round(total_powder_kg, 2),
            "total_volume_m3": round(total_volume_m3, 2),
            "containers_by_weight": round(containers_by_weight, 2),
            "containers_by_volume": round(containers_by_volume, 2),
            "containers_needed": round(containers_needed, 2),
            "limiting_factor": limiting_factor
        },
        "container_utilization": {
            "weight_utilization_percent": round((total_powder_kg / containers_needed / weight_limit) * 100, 1),
            "volume_utilization_percent": round((total_volume_m3 / containers_needed / volume_limit) * 100, 1)
        },
        "standard_container_reference": standard_specs
    }

def calculate_volume_metrics(drinks_target: int, powder_per_drink: float, powder_density: float, container_volume: float) -> Dict[str, Any]:
    """Calculate volume metrics for Phase 1 - backward compatible with existing app calls
    
    Args:
        drinks_target: Number of drinks estimated for Year 1 (from app.py)
        powder_per_drink: Grams of powder needed per drink (from app.py) 
        powder_density: Density of powder in kg/L (from app.py)
        container_volume: Container volume in m³ (from app.py)
    """
    
    # Get standard container specifications
    container_specs = get_container_specifications()["capacity"]
    
    # Convert powder_density from kg/L to kg/m³ if needed
    # Note: kg/L = 1000 * kg/m³, so if input is kg/L, multiply by 1000
    powder_density_kg_m3 = powder_density * 1000  # Convert kg/L to kg/m³
    
    # Calculate total requirements
    total_powder_kg = (drinks_target * powder_per_drink) / 1000  # Convert grams to kg
    total_volume_m3 = total_powder_kg / powder_density_kg_m3
    
    # Calculate containers needed based on both weight and volume constraints
    containers_by_weight = total_powder_kg / container_specs["max_payload_kg"]
    containers_by_volume = total_volume_m3 / container_volume
    containers_needed = max(containers_by_weight, containers_by_volume)  # Limiting factor
    
    return {
        "drinks_target": drinks_target,
        "powder_per_drink": powder_per_drink,
        "total_powder_kg": total_powder_kg,
        "total_volume_m3": total_volume_m3,
        "powder_density_used": powder_density_kg_m3,
        "container_specs": {
            "max_payload_kg": container_specs["max_payload_kg"],
            "max_volume_m3": container_volume,
            "tare_weight_kg": container_specs["tare_weight_kg"]
        },
        "containers_by_weight": containers_by_weight,
        "containers_by_volume": containers_by_volume,
        "containers_needed": containers_needed,
        "limiting_factor": "weight" if containers_by_weight > containers_by_volume else "volume"
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
            "Dragon Fire Case Context: Blue Dragon (German startup) is launching Dragon Fire energy drink in China as their first market. "
            "Key facts: 25 Yuan price point for bars/restaurants (~3.30€), future supermarket price 10 Yuan (~1.30€), "
            "powder produced in Germany and shipped to China, mixed with water and bottled/canned in China, "
            "two variants (with sugar and sugar-free), distributed to bars/clubs/restaurants initially (no supermarkets yet). "
            "Transportation costs: Air cargo €1.50/kg (3 days), Sea freight €400 per 40ft container (30 days), "
            "Rail transport €3,000 per 40ft container (15 days). Main Chinese ports: Shanghai, Ningbo, Shenzhen. "
            "For Phase 1: Students must estimate their own sales targets and powder requirements per drink. "
            "Guide them to consider market research methods, comparable products, and realistic startup projections. "
            "For powder density, typical energy drink powders range 450-650 kg/m³. Standard 40ft containers: "
            "26,000 kg payload capacity, 67.3 m³ volume. Students should research and justify their estimates. "
            "Consider: market entry risks, regulatory requirements, temperature sensitivity, "
            "premium market positioning, supply chain disruptions. Guide students through systematic analysis "
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