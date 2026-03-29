# app.py

from pathlib import Path
from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent / ".env"
# override=True: a system/user env var set to empty would otherwise block .env (python-dotenv default)
load_dotenv(_env_path, override=True)

import os
import streamlit as st
from matcher import parse_job_description, analyze_match, rewrite_bullets, generate_interview_questions
from utils import extract_text_from_pdf, extract_text_from_txt, parse_match_score, get_score_color, get_score_label

# ── Page Setup ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CV/JD Matcher",
    page_icon="📄",
    layout="wide"
)

st.title("📄 CV / JD Matcher")
st.caption("Powered by Groq (Llama 3.3 70B) | Instant gap analysis & CV optimization")

def _env_file_has_groq_line_but_no_value():
    try:
        raw = _env_path.read_text(encoding="utf-8")
    except OSError:
        return False
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("GROQ_API_KEY="):
            return not line[len("GROQ_API_KEY=") :].strip()
    return False

if not (os.getenv("GROQ_API_KEY") or "").strip():
    if _env_file_has_groq_line_but_no_value():
        st.error(
            "**`GROQ_API_KEY` is empty on disk.** Your editor may show the key but the file is not saved yet — "
            "press **Ctrl+S** on `.env`, then restart Streamlit. "
            "The line must look like `GROQ_API_KEY=gsk_...` with no spaces around `=`."
        )
    else:
        st.error(
            "**Missing `GROQ_API_KEY`.** Add it to `.env` in this folder as `GROQ_API_KEY=...` "
            "([get a key from Groq](https://console.groq.com/keys)), save the file, then restart Streamlit."
        )

# ── Session State ─────────────────────────────────────────────────────────────
if "cv_text" not in st.session_state:
    st.session_state.cv_text = None
if "jd_parsed" not in st.session_state:
    st.session_state.jd_parsed = None
if "analysis" not in st.session_state:
    st.session_state.analysis = None
if "match_score" not in st.session_state:
    st.session_state.match_score = 0
if "rewritten_bullets" not in st.session_state:
    st.session_state.rewritten_bullets = None
if "interview_questions" not in st.session_state:
    st.session_state.interview_questions = None

# ── Layout: Two Columns for Inputs ────────────────────────────────────────────
st.markdown("### Step 1: Upload Your Inputs")
col1, col2 = st.columns(2)

with col1:
    st.markdown("**Your CV**")
    cv_file = st.file_uploader(
        "Upload CV (PDF or TXT)",
        type=["pdf", "txt"],
        key="cv_uploader"
    )

    if cv_file:
        if cv_file.type == "application/pdf":
            cv_text, error = extract_text_from_pdf(cv_file)
        else:
            cv_text, error = extract_text_from_txt(cv_file)

        if error:
            st.error(f"Error reading CV: {error}")
        else:
            st.session_state.cv_text = cv_text
            st.success(f"✅ CV loaded — {len(cv_text.split())} words extracted")
            with st.expander("Preview extracted CV text"):
                st.text(cv_text[:1000] + "..." if len(cv_text) > 1000 else cv_text)

with col2:
    st.markdown("**Job Description**")
    jd_input_method = st.radio(
        "Input method",
        ["Paste text", "Upload file"],
        horizontal=True
    )

    if jd_input_method == "Paste text":
        jd_text = st.text_area(
            "Paste the job description here",
            height=200,
            placeholder="Copy and paste the full job description..."
        )
    else:
        jd_file = st.file_uploader(
            "Upload JD (PDF or TXT)",
            type=["pdf", "txt"],
            key="jd_uploader"
        )
        jd_text = ""
        if jd_file:
            if jd_file.type == "application/pdf":
                jd_text, error = extract_text_from_pdf(jd_file)
            else:
                jd_text, error = extract_text_from_txt(jd_file)
            if error:
                st.error(f"Error reading JD: {error}")
            else:
                st.success(f"✅ JD loaded — {len(jd_text.split())} words extracted")

# ── Analyze Button ─────────────────────────────────────────────────────────────
st.divider()
st.markdown("### Step 2: Run the Analysis")

can_analyze = st.session_state.cv_text and jd_text and len(jd_text.strip()) > 50

if st.button("🔍 Analyze Match", type="primary", disabled=not can_analyze):
    try:
        with st.spinner("Step 1/2: Parsing job description..."):
            st.session_state.jd_parsed = parse_job_description(jd_text)

        with st.spinner("Step 2/2: Analyzing CV against JD..."):
            st.session_state.analysis = analyze_match(
                st.session_state.cv_text,
                st.session_state.jd_parsed
            )
            st.session_state.match_score = parse_match_score(st.session_state.analysis)

        st.session_state.rewritten_bullets = None
        st.session_state.interview_questions = None
        st.rerun()
    except ValueError as e:
        st.error(str(e))

# ── Results ────────────────────────────────────────────────────────────────────
if st.session_state.analysis:
    st.divider()
    st.markdown("### Step 3: Your Results")

    # Score display
    score = st.session_state.match_score
    color = get_score_color(score)
    label = get_score_label(score)

    col_score, col_label = st.columns([1, 3])
    with col_score:
        st.markdown(f"""
        <div style='text-align:center; padding:20px; border-radius:10px; background-color:#f0f2f6;'>
            <h1 style='color:{color}; margin:0;'>{score}</h1>
            <p style='margin:0; font-size:12px;'>out of 100</p>
        </div>
        """, unsafe_allow_html=True)
    with col_label:
        st.markdown(f"## {label}")
        st.markdown("Scroll down to see full breakdown, CV rewrites, and interview prep.")

    st.divider()

    # Two column layout for results
    res_col1, res_col2 = st.columns(2)

    with res_col1:
        st.markdown("#### 📋 Parsed Job Requirements")
        st.text(st.session_state.jd_parsed)

    with res_col2:
        st.markdown("#### 🔍 Match Analysis")
        st.text(st.session_state.analysis)

    st.divider()

    # ── Bullet Rewriter ────────────────────────────────────────────────────────
    st.markdown("### Step 4: Rewrite CV Bullets for This Role")
    st.caption("Paste 3-5 of your existing CV bullet points and get them rewritten to match this JD.")

    cv_bullets_input = st.text_area(
        "Paste your CV bullet points here",
        height=150,
        placeholder="- Led development of entity resolution framework improving match precision to >99%\n- Built RAG pipeline using GPT-4o for linkage validation\n- Managed team of 8 data scientists..."
    )

    if st.button("✏️ Rewrite Bullets", disabled=not cv_bullets_input.strip()):
        try:
            with st.spinner("Rewriting your bullets to match the JD..."):
                st.session_state.rewritten_bullets = rewrite_bullets(
                    cv_bullets_input,
                    st.session_state.jd_parsed
                )
            st.rerun()
        except ValueError as e:
            st.error(str(e))

    if st.session_state.rewritten_bullets:
        st.markdown("#### ✅ Rewritten Bullets")
        st.success(st.session_state.rewritten_bullets)
        st.caption("These keep your original facts — only the framing and keywords are optimized.")

    st.divider()

    # ── Interview Prep ─────────────────────────────────────────────────────────
    st.markdown("### Step 5: Interview Prep Questions")
    st.caption("Get the 5 questions most likely to be asked based on your gap areas.")

    if st.button("🎯 Generate Interview Questions"):
        # Extract gap section from analysis
        gaps_text = ""
        lines = st.session_state.analysis.split("\n")
        in_gaps = False
        for line in lines:
            if "CRITICAL GAPS" in line or "NICE TO HAVE GAPS" in line:
                in_gaps = True
            elif "STRENGTHS" in line or "OVERALL" in line:
                in_gaps = False
            elif in_gaps and line.strip():
                gaps_text += line + "\n"

        # Extract role title and domain from parsed JD
        role_title = "Data Science"
        domain = "BFSI"
        for line in st.session_state.jd_parsed.split("\n"):
            if "ROLE TITLE:" in line:
                role_title = line.replace("ROLE TITLE:", "").strip()
            if "DOMAIN:" in line:
                domain = line.replace("DOMAIN:", "").strip()

        try:
            with st.spinner("Generating targeted interview questions..."):
                st.session_state.interview_questions = generate_interview_questions(
                    gaps_text, role_title, domain
                )
            st.rerun()
        except ValueError as e:
            st.error(str(e))

    if st.session_state.interview_questions:
        st.markdown("#### 🎯 Likely Interview Questions Based on Your Gaps")
        st.markdown(st.session_state.interview_questions)
