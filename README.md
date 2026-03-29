# 📄 CV / JD Matcher

An AI-powered tool that analyzes your CV against any job description and gives you:
- A match score (0-100)
- Skill gap analysis (critical vs nice-to-have)
- CV bullet rewrites optimized for the role
- Targeted interview questions based on your gaps

## Tech Stack
- **LLM:** Groq (Llama 3.3 70B) — free, ultra-fast inference
- **UI:** Streamlit
- **PDF parsing:** pdfplumber
- **Language:** Python

## How to Run
1. Clone the repo
2. Install dependencies
   pip install groq streamlit pdfplumber python-dotenv
3. Add your Groq API key to a .env file
   GROQ_API_KEY=gsk_your-key-here
4. Run the app
   streamlit run app.py

## Author
Sajal Jain