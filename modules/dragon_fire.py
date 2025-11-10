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

        "Phase 2: Transportation Mode Comparison\n\nCompare different ways to get Dragon Fire powder from Germany to China.\n\n**Available Options**:\n- **Sea Freight**: 30 days, €400 per 40ft container\n- **Air Freight**: 3 days, €1.50 per kg\n- **Rail Freight**: 15 days, €3,000 per 40ft container\n- **Multimodal**: Combinations of above\n\n**Your Analysis**:\n\n**Calculate and Compare**: Using the transportation rates above:\n- Calculate transportation cost for each mode\n- Calculate cost of capital (inventory holding cost during transit)\n- Consider total cost = transportation cost + cost of capital\n\n**Mode Evaluation**: Evaluate each transportation mode based on:\n- **Cost**: Total cost per kg\n- **Speed to Market**: Time to reach customers\n- **Reliability**: Service consistency and predictability\n- **Risk Level**: Potential disruptions and vulnerabilities\n- **Environmental Impact**: CO2 emissions and sustainability",

        "Phase 3: Supply Chain Design\n\nDesign your complete China operation for this startup market entry.\n\n**Key Decisions to Make**:\n\n1. **Entry Port Selection**:\n   - Compare Shanghai, Ningbo, and Shenzhen ports\n   - Consider: proximity to target bar/restaurant markets, port efficiency, inland transport costs\n   - Choose one port and justify your selection\n\n2. **Mixing/Bottling Facility Location**:\n   - Where in China will you mix powder with water and bottle/can the drinks?\n   - Consider: labor costs, regulations, proximity to bars/restaurants, water quality, startup budget constraints\n   - Identify 2-3 potential cities and rank them.",

        "Phase 4: Risk Management & Scenario Planning\n\nYour startup supply chain faces a real-world disruption. How will you respond?\n\nDevelop a comprehensive response plan for the disruptive scenario given below.\n\n**Your Response Plan** (for your assigned disruption):\n1. **Immediate Actions** (first 48 hours) - consider startup's limited resources\n2. **Short-term Mitigation** (1-4 weeks) - cash flow and customer retention focus\n3. **Long-term Adaptation** (1-6 months) - strategic pivots for startup survival\n4. **Cost Impact** (estimated additional costs and impact on startup budget)\n\n**Risk Prevention**: Design 2 proactive measures to reduce vulnerability considering startup constraints and limited market presence."
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

def get_container_research_info() -> str:
    """Return formatted container information for student research display"""
    specs = get_container_specifications_display()
    
    info = """
##  Container Research Guide

### Standard 40ft High Cube Container Specifications:

**Weight Limits:**
- **Maximum Payload:** 26,000 kg (what you can actually ship)
- **Container Weight:** 4,200 kg (empty container)
- **Gross Weight:** 30,400 kg (total maximum)

**Volume Limits:**
- **Internal Volume:** 67.3 m³
- **Dimensions:** 12.0m × 2.4m × 2.4m (L × W × H)

### Research Tips:
- Different shipping lines may have slightly different weight limits (24,000-27,000 kg)
- Standard containers (58.3 m³) vs High Cube containers (67.3 m³)
- Consider packaging weight in your calculations
- Energy drink powder density typically: 450-650 kg/m³

### Your Task:
Research and input the weight and volume limits you find for 40ft containers, then calculate how many containers your powder shipment will need.
"""
    return info

def get_container_specifications_display() -> Dict[str, Any]:
    """Return container specifications formatted for student display and research"""
    return {
        "standard_40ft_container": {
            "type": "40ft High Cube Container (Most Common)",
            "weight_limits": {
                "max_payload_kg": 26000,
                "tare_weight_kg": 4200,
                "gross_weight_kg": 30400,
                "note": "Payload = what you can actually ship"
            },
            "volume_limits": {
                "max_volume_m3": 67.3,
                "length_m": 12.032,
                "width_m": 2.352,
                "height_m": 2.385,
                "note": "Internal dimensions for cargo"
            },
            "research_guidance": {
                "weight_research": "Look up shipping line specifications - may vary 24,000-27,000 kg",
                "volume_research": "Standard vs High Cube containers differ in height",
                "practical_note": "Actual usable space depends on packaging and cargo type"
            }
        },
        "alternative_containers": {
            "40ft_standard": {"payload_kg": 26000, "volume_m3": 58.3},
            "20ft_container": {"payload_kg": 21000, "volume_m3": 28.0}
        },
        "student_research_tips": [
            "Check multiple shipping line websites for container specs",
            "Consider weight distribution and loading constraints", 
            "Account for packaging weight in your calculations",
            "Research shows typical energy drink powder density: 450-650 kg/m³"
        ]
    }

def validate_student_container_research(weight_capacity_kg: float, volume_capacity_m3: float) -> Dict[str, Any]:
    """Validate student's container research against standard specifications"""
    standard_specs = get_container_specifications()["capacity"]
    
    # Reasonable ranges based on real container specifications
    weight_range = {"min": 20000, "max": 30000, "typical_min": 24000, "typical_max": 27000}
    volume_range = {"min": 50, "max": 80, "typical_min": 58, "typical_max": 68}
    
    weight_reasonable = weight_range["min"] <= weight_capacity_kg <= weight_range["max"]
    volume_reasonable = volume_range["min"] <= volume_capacity_m3 <= volume_range["max"]
    
    weight_typical = weight_range["typical_min"] <= weight_capacity_kg <= weight_range["typical_max"]
    volume_typical = volume_range["typical_min"] <= volume_capacity_m3 <= volume_range["typical_max"]
    
    return {
        "weight_analysis": {
            "value": weight_capacity_kg,
            "reasonable": weight_reasonable,
            "typical": weight_typical,
            "feedback": get_weight_feedback(weight_capacity_kg, weight_range),
            "standard_reference": standard_specs["max_payload_kg"]
        },
        "volume_analysis": {
            "value": volume_capacity_m3,
            "reasonable": volume_reasonable,
            "typical": volume_typical,
            "feedback": get_volume_feedback(volume_capacity_m3, volume_range),
            "standard_reference": standard_specs["max_volume_m3"]
        },
        "overall_quality": {
            "both_reasonable": weight_reasonable and volume_reasonable,
            "both_typical": weight_typical and volume_typical,
            "research_score": calculate_research_score(weight_reasonable, volume_reasonable, weight_typical, volume_typical)
        }
    }

def get_weight_feedback(weight_kg: float, weight_range: Dict[str, float]) -> str:
    """Generate feedback for weight capacity research"""
    if weight_kg < weight_range["min"]:
        return "Too low - Check for maximum payload capacity, not container weight"
    elif weight_kg > weight_range["max"]:
        return "Too high - This exceeds typical container weight limits"
    elif weight_range["typical_min"] <= weight_kg <= weight_range["typical_max"]:
        return "Excellent - This is within typical range for 40ft containers"
    else:
        return "Acceptable - Consider checking multiple shipping line specifications"

def get_volume_feedback(volume_m3: float, volume_range: Dict[str, float]) -> str:
    """Generate feedback for volume capacity research"""
    if volume_m3 < volume_range["min"]:
        return "Too low - Check if you found standard container vs high cube"
    elif volume_m3 > volume_range["max"]:
        return "Too high - This exceeds typical container volumes"
    elif volume_range["typical_min"] <= volume_m3 <= volume_range["typical_max"]:
        return "Excellent - Correct range for 40ft containers"
    else:
        return "Acceptable - Consider standard (58m³) vs high cube (67m³) containers"

def calculate_research_score(weight_reasonable: bool, volume_reasonable: bool, weight_typical: bool, volume_typical: bool) -> str:
    """Calculate overall research quality score"""
    if weight_typical and volume_typical:
        return "A - Excellent research with typical values"
    elif weight_reasonable and volume_reasonable:
        return "B - Good research within acceptable ranges"
    elif weight_reasonable or volume_reasonable:
        return "C - Partial success, review the other specification"
    else:
        return "D - Please review your research sources"

def calculate_volume_metrics(drinks_target: int, powder_per_drink: float, powder_density: float, container_volume: float, container_weight_capacity: float = None) -> Dict[str, Any]:
    """Calculate volume metrics for Phase 1 - backward compatible with existing app calls
    
    Args:
        drinks_target: Number of drinks estimated for Year 1 (from app.py)
        powder_per_drink: Grams of powder needed per drink (from app.py) 
        powder_density: Density of powder in kg/L (from app.py)
        container_volume: Container volume in m³ (from app.py)
        container_weight_capacity: Optional weight capacity in kg (new parameter)
    """
    
    # Get standard container specifications
    container_specs = get_container_specifications()["capacity"]
    
    # Use provided weight capacity or default
    weight_capacity = container_weight_capacity if container_weight_capacity else container_specs["max_payload_kg"]
    
    # Convert powder_density from kg/L to kg/m³ if needed
    # Note: kg/L = 1000 * kg/m³, so if input is kg/L, multiply by 1000
    powder_density_kg_m3 = powder_density * 1000  # Convert kg/L to kg/m³
    
    # Calculate total requirements
    total_powder_kg = (drinks_target * powder_per_drink) / 1000  # Convert grams to kg
    total_volume_m3 = total_powder_kg / powder_density_kg_m3
    
    # Calculate containers needed based on both weight and volume constraints
    containers_by_weight = total_powder_kg / weight_capacity
    containers_by_volume = total_volume_m3 / container_volume
    containers_needed = max(containers_by_weight, containers_by_volume)  # Limiting factor
    
    # Determine limiting factor and utilization
    limiting_factor = "weight" if containers_by_weight > containers_by_volume else "volume"
    weight_utilization = (total_powder_kg / containers_needed / weight_capacity) * 100
    volume_utilization = (total_volume_m3 / containers_needed / container_volume) * 100
    
    return {
        # Backward compatibility - flat structure for existing app.py
        "total_powder_kg": round(total_powder_kg, 2),
        "total_volume_m3": round(total_volume_m3, 3),
        "containers_needed": round(containers_needed, 2),
        "containers_by_weight": round(containers_by_weight, 2),
        "containers_by_volume": round(containers_by_volume, 2),
        "limiting_factor": limiting_factor,
        "powder_density_used": powder_density_kg_m3,
        
        # Enhanced structure for future use
        "inputs": {
            "drinks_target": drinks_target,
            "powder_per_drink_grams": powder_per_drink,
            "powder_density_kg_L": powder_density,
            "container_volume_m3": container_volume,
            "container_weight_capacity_kg": weight_capacity,
            "used_custom_weight_capacity": container_weight_capacity is not None
        },
        "calculations": {
            "total_powder_kg": round(total_powder_kg, 2),
            "total_volume_m3": round(total_volume_m3, 3),
            "powder_density_kg_m3": powder_density_kg_m3,
            "containers_by_weight": round(containers_by_weight, 2),
            "containers_by_volume": round(containers_by_volume, 2),
            "containers_needed": round(containers_needed, 2),
            "limiting_factor": limiting_factor
        },
        "utilization": {
            "weight_utilization_percent": round(weight_utilization, 1),
            "volume_utilization_percent": round(volume_utilization, 1),
            "efficiency_note": f"Container is limited by {limiting_factor}"
        },
        "container_research": {
            "weight_capacity_used": weight_capacity,
            "volume_capacity_used": container_volume,
            "standard_reference": {
                "standard_weight_capacity": container_specs["max_payload_kg"],
                "standard_volume_capacity": container_specs["max_volume_m3"]
            }
        }
    }

def get_phase2_guidance() -> Dict[str, Any]:
    """Provide guidance for Phase 2 transportation mode analysis"""
    return {
        "transportation_data": {
            "sea_freight": {
                "cost": "€400 per 40ft container",
                "transit_time": "30 days",
                "notes": "Most economical for large volumes"
            },
            "air_freight": {
                "cost": "€1.50 per kg",
                "transit_time": "3 days", 
                "notes": "Fastest but most expensive"
            },
            "rail_freight": {
                "cost": "€3,000 per 40ft container",
                "transit_time": "15 days",
                "notes": "Balance of cost and speed"
            }
        },
        "wacc_guidance": {
            "typical_ranges": {
                "startup_wacc": "12-20% annually",
                "established_company": "6-12% annually",
                "recommended_assumption": "15% for Dragon Fire startup"
            },
            "calculation_steps": [
                "1. Estimate your powder production cost per kg (€8-15 typical)",
                "2. Choose annual WACC rate (12-20% for startups)",
                "3. Calculate daily cost: (WACC ÷ 365) × Total Inventory Value",
                "4. Multiply by transit days for each transportation mode"
            ]
        },
        "evaluation_framework": {
            "cost": {
                "factors": ["Transportation cost", "Cost of capital", "Total cost per kg"],
                "questions": ["Which mode has lowest total cost?", "How sensitive to volume changes?"]
            },
            "speed_to_market": {
                "factors": ["Transit time", "Market opportunity cost", "Customer expectations"],
                "questions": ["How critical is launch timing?", "What's the cost of delay?"]
            },
            "reliability": {
                "factors": ["Weather dependency", "Infrastructure quality", "Service frequency"],
                "questions": ["Which mode has most predictable delivery?", "Backup options?"]
            },
            "risk_level": {
                "factors": ["Geopolitical risks", "Route disruptions", "Capacity constraints"],
                "questions": ["What could go wrong?", "How would you mitigate risks?"]
            },
            "environmental_impact": {
                "factors": ["CO2 emissions per kg", "Sustainability goals", "Customer perception"],
                "questions": ["Does environmental impact matter for brand?", "Future regulations?"]
            }
        },
        "analysis_instructions": {
            "required_inputs": [
                "Number of containers (from Phase 1)",
                "Total weight in kg (from Phase 1)",
                "Total volume in m³ (from Phase 1)",
                "WACC rate assumption (12-20% for startups)"
            ],
            "student_task": [
                "Calculate transportation costs for each mode using given rates",
                "Calculate cost of capital based on your WACC assumption",
                "Evaluate all modes against 5 factors: Cost, Speed, Reliability, Risk, Environment",
                "Choose preferred mode with 3 specific justifications"
            ]
        }
    }

def collect_phase2_inputs(
    containers: float,
    total_weight_kg: float, 
    total_volume_m3: float,
    wacc_rate: float
) -> Dict[str, Any]:
    """Collect and validate Phase 2 inputs for student analysis"""
    
    # Basic validation
    errors = []
    if containers <= 0:
        errors.append("Number of containers must be positive")
    if total_weight_kg <= 0:
        errors.append("Total weight must be positive")
    if total_volume_m3 <= 0:
        errors.append("Total volume must be positive")
    if not (0.05 <= wacc_rate <= 0.30):  # 5% to 30%
        errors.append("WACC rate should be between 5% and 30% (0.05 to 0.30)")
    
    return {
        "inputs": {
            "containers": containers,
            "total_weight_kg": total_weight_kg,
            "total_volume_m3": total_volume_m3, 
            "wacc_rate": wacc_rate
        },
        "validation": {
            "valid": len(errors) == 0,
            "errors": errors
        },
        "transportation_rates": {
            "sea_freight": "€400 per 40ft container, 30 days transit",
            "air_freight": "€1.50 per kg, 3 days transit",
            "rail_freight": "€3,000 per 40ft container, 15 days transit"
        },
        "next_steps": [
            "Calculate transportation cost for each mode using the given rates",
            "Calculate cost of capital based on your WACC assumption", 
            "Evaluate all modes against the 5 factors: Cost, Speed, Reliability, Risk, Environment",
            "Choose your preferred transportation mode with 3 specific justifications"
        ]
    }

def calculate_transport_costs(containers: float, total_kg: float, costs: Dict[str, float]) -> Dict[str, float]:
    """Simple transportation costs calculation - kept for backward compatibility"""
    sea_total = containers * costs.get('sea_per_container', 400)  # Default €400
    air_total = total_kg * costs.get('air_per_kg', 1.50)  # Default €1.50/kg
    rail_total = containers * costs.get('rail_per_container', 3000)  # Default €3000
    
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