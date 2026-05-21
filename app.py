import streamlit as st
import requests
from PyPDF2 import PdfReader
from docx import Document
import pandas as pd
import os
import tempfile
import re
from datetime import datetime
from fpdf import FPDF

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="VivaLens 2.0",
    page_icon="🎓",
    layout="wide"
)

# =====================================================
# STYLING (UNCHANGED)
# =====================================================
st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}
.stButton button {
    width: 100%;
    border-radius: 14px;
    height: 52px;
    font-size: 17px;
    font-weight: 600;
}
.stTextArea textarea {
    border-radius: 14px;
}
[data-testid="stSidebar"] {
    background-color: #111827;
}
.metric-card {
    background: #111827;
    padding: 20px;
    border-radius: 18px;
    text-align: center;
    color: white;
    border: 1px solid #374151;
}
.result-box {
    background: #0f172a;
    padding: 25px;
    border-radius: 18px;
    border: 1px solid #334155;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# API CONFIG
# =====================================================
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY")
CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
TRANSCRIBE_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

if not GROQ_API_KEY:
    st.error("Missing GROQ API Key")
    st.stop()

# =====================================================
# SESSION STATE
# =====================================================
defaults = {
    "mode": "Student Practice",
    "questions": [],
    "answers": [],
    "q_index": 0,
    "final_result": None,
    "voice_answers": {},
    "saved_once": False   # 🔥 prevents duplicate saving
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =====================================================
# FILE READER
# =====================================================
def extract_text(file):
    text = ""
    try:
        if file.type == "application/pdf":
            reader = PdfReader(file)
            for p in reader.pages:
                text += p.extract_text() or ""

        elif file.name.endswith(".docx"):
            doc = Document(file)
            for para in doc.paragraphs:
                text += para.text + "\n"

        else:
            text = file.read().decode("utf-8", errors="ignore")
    except:
        pass
    return text

# =====================================================
# AUDIO TRANSCRIPTION
# =====================================================
def transcribe_audio(audio_bytes):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio_bytes)
            path = f.name

        with open(path, "rb") as af:
            res = requests.post(
                TRANSCRIBE_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                files={"file": af},
                data={"model": "whisper-large-v3"}
            )

        os.remove(path)
        return res.json().get("text", "")

    except:
        return ""

# =====================================================
# QUESTION GENERATION
# =====================================================
def generate_questions(project_text, section, difficulty, examiner_mode, system_mode):

    prompt = f"""
You are a strict university viva examiner.

Generate EXACTLY 6 questions based on SECTION: {section}

PROJECT:
{project_text[:12000]}

FORMAT:
Q1: ...
Q2: ...
Q3: ...
Q4: ...
Q5: ...
Q6: ...
"""

    res = requests.post(
        CHAT_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }
    )

    data = res.json()

    if "choices" not in data:
        return ["Error generating questions"] * 6

    raw = data["choices"][0]["message"]["content"]

    questions = []
    for line in raw.split("\n"):
        if "Q" in line and ":" in line:
            questions.append(line.split(":", 1)[1].strip())

    return questions[:6] if len(questions) >= 6 else ["Fallback question"] * 6

# =====================================================
# EVALUATION
# =====================================================
def evaluate_answer(q, a):
    res = requests.post(
        CHAT_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        json={
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": f"{q}\n{a}"}],
            "temperature": 0.2
        }
    )
    return res.json()["choices"][0]["message"]["content"]

# =====================================================
# FINAL RESULT
# =====================================================
def generate_final_result(qa, name, roll, dept, project_title):

    prompt = f"""
Evaluate viva:

Name: {name}
Roll: {roll}
Dept: {dept}
Project: {project_title}

{qa}

Give score out of 100 and PASS/FAIL.
"""

    res = requests.post(
        CHAT_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        json={
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }
    )

    return res.json()["choices"][0]["message"]["content"]

# =====================================================
# SAVE TO EXCEL (FIXED - ONLY ONE FUNCTION)
# =====================================================
def save_to_excel(name, roll, dept, project_title, result):

    try:
        file_path = "student_results.xlsx"

        marks = re.search(r'(\d+)\s*/\s*100', result)
        marks = marks.group(0) if marks else "N/A"

        status = "PASS" if "PASS" in result.upper() else "FAIL" if "FAIL" in result.upper() else "UNKNOWN"

        new_row = pd.DataFrame([{
            "Student Name": name,
            "Roll Number": roll,
            "Department": dept,
            "Project Title": project_title,
            "Marks": marks,
            "Status": status,
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])

        if os.path.exists(file_path):
            old = pd.read_excel(file_path, engine="openpyxl")
            new_row = pd.concat([old, new_row], ignore_index=True)

        new_row.to_excel(file_path, index=False, engine="openpyxl")

        st.success("✅ Saved to Excel Database")

    except Exception as e:
        st.error(f"Save failed: {e}")

# =====================================================
# UI
# =====================================================
st.title("🎓 VivaLens 2.0")

mode_toggle = st.sidebar.toggle("🏛 University Final Exam Mode")
st.session_state.mode = "University Final Exam" if mode_toggle else "Student Practice"

uploaded_file = st.file_uploader("Upload Project")

if st.session_state.mode == "University Final Exam":
    name = st.text_input("Student Name")
    roll = st.text_input("Roll Number")
    dept = st.text_input("Department")
    project_title = st.text_input("Project Title")

# =====================================================
# GENERATE QUESTIONS
# =====================================================
if st.button("Generate Viva Questions"):
    if uploaded_file:
        text = extract_text(uploaded_file)
        st.session_state.questions = generate_questions(
            text, "Technical", "Medium", "Strict", st.session_state.mode
        )
        st.session_state.q_index = 0
        st.session_state.answers = []
        st.session_state.saved_once = False
        st.success("Questions Generated")

# =====================================================
# FINAL REPORT FLOW
# =====================================================
if st.session_state.mode == "University Final Exam":

    if st.session_state.questions and st.session_state.q_index >= len(st.session_state.questions):

        if st.button("Generate Final Report"):

            qa = ""
            for i, q in enumerate(st.session_state.questions):
                ans = st.session_state.answers[i] if i < len(st.session_state.answers) else ""
                qa += f"Q{i+1}: {q}\nA{i+1}: {ans}\n\n"

            result = generate_final_result(qa, name, roll, dept, project_title)
            st.session_state.final_result = result

            # 🔥 SAVE ONLY ONCE
            if not st.session_state.saved_once:
                save_to_excel(name, roll, dept, project_title, result)
                st.session_state.saved_once = True

# =====================================================
# RESULT DISPLAY
# =====================================================
if st.session_state.final_result:
    st.success("Final Evaluation Ready")
    st.write(st.session_state.final_result)

    if st.button("Next Student"):
        st.session_state.questions = []
        st.session_state.answers = []
        st.session_state.q_index = 0
        st.session_state.final_result = None
        st.session_state.saved_once = False
        st.rerun()
