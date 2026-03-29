# 🧠 CV / JD Matcher — Full Technical Explanation

> This document explains the architecture, code design, and key concepts behind the CV/JD Matcher app.
> Use this to confidently explain the project in interviews or to onboard collaborators.

---

## The Big Picture

You built a **multi-stage AI pipeline** that takes two unstructured text inputs — a CV and a Job Description — and produces four structured, actionable outputs:

1. **Parsed JD** — structured extraction of role requirements
2. **Match Analysis** — scored gap analysis between CV and JD
3. **Rewritten Bullets** — CV bullet points optimized for the specific role
4. **Interview Questions** — targeted prep based on identified gaps

The key architectural insight is that **complex tasks are broken into sequential, focused API calls** rather than one giant prompt. Each stage has a single responsibility and feeds its output into the next stage. This is called a **prompt chaining pipeline** — one of the most important patterns in production GenAI systems.

```
CV (PDF/TXT)          Job Description (text/PDF)
      │                        │
      ▼                        ▼
 Text Extraction          Stage 1: JD Parser
 (pdfplumber)             → Structured requirements
      │                        │
      └──────────┬─────────────┘
                 ▼
          Stage 2: Match Analyzer
          → Score + Gap Analysis
                 │
        ┌────────┴────────┐
        ▼                 ▼
  Stage 3:           Stage 4:
  Bullet Rewriter    Interview Prep
  → Optimized        → Targeted
    CV bullets         questions
```

---

## The 4 Files and What Each Does

### 1. `config.py` — The Pipeline's Instructions

Contains all four prompts that define the pipeline's behavior. No logic — just carefully engineered text instructions.

#### JD_PARSER_PROMPT
Converts a raw, unstructured job description into a clean structured format:
- ROLE TITLE, REQUIRED SKILLS, PREFERRED SKILLS, EXPERIENCE LEVEL, KEY RESPONSIBILITIES, DOMAIN

**Why parse the JD first?**
Raw JD text is messy — it mixes role marketing copy, company culture blurb, and actual requirements. By parsing it first into a clean structure, every downstream stage works with clean, focused input rather than noisy raw text. This dramatically improves the quality of all subsequent outputs.

**Temperature = 0.3** — set deliberately low for this stage. Parsing is a factual extraction task — you want consistency and accuracy, not creativity.

#### MATCH_ANALYSIS_PROMPT
The core analytical engine. Receives the CV text and the parsed JD, returns:
- MATCH SCORE (0-100)
- MATCHED SKILLS
- CRITICAL GAPS
- NICE TO HAVE GAPS
- STRENGTHS FOR THIS ROLE
- OVERALL ASSESSMENT

**Key design decision:** The prompt says *"return in this EXACT format"* — this is **output format enforcement** via prompt. By demanding a predictable structure, the app can reliably parse specific sections (like extracting just the gaps for the interview prep stage).

**Temperature = 0.3** — again low, because scoring and gap analysis should be consistent and fact-based.

#### BULLET_REWRITER_PROMPT
Takes existing CV bullets and rewrites them using JD language and keywords — while explicitly instructing the model **not to invent experience**.

This constraint is critical:
- Without it, the model might hallucinate impressive-sounding bullets
- With it, you get authentic optimization — same facts, better framing
- The instruction *"Keep the same facts"* is an example of **guardrail prompting**

**Temperature = 0.5** — slightly higher because rewriting requires some creativity in phrasing.

#### INTERVIEW_PREP_PROMPT
Takes the gap areas identified in Stage 2 and generates the 5 most likely interview questions targeting those weaknesses, with coaching tips.

**Why use the gaps as input rather than the full analysis?**
Focused input = focused output. By extracting just the gap section and passing only that, the model generates questions specifically targeting weak areas — not generic DS interview questions.

**Temperature = 0.6** — higher because interview questions benefit from some variety and creativity.

---

### 2. `utils.py` — The Helper Layer

Four utility functions that handle tasks the main logic shouldn't worry about.

#### `extract_text_from_pdf()`
Uses `pdfplumber` to read PDF files uploaded via Streamlit.

```python
with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
    for page in pdf.pages:
        page_text = page.extract_text()
```

**Why `io.BytesIO`?**
Streamlit's file uploader returns a file-like object in memory, not a path on disk. `io.BytesIO` wraps it so pdfplumber can read it as if it were a real file — without saving anything to disk. This is the standard pattern for handling uploaded files in web apps.

**Error handling** — the function returns a tuple `(text, error)` rather than raising exceptions. This lets the UI gracefully display error messages to the user instead of crashing.

#### `parse_match_score()`
Extracts the numeric score from the analysis text:

```python
for line in analysis_text.split("\n"):
    if "MATCH SCORE:" in line:
        score = line.replace("MATCH SCORE:", "").strip()
        return int(''.join(filter(str.isdigit, score)))
```

**Why parse it manually?**
The LLM returns the score as text like "MATCH SCORE: 80" or "MATCH SCORE: 80/100". Using `filter(str.isdigit, score)` extracts just the digits regardless of format — a robust parsing approach that handles variation in model output.

#### `get_score_color()` and `get_score_label()`
Simple threshold functions that convert a numeric score into a color and label:
- 75+ → green, "Strong Match ✅"
- 50-74 → orange, "Moderate Match ⚠️"
- Below 50 → red, "Weak Match ❌"

This is **presentation logic** kept intentionally separate from business logic — a clean separation of concerns.

---

### 3. `matcher.py` — The API Layer

Four functions, each making one Groq API call corresponding to one pipeline stage.

#### Key difference from Project 6
In Project 6 (Interview Coach), conversation history was passed on every call to maintain context.
Here, **each function is completely stateless** — it only receives what it needs for that specific task.

This is intentional:
- Stage 1 (JD Parser) only needs the JD text
- Stage 2 (Match Analyzer) only needs CV + parsed JD
- Stage 3 (Bullet Rewriter) only needs the bullets + parsed JD
- Stage 4 (Interview Prep) only needs the gaps + role info

**No stage needs to know what happened in a different stage** — each does one job independently.
This makes the pipeline modular — you can swap out any stage without touching the others.

#### Why Groq instead of OpenAI?
```python
from groq import Groq
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
```

Groq runs Llama 3.3 70B on custom hardware (LPUs — Language Processing Units) that delivers
700+ tokens/second — roughly 10x faster than OpenAI for the same model quality class.
For a pipeline with 4 sequential API calls, speed compounds — the whole analysis feels instant.

**API compatibility:** Groq uses the exact same interface as OpenAI:
```python
response = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": prompt}],
    temperature=0.3
)
return response.choices[0].message.content
```
This means switching between providers requires changing just 2 lines — the import and the client initialization. Everything else stays identical. This is called **provider-agnostic design**.

---

### 4. `app.py` — The UI and Flow Orchestrator

#### The 5-Step User Journey
The app guides users through a linear 5-step flow:

```
Step 1: Upload CV + JD
Step 2: Run Match Analysis  ← triggers Stage 1 + Stage 2
Step 3: View Results (score, gaps, strengths)
Step 4: Rewrite Bullets     ← triggers Stage 3 (optional)
Step 5: Interview Prep      ← triggers Stage 4 (optional)
```

Steps 4 and 5 are **on-demand** — triggered by separate buttons. This is a deliberate UX choice:
- Not every user wants bullet rewrites or interview questions
- On-demand saves API calls (and cost) for users who only need the score
- It also keeps the initial result display fast and uncluttered

#### Session State Strategy
```python
st.session_state.cv_text         # Extracted CV text
st.session_state.jd_parsed       # Stage 1 output
st.session_state.analysis        # Stage 2 output
st.session_state.match_score     # Parsed numeric score
st.session_state.rewritten_bullets  # Stage 3 output
st.session_state.interview_questions # Stage 4 output
```

Each pipeline stage output is stored separately in session state.
This means:
- Clicking "Rewrite Bullets" doesn't re-run the match analysis
- Clicking "Generate Interview Questions" doesn't re-run anything else
- Re-uploading a new CV resets all downstream results (prevents stale data)

#### The Reset Logic
```python
# Reset downstream results when re-analyzing
st.session_state.rewritten_bullets = None
st.session_state.interview_questions = None
```

When the user clicks "Analyze Match" again (e.g. with a new JD), downstream results are
cleared so they don't show stale output from the previous analysis. This is **state invalidation** —
a pattern used in every caching and state management system.

#### Gap Extraction for Interview Prep
```python
lines = st.session_state.analysis.split("\n")
in_gaps = False
for line in lines:
    if "CRITICAL GAPS" in line or "NICE TO HAVE GAPS" in line:
        in_gaps = True
    elif "STRENGTHS" in line or "OVERALL" in line:
        in_gaps = False
    elif in_gaps and line.strip():
        gaps_text += line + "\n"
```

This is a simple **section parser** — it reads the analysis output line by line and extracts
only the gap section by detecting header keywords. This is why the output format in the prompt
matters so much — predictable formatting enables reliable downstream parsing.

---

## Key Technical Concepts for Interviews

### 1. Prompt Chaining Pipeline
Breaking a complex task into sequential, focused API calls where each stage's output
feeds the next stage's input.

**Why not one giant prompt?**
- Focused prompts produce better outputs than overloaded ones
- Easier to debug — if Stage 3 output is bad, you fix Stage 3's prompt only
- Modular — swap any stage independently
- Cost-efficient — early stages use cheaper models if needed

---

### 2. Provider-Agnostic Design
The code is written so switching LLM providers requires changing 2 lines.
This is production best practice — LLM providers change pricing and quality frequently.

```python
# Switch from Groq to OpenAI: change just these 2 lines
from openai import OpenAI          # was: from groq import Groq
client = OpenAI()                  # was: client = Groq(api_key=...)
# Everything else stays identical
```

---

### 3. Temperature as a Design Parameter
Different tasks need different levels of creativity vs consistency:

| Stage | Task Type | Temperature | Reasoning |
|---|---|---|---|
| JD Parser | Extraction | 0.3 | Facts only, no creativity |
| Match Analyzer | Analysis | 0.3 | Consistent scoring |
| Bullet Rewriter | Creative rewrite | 0.5 | Some variation needed |
| Interview Prep | Generation | 0.6 | Diverse, creative questions |

Setting temperature deliberately (not just leaving it at default) shows maturity in LLM usage.

---

### 4. Guardrail Prompting
Instructing the model on what NOT to do to prevent harmful outputs:
*"Keep the same facts — do NOT invent experience that doesn't exist"*

In production systems, guardrails prevent:
- Hallucination of credentials or experience
- Bias in scoring (explicit instruction to be fair)
- Format violations (explicit output structure)

---

### 5. Stateless Pipeline vs Stateful Conversation
This project uses a **stateless pipeline** — each API call is independent.
Project 6 (Interview Coach) used a **stateful conversation** — history passed every call.

Knowing when to use each pattern is a key GenAI architecture skill:
- Use stateful when context accumulates and affects future outputs (conversations, agents)
- Use stateless when each task is independent (pipelines, batch processing, evaluation)

---

### 6. In-Memory File Handling
```python
pdfplumber.open(io.BytesIO(uploaded_file.read()))
```

Web apps should avoid writing uploaded files to disk — it creates security risks,
cleanup complexity, and doesn't work on serverless platforms. `io.BytesIO` keeps
everything in memory. This is the production-standard approach.

---

## How to Frame It in an Interview

**30-second elevator pitch:**

> "I built a multi-stage prompt chaining pipeline that analyzes a CV against a job description
> across four sequential stages — JD parsing, match scoring, bullet optimization, and interview
> prep generation. Each stage is a focused, stateless API call to Groq's Llama 3.3 70B model,
> with temperature tuned per task type. The architecture is provider-agnostic, so switching
> from Groq to OpenAI or Gemini requires changing two lines of code."

**Follow-up questions you should be ready for:**

| Question | Key Point to Make |
|---|---|
| Why 4 separate API calls instead of one? | Focused prompts outperform overloaded ones; modular design; easier debugging |
| How do you handle PDF parsing? | pdfplumber with io.BytesIO for in-memory handling — no disk writes |
| Why Groq over OpenAI? | 10x faster inference, free tier, identical API interface |
| How would you make scoring more reliable? | JSON mode / Pydantic for structured output, calibration on labeled CV-JD pairs |
| How would you scale this to batch processing? | Async API calls, queue-based architecture, result caching by JD hash |
| What's the biggest limitation? | LLM scoring isn't calibrated — same CV + JD may get slightly different scores on different runs. Fix: use deterministic scoring (temperature=0) or ensemble multiple runs |

---

## Possible Extensions (Good to Mention Proactively)

- **Batch mode** — upload multiple JDs and rank them by match score automatically
- **Score calibration** — run the same CV-JD pair 3 times and average the scores for stability
- **Keyword highlighting** — highlight matched and missing keywords directly in the CV text
- **ATS simulation** — simulate Applicant Tracking System keyword scanning
- **LinkedIn JD scraper** — paste a LinkedIn job URL and auto-fetch the JD
- **Cover letter generator** — add a Stage 5 that writes a tailored cover letter

---

*Built by Sajal Jain*
*Stack: Python · Groq (Llama 3.3 70B) · Streamlit · pdfplumber · 4-Stage Prompt Pipeline*