# config.py

MODEL = "llama-3.3-70b-versatile"  # Groq's best free model

JD_PARSER_PROMPT = """You are an expert HR analyst. Extract the key requirements from this job description.

Return your response in this exact format:

ROLE TITLE: [job title]
REQUIRED SKILLS: [comma separated list of must-have technical skills]
PREFERRED SKILLS: [comma separated list of nice-to-have skills]
EXPERIENCE LEVEL: [Junior / Mid / Senior / Principal]
KEY RESPONSIBILITIES: [3-4 bullet points of main responsibilities]
DOMAIN: [e.g. BFSI, Healthcare, E-commerce, etc.]

Job Description:
{jd_text}"""


MATCH_ANALYSIS_PROMPT = """You are an expert career coach and CV analyst specializing in Data Science roles.

Analyze this CV against the job description requirements and return your response in this EXACT format:

MATCH SCORE: [a number between 0 and 100]

MATCHED SKILLS:
- [skill 1 found in both CV and JD]
- [skill 2 found in both CV and JD]
- [skill 3 found in both CV and JD]

CRITICAL GAPS:
- [important required skill missing from CV]
- [another critical gap]

NICE TO HAVE GAPS:
- [preferred skill missing but not critical]
- [another nice to have gap]

STRENGTHS FOR THIS ROLE:
- [specific strength from CV relevant to this JD]
- [another strength]
- [another strength]

OVERALL ASSESSMENT:
[2-3 sentences summarizing fit for the role]

CV Content:
{cv_text}

Job Requirements:
{jd_parsed}"""


BULLET_REWRITER_PROMPT = """You are an expert CV coach. Rewrite these CV bullet points to better match the job description.

Rules:
- Keep the same facts — do NOT invent experience that doesn't exist
- Use keywords and language from the job description naturally
- Make impact and numbers more prominent where they exist
- Keep each bullet to 1-2 lines maximum
- Start each bullet with a strong action verb

CV Bullets to Rewrite:
{cv_bullets}

Job Description Requirements:
{jd_parsed}

Return ONLY the rewritten bullets, one per line, starting with a dash (-).
Do not add any explanation or preamble."""


INTERVIEW_PREP_PROMPT = """You are an expert interview coach for Data Science roles.

Based on the gap analysis between this candidate's CV and the job description, generate the 5 most likely interview questions the candidate will face — specifically targeting their identified weak areas.

For each question also provide a coaching tip on how to answer it well.

Return in this format:
Q1: [question]
TIP: [1-2 sentence coaching tip]

Q2: [question]
TIP: [1-2 sentence coaching tip]

(and so on for Q3, Q4, Q5)

Candidate Gap Areas:
{gaps}

Job Role: {role_title}
Domain: {domain}"""
