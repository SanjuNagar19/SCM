
# Assignment: Designing Efficient and Responsive Distribution – The Case of Seven-Eleven Japan

## Course Context
**Course:** Supply Chain Management  
**Session:** 5 — Key Trade-offs in Distribution  
**Case:** Seven-Eleven Japan Co. (2015)  
**Instructor:** Prof. Wallenburg (WHU BSc Fall 2024)  
**Platform:** Streamlit Learning Tool with GPT-powered chatbot context  

---

## Case Overview
Seven-Eleven Japan operates one of the world’s most efficient convenience-store supply chains.  
Its **Combined Delivery System (CDS)** routes all products through distribution centers (DCs) before delivery to stores, **prohibiting direct store delivery (DSD)** by suppliers.  

- 16,000 stores across Japan (2013 data)  
- 158 distribution centers  
- 3 deliveries per day per store  
- 10 stores per truck per run  
- ¥50,000 cost per truck/run  
- Product categories: ~171, across three temperature zones (frozen, chilled, ambient)  
- Fresh/fast food share ≈ 65% of sales  
- Average DC-to-store lead time: ~3 hours  

**Strategic question from the case:**  
> Should Seven-Eleven Japan continue its current CDS or introduce limited DSD in the future? If yes, for which products?  

---

## Learning Objectives
1. Understand trade-offs between *efficiency* and *responsiveness* in retail distribution.  
2. Apply distribution design frameworks (from Session 5) to a real case.  
3. Use quantitative reasoning to evaluate network efficiency.  
4. Interact with an AI chatbot to derive and apply contextual case data.  

---

## Assignment Structure

| Section | Focus | Input Type | Grading |
|----------|--------|------------|----------|
| Part 1 | Conceptual understanding | Short written | Rubric |
| Part 2 | Quantitative case analysis | Numeric + short written | Auto + rubric |
| Part 3 | Chatbot-assisted inquiry | Chat snippet + reasoning | Rubric |
| Part 4 | Strategic application | Written | Rubric |

---

## Part 1 – Conceptual Foundations
**Goal:** Explain how distribution network design affects efficiency and responsiveness.

**Questions:**
1. Why does Seven-Eleven Japan operate so many stores in dense clusters?  
2. Explain how the *Combined Delivery System (CDS)* supports efficiency and responsiveness compared to *Direct Store Delivery (DSD)*.  
3. Identify **two cost factors** and **two service factors** from the Session 5 framework (slide 350) that are directly impacted by this choice.

**Expected focus points:**
- Efficiency: routing consolidation, DC utilization, inventory turnover.  
- Responsiveness: frequent replenishment, product freshness, reduced stockouts.  

*(Answer length ≈ 150–200 words.)*

---

## Part 2 – Quantitative Case Analysis: Evaluating the Combined Delivery System

### Case Data (from 2015 study):

| Parameter | Japan | U.S. (for comparison) |
|------------|--------|------------------------|
| No. of stores | 16,000 | — |
| No. of DCs | 158 | — |
| Stores per truck/run | 10 | 8 |
| Cost per truck/run | ¥50,000 | ¥60,000 |
| Deliveries per store/day | 3 | 1 |
| Avg. DC–store distance | 25 km | 60 km |
| Temperature zones | 3 | 1 |

### Task 2.1 – DC Utilization
Compute average stores served per DC.  
`16,000 / 158 = 101.27`  
✅ Expected range: **100–102 stores per DC**

### Task 2.2 – Daily Delivery Cost per Store
`Cost per store/day (Japan) = (50,000 / 10) × 3 = ¥15,000`  
`Cost per store/day (U.S.) = (60,000 / 8) × 1 = ¥7,500`  
✅ **Expected numeric answer: ¥7,500 difference per store/day**  
*(Auto-validation tolerance ±500)*

### Task 2.3 – Multi-temperature Deliveries
If each temperature zone requires separate runs:  
`3 × (50,000 ÷ 10) × 3 = ¥45,000 per store/day`  
If DSD = 5 suppliers × ¥7,500 = ¥37,500.  
Discuss which setup is more cost-efficient and why.  
*(≈100 words)*

### Task 2.4 – Fresh Food Rationale
Fresh and fast foods = ~65% of sales.  
Explain briefly how this justifies the high delivery frequency and cost.  
*(≈80 words)*

### Optional (Advanced)
If 15% of volume (beverages) moved to DSD (¥70,000/run, 8 stores/run, 1 run/day):  
CDS portion = 85% × ¥15,000 = ¥12,750  
DSD portion = 15% × ¥8,750 = ¥1,312  
Total ≈ **¥14,062 per store/day**

---

## Part 3 – Guided Chatbot Exploration
**Goal:** Use the GPT chatbot (preloaded with case) to explore product-specific implications.

**Instructions to Students:**
Ask the chatbot:
- “Which product categories in Seven-Eleven Japan’s supply chain are most suitable for DSD?”  
- “What problems could arise if suppliers deliver directly to stores?”

**Task:**
1. Copy 1–2 chatbot exchanges (max 5 lines).  
2. Summarize what you learned (≤100 words).  

*(Rubric: relevance, reasoning, and correct use of case context.)*

---

## Part 4 – Strategic Application: Expansion to Germany
**Scenario (from Session 5 slide 313):**
Seven-Eleven Japan considers entering Germany.  
How promising would a market entry using the Japanese concept be, and which regions would be most suitable?

**Task:**
- Recommend whether 7-Eleven should replicate CDS or adopt a hybrid (CDS + DSD).  
- Identify **2–3 promising German regions** and justify (density, autobahn, consumer habits).  
*(≈200 words)*

---

## Deliverables Summary

| Section | Input | Validation | Evaluation |
|----------|--------|-------------|-------------|
| Part 1 | Short written | Completion | Rubric (0–3) |
| Part 2.1–2.2 | Numeric | Auto-check | Auto |
| Part 2.3–2.5 | Short written | Completion | Rubric (0–3) |
| Part 3 | Chat + summary | Completion | Rubric (0–3) |
| Part 4 | Written | Completion | Rubric (0–3) |

---

## Chatbot Integration Notes for Developer

**Context Prompt:**
> “You are an SCM case assistant. Use the *Seven-Eleven Japan (2015)* case and Session 5 slides to answer questions about CDS, DSD, and their trade-offs. Base responses on supply chain efficiency and responsiveness principles.”

**Key facts chatbot should recall:**
- 16,000 stores, 158 DCs  
- 3 deliveries/day, 10 stores/truck  
- ¥50,000 per truck/run, 3 temperature zones  
- 65% fresh food share, 3-hour lead time  

**Validation logic:**
- Numeric ranges (±500 yen; ±2 for ratios).  
- Require at least one chatbot interaction snippet.  

---

## Expected Numeric Outputs (for verification)

| Task | Expected Answer | Range |
|------|------------------|--------|
| 2.1 | 101 | ±2 |
| 2.2 | 7,500 | ±500 |
| 2.3 | 45,000 vs 37,500 | — |
| Optional | 14,000 | ±1,000 |

---

## Example Code for Validation

```python
# Example student validation logic
stores_per_dc = 16000 / 158  # 101.27
japan_cost = (50000 / 10) * 3  # 15000
us_cost = (60000 / 8) * 1  # 7500
difference = japan_cost - us_cost  # 7500
multi_temp_cost = 3 * (50000 / 10) * 3  # 45000
```

---

## Instructor Dashboard Fields

| Field | Description |
|--------|--------------|
| Student ID | Auto-filled |
| Numeric results (auto) | Parts 2.1–2.2 |
| Text answers (Parts 1, 2.3–4) | Editable for rubric grading |
| Chat transcript (Part 3) | Text snippet |
| Rubric scores | Dropdown (0–3) |
| Overall grade | Auto-calculated |
