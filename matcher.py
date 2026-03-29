# matcher.py

from pathlib import Path
from groq import Groq
from config import MODEL, JD_PARSER_PROMPT, MATCH_ANALYSIS_PROMPT, BULLET_REWRITER_PROMPT, INTERVIEW_PREP_PROMPT
import os
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

_client = None


def _get_client():
    global _client
    if _client is None:
        key = (os.getenv("GROQ_API_KEY") or "").strip()
        if not key:
            raise ValueError(
                "GROQ_API_KEY is not set. Add GROQ_API_KEY=... to the .env file in this project "
                "(create https://console.groq.com/keys)."
            )
        _client = Groq(api_key=key)
    return _client


def parse_job_description(jd_text):
    """Extract structured requirements from raw JD text."""
    prompt = JD_PARSER_PROMPT.format(jd_text=jd_text)

    response = _get_client().chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    return response.choices[0].message.content


def analyze_match(cv_text, jd_parsed):
    """Compare CV against parsed JD and return structured analysis."""
    prompt = MATCH_ANALYSIS_PROMPT.format(
        cv_text=cv_text,
        jd_parsed=jd_parsed
    )

    response = _get_client().chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    return response.choices[0].message.content


def rewrite_bullets(cv_bullets, jd_parsed):
    """Rewrite CV bullet points to better match the JD."""
    prompt = BULLET_REWRITER_PROMPT.format(
        cv_bullets=cv_bullets,
        jd_parsed=jd_parsed
    )

    response = _get_client().chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )

    return response.choices[0].message.content


def generate_interview_questions(gaps, role_title, domain):
    """Generate likely interview questions based on identified gaps."""
    prompt = INTERVIEW_PREP_PROMPT.format(
        gaps=gaps,
        role_title=role_title,
        domain=domain
    )

    response = _get_client().chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6
    )

    return response.choices[0].message.content
