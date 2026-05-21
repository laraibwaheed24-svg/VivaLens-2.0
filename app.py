import streamlit as st
import requests
from PyPDF2 import PdfReader
from docx import Document
import pandas as pd
import os
import tempfile
from datetime import datetime
from fpdf import FPDF
import re

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="VivaLens 2.0",
    page_icon="🎓",
    layout="wide"
)

# =====================================================
# STYLING
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
    "voice_answers": {}
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

Generate EXACTLY 6 questions based on:
Section: {section}
Difficulty: {difficulty}
Examiner: {examiner_mode}

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
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        json={
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }
    )

    data = res.json()

    if "choices" not in data:
        return ["Fallback question"] * 6

    raw = data["choices"][0]["message"]["content"]

    questions = []
    for line in raw.split("\n"):
        if line.startswith("Q") and ":" in line:
            questions.append(line.split(":", 1)[1].strip())

    return questions[:6] if len(questions) >= 6 else ["Fallback"] * 6

# =====================================================
# FINAL RESULT
# =====================================================

def generate_final_result(qa, name, roll, dept, project_title):

    prompt = f"""
You are a strict university examiner.

Evaluate:

Name: {name}
Roll: {roll}
Dept: {dept}
Project: {project_title}

VIVA:
{qa}

Give:
- Score out of 100 (VERY IMPORTANT include this line exactly like: Overall Marks: 85/100)
- PASS or FAIL
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

    data = res.json()
    return data["choices"][0]["message"]["content"]

# =====================================================
# ✅ FIXED DATABASE SAVE (MAIN FIX)
# =====================================================

def save_to_excel(name, roll, dept, project_title, result):

    file_path = "student_results.xlsx"

    marks_match = re.search(r'Overall Marks:\s*(\d+\/100)', result)
    marks = marks_match.group(1) if marks_match else "N/A"

    status = "PASS" if "PASS" in result.upper() else "FAIL"

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

# =====================================================
# PDF REPORT
# =====================================================

def create_pdf_report(name, roll, dept, project_title, result):

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "VivaLens Report", ln=True, align="C")

    pdf.ln(10)
    pdf.set_font("Arial", "", 12)

    pdf.cell(200, 10, f"Name: {name}", ln=True)
    pdf.cell(200, 10, f"Roll: {roll}", ln=True)
    pdf.cell(200, 10, f"Dept: {dept}", ln=True)
    pdf.cell(200, 10, f"Project: {project_title}", ln=True)

    pdf.ln(10)
    pdf.multi_cell(0, 10, result)

    path = f"{roll}_report.pdf"
    pdf.output(path)
    return path

# =====================================================
# HEADER
# =====================================================

st.title("🎓 VivaLens 2.0")

# =====================================================
# SIDEBAR
# =====================================================

mode_toggle = st.sidebar.toggle("Final Exam Mode")

st.session_state.mode = "University Final Exam" if mode_toggle else "Student Practice"

section = st.sidebar.radio("Section", ["Basic","Technical","Logical"]) if st.session_state.mode == "Student Practice" else st.sidebar.radio("Section", ["Overall","Technical Depth","Presentation","Defense"])

difficulty = "Medium"
examiner_mode = "Strict"

# =====================================================
# FILE UPLOAD
# =====================================================

uploaded_file = st.file_uploader("Upload Project", type=["pdf","docx","txt"])

if st.session_state.mode == "University Final Exam":
    name = st.text_input("Name")
    roll = st.text_input("Roll")
    dept = st.text_input("Dept")
    project_title = st.text_input("Project")

# =====================================================
# GENERATE
# =====================================================

if st.button("Generate Viva Questions") and uploaded_file:

    text = extract_text(uploaded_file)

    st.session_state.questions = generate_questions(
        text, section, difficulty, examiner_mode, st.session_state.mode
    )

    st.session_state.answers = []
    st.session_state.q_index = 0
    st.session_state.final_result = None

    st.success("Generated")

# =====================================================
# FLOW
# =====================================================

if st.session_state.questions:

    i = st.session_state.q_index

    if i < len(st.session_state.questions):

        q = st.session_state.questions[i]
        st.subheader(q)

        answer = st.text_area("Answer", key=f"a{i}")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Submit", key=f"s{i}"):

                if st.session_state.mode == "Student Practice":
                    st.success(evaluate_answer(q, answer))
                else:
                    st.success("Saved")

        with col2:
            if st.button("Next", key=f"n{i}"):

                st.session_state.answers.append(answer)
                st.session_state.q_index += 1
                st.rerun()

# =====================================================
# FINAL REPORT + SAVE FIX
# =====================================================

if st.session_state.mode == "University Final Exam":

    if st.session_state.questions and st.session_state.q_index >= len(st.session_state.questions):

        st.subheader("Final Result")

        if st.button("Generate Final Report"):

            qa = ""
            for i, q in enumerate(st.session_state.questions):
                ans = st.session_state.answers[i] if i < len(st.session_state.answers) else ""
                qa += f"{q}\n{ans}\n\n"

            result = generate_final_result(qa, name, roll, dept, project_title)

            st.session_state.final_result = result

            # 🔥 THIS IS THE FIX (NOW IT ACTUALLY SAVES)
            save_to_excel(name, roll, dept, project_title, result)

            st.success("Saved to database ✅")

            pdf = create_pdf_report(name, roll, dept, project_title, result)

            with open(pdf, "rb") as f:
                st.download_button("Download PDF", f, file_name=pdf)

# =====================================================
# VIEW DB
# =====================================================

if st.session_state.mode == "University Final Exam":

    if os.path.exists("student_results.xlsx"):
        df = pd.read_excel("student_results.xlsx")
        st.dataframe(df)
