# Dragon Fire Transportation Challenge
## Interactive Supply Chain Learning Tool

### Case Overview
**Company**: Blue Dragon (Austria)  
**Product**: Dragon Fire energy drink powder  
**Target Market**: High-end bars, clubs, restaurants in China  
**Price Point**: 25 Yuan (~3€) per drink  
**Unique Selling Point**: Coca leaf-based energy (not caffeine)  
**Challenge**: Design optimal transportation from Austria to China

---

## Learning Progression Framework

### Phase 1: Product Analysis (Foundation Questions)
Students must understand the product before designing logistics:

**AI-Guided Questions:**
1. "What are the physical characteristics of the powder that affect transportation?"
2. "How does the powder's shelf life impact supply chain timing?"
3. "What regulatory considerations exist for coca leaf-based products?"
4. "How much powder is needed to produce one drink?"

**Interactive Elements:**
- Volume calculator: Students estimate annual demand → powder volume needed
- Packaging optimizer: Choose container types and calculate space efficiency
- Shelf life timer: Understand time constraints in supply chain

### Phase 2: Transportation Mode Analysis
**Modes to Compare:**
1. **Sea Freight** (Rotterdam → Shanghai/Ningbo)
2. **Air Freight** (Vienna → Beijing/Shanghai)
3. **Rail Freight** (Via Belt & Road Initiative)
4. **Multimodal** (Combinations of above)

**AI Prompts for Each Mode:**
- "What are the trade-offs between cost and speed for this mode?"
- "How does this mode affect product quality during transport?"
- "What are the capacity limitations and scheduling constraints?"

### Phase 3: Route Optimization
**Interactive Map Features:**
- Click different routes to see distance, time, cost
- Weather impact simulator (monsoons, winter delays)
- Port congestion indicators
- Geopolitical risk markers

### Phase 4: Supply Chain Design Challenge
Students build their complete supply chain:

**Decision Points:**
1. **Production Planning**: Batch sizes, production frequency
2. **Warehousing**: Location of Chinese mixing/bottling facilities
3. **Distribution**: From ports to end customers
4. **Inventory Management**: Safety stock levels
5. **Risk Management**: Backup plans and alternatives

### Phase 5: Disruption Scenarios
**Real-world challenges students must solve:**

1. **Suez Canal Blockage**
   - AI: "Your sea freight is delayed 2 weeks. How do you maintain supply?"
   - Options: Air freight backup, local sourcing, inventory buffers

2. **COVID-19 Port Closures**
   - AI: "Shanghai port is closed. What are your alternatives?"
   - Students explore other Chinese ports and logistics networks

3. **Quality Issue Discovery**
   - AI: "Powder degradation found in hot containers. How do you prevent this?"
   - Students redesign packaging and routing for temperature control

4. **Regulatory Changes**
   - AI: "China restricts coca leaf imports. How do you pivot?"
   - Students explore product reformulation or market strategy changes

---

## Implementation Structure

### Backend Components Needed:

1. **Transportation Calculator**
```python
def calculate_transport_cost(mode, volume, route, urgency):
    # Dynamic pricing based on real-world factors
    base_costs = {
        'sea': 2000,  # per container
        'air': 8,     # per kg
        'rail': 3000, # per wagon
    }
    # Factor in distance, fuel costs, seasonal variations
    return adjusted_cost

def simulate_delivery_time(mode, route, disruptions=[]):
    # Account for weather, congestion, holidays
    return estimated_days
```

2. **Disruption Simulator**
```python
def generate_disruption_scenario():
    scenarios = [
        "port_congestion", "weather_delay", "customs_hold",
        "capacity_shortage", "fuel_price_spike", "geopolitical_risk"
    ]
    return random.choice(scenarios)
```

3. **AI Question Engine**
```python
def generate_contextual_question(student_choices, current_phase):
    # AI generates questions based on student's previous decisions
    # Guides them to consider factors they might have missed
    return adaptive_question
```

### Frontend Components:

1. **Interactive Supply Chain Builder**
   - Drag-and-drop interface for route building
   - Real-time cost/time calculations
   - Visual representation of chosen supply chain

2. **Scenario Simulator Dashboard**
   - Current supply chain status
   - Disruption alerts
   - Performance metrics (cost, time, reliability)

3. **Decision Tree Visualizer**
   - Shows consequences of different choices
   - "What-if" analysis tools
   - Comparison matrices

### Assessment Framework:

**Grading Criteria:**
1. **Cost Efficiency** (25%): Optimal cost per unit delivered
2. **Risk Management** (25%): How well disruptions are handled
3. **Strategic Thinking** (25%): Understanding of trade-offs
4. **Innovation** (25%): Creative solutions to challenges

**Auto-Scoring Elements:**
- Cost calculations (quantitative)
- Time to market (quantitative)
- Risk mitigation strategies (qualitative AI assessment)

---

## Sample Student Journey

### Initial Questions (AI-Driven):
```
AI: "Welcome to Dragon Fire! You need to get energy drink powder from Austria to China. Let's start: How much do you think one serving of powder weighs?"

Student: "Maybe 10 grams?"

AI: "Good estimate! Now, if you plan to sell 1 million drinks in the first year, how much total powder do you need? And what volume will that occupy?"

Student: [Calculates 10,000 kg]

AI: "Excellent! 10 tons of powder. Now, that powder is worth about €2 million. Would you ship it by sea (cheap, slow) or air (expensive, fast)? What factors should influence this decision?"
```

### Progressive Challenge:
```
AI: "You chose sea freight - smart for cost! But I have bad news: there's a 3-week delay at Shanghai port due to COVID. Your Chinese customers are running out of Dragon Fire. What's your backup plan?"

Student: "Switch to air freight for urgent deliveries?"

AI: "That could work! Let's calculate: air freight costs 4x more. How much of your shipment should go by air vs. waiting for the ship? What's the break-even point where you lose more money from lost sales than extra transport costs?"
```

This creates an engaging, realistic learning experience that builds practical supply chain thinking while maintaining academic rigor.