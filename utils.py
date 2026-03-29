# utils.py

import io


def extract_text_from_pdf(uploaded_file):
    """Extract text from an uploaded PDF file."""
    try:
        import pdfplumber
    except ImportError:
        return None, "Missing dependency: run `pip install pdfplumber`"

    text = ""
    try:
        with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        return None, str(e)

    if not text.strip():
        return None, "Could not extract text from PDF. Make sure it is not a scanned image."

    return text.strip(), None


def extract_text_from_txt(uploaded_file):
    """Extract text from an uploaded text file."""
    try:
        text = uploaded_file.read().decode("utf-8")
        return text.strip(), None
    except Exception as e:
        return None, str(e)


def parse_match_score(analysis_text):
    """Extract the numeric match score from the analysis text."""
    try:
        for line in analysis_text.split("\n"):
            if "MATCH SCORE:" in line:
                score = line.replace("MATCH SCORE:", "").strip()
                return int("".join(filter(str.isdigit, score)))
    except Exception:
        pass
    return 0


def get_score_color(score):
    """Return a color based on the match score."""
    if score >= 75:
        return "green"
    elif score >= 50:
        return "orange"
    else:
        return "red"


def get_score_label(score):
    """Return a label based on the match score."""
    if score >= 75:
        return "Strong Match ✅"
    elif score >= 50:
        return "Moderate Match ⚠️"
    else:
        return "Weak Match ❌"
