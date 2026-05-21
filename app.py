
import streamlit as st
import requests
from PyPDF2 import PdfReader
from docx import Document
import pandas as pd
import os
import tempfile
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
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}"
                },
                files={"file": af},
                data={"model": "whisper-large-v3"}
            )

        try:
            os.remove(path)
        except:
            pass

        return res.json().get("text", "")

    except:
        return ""

# =====================================================
# QUESTION GENERATION
# =====================================================

def generate_questions(project_text, section, difficulty, examiner_mode, system_mode):

    prompt = f"""
You are a strict university viva examiner.

Generate EXACTLY 6 questions.

IMPORTANT RULES:
- MUST strictly follow section: {section}
- MUST match difficulty: {difficulty}
- MUST match examiner style: {examiner_mode}
- DO NOT ignore instructions
- Questions MUST be relevant to selected section only

SECTION RULES:
- Basic → simple conceptual understanding
- Technical → code, architecture, implementation details
- Logical → reasoning, problem solving
- Overall → mixed evaluation
- Presentation → communication & explanation skills
- Defense → critical questioning

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
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }
    )

    data = res.json()

    if "choices" not in data:
        return [
            f"Explain your {section} part of project.",
            "Describe system architecture.",
            "What technologies are used?",
            "Explain workflow.",
            "What challenges did you face?",
            "What improvements can be made?"
        ]

    raw = data["choices"][0]["message"]["content"]

    questions = []
    for line in raw.split("\n"):
        if line.startswith("Q") and ":" in line:
            questions.append(line.split(":", 1)[1].strip())

    if len(questions) < 6:
        return [
            f"Explain your {section} module.",
            "Describe architecture.",
            "Explain implementation.",
            "What challenges did you face?",
            "How does system work?",
            "What improvements can be made?"
        ]

    return questions[:6]
    
# =====================================================
# ANSWER EVALUATION
# =====================================================

def evaluate_answer(q, a):

    prompt = f"""
Question: {q}

Student Answer:
{a}

Give strict evaluation with score.
"""

    try:

        res = requests.post(
            CHAT_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}"
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.2
            }
        )

        return res.json()["choices"][0]["message"]["content"]

    except:
        return "Evaluation failed."

# =====================================================
# FINAL RESULT
# =====================================================

def generate_final_result(qa, name, roll, dept, project_title):

    prompt = f"""
You are a university external examiner.

Evaluate the complete viva professionally.

STUDENT:
Name: {name}
Roll: {roll}
Department: {dept}
Project: {project_title}

VIVA:
{qa}

REQUIRED:
- Overall Score /100
- Technical Skills
- Communication
- Strengths
- Weaknesses
- Final Verdict
"""

    try:

        res = requests.post(
            CHAT_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.2
            }
        )

        data = res.json()

        if "choices" not in data:
            return "Evaluation failed."

        return data["choices"][0]["message"]["content"]

    except:
        return "Evaluation failed."


# =====================================================
# PDF REPORT
# =====================================================

def create_pdf_report(name, roll, dept, project_title, result):

    pdf = FPDF()

    pdf.add_page()

    pdf.set_font("Arial", "B", 18)
    pdf.cell(200, 10, "VivaLens Final Viva Report", ln=True, align="C")

    pdf.ln(10)

    pdf.set_font("Arial", "", 12)

    pdf.cell(200, 10, f"Student Name: {name}", ln=True)
    pdf.cell(200, 10, f"Roll Number: {roll}", ln=True)
    pdf.cell(200, 10, f"Department: {dept}", ln=True)
    pdf.cell(200, 10, f"Project Title: {project_title}", ln=True)

    pdf.ln(10)

    pdf.multi_cell(0, 10, result)

    pdf_file = f"{roll}_viva_report.pdf"

    pdf.output(pdf_file)

    return pdf_file

# =====================================================
# HEADER
# =====================================================

st.title("🎓 VivaLens 2.0")
st.markdown("### AI Viva + Thesis Defense System")

# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.title("⚙️ VivaLens Settings")

mode_toggle = st.sidebar.toggle("🏛 University Final Exam Mode")

st.session_state.mode = (
    "University Final Exam"
    if mode_toggle
    else "Student Practice"
)

section = "Technical"
difficulty = "Medium"
examiner_mode = "Strict 😐"

if st.session_state.mode == "Student Practice":

    section = st.sidebar.radio(
        "Viva Section",
        ["Basic", "Technical", "Logical"]
    )

    difficulty = st.sidebar.selectbox(
        "Difficulty",
        ["Easy", "Medium", "Difficult", "Expert"]
    )

    examiner_mode = st.sidebar.selectbox(
        "Examiner Personality",
        [
            "Friendly 🙂",
            "Strict 😐",
            "Interview 💼",
            "Rapid Fire ⚡",
            "Defense Panel 🔥"
        ]
    )

    answer_mode = st.sidebar.radio(
        "Answer Mode",
        ["Voice", "Text"]
    )

else:

    examiner_mode = st.sidebar.selectbox(
        "Examiner Mode",
        [
            "Formal Board",
            "HOD Panel",
            "External Examiner",
            "AI Strict Judge"
        ]
    )

    section = st.sidebar.radio(
        "Section",
        [
            "Overall",
            "Technical Depth",
            "Presentation",
            "Defense"
        ]
    )

    answer_mode = st.sidebar.radio(
        "Answer Mode",
        ["Voice", "Text"]
    )

# =====================================================
# FILE UPLOAD
# =====================================================

uploaded_file = st.file_uploader(
    "📄 Upload Project",
    type=["pdf", "docx", "txt", "py", "ipynb"]
)

# =====================================================
# STUDENT INFO
# =====================================================

if st.session_state.mode == "University Final Exam":

    name = st.text_input("Student Name")
    roll = st.text_input("Roll Number")
    dept = st.text_input("Department")
    project_title = st.text_input("Project Title")

# =====================================================
# GENERATE QUESTIONS
# =====================================================

if st.button("🚀 Generate Viva Questions"):

    if uploaded_file:

        text = extract_text(uploaded_file)

        with st.spinner("Generating AI Questions..."):

            st.session_state.questions = generate_questions(
                text,
                section,
                difficulty,
                examiner_mode,
                st.session_state.mode
            )

        st.session_state.answers = []
        st.session_state.q_index = 0
        st.session_state.voice_answers = {}
        st.session_state.final_result = None

        st.success("Questions Generated Successfully ✅")

# =====================================================
# QUESTION FLOW
# =====================================================

if st.session_state.questions:

    i = st.session_state.q_index

    progress = int((i / len(st.session_state.questions)) * 100)

    st.progress(progress)

    if i >= len(st.session_state.questions):

        st.success("✅ Viva Completed!")

    else:

        q = st.session_state.questions[i]

        st.markdown("---")

        st.subheader(f"Question {i+1} / 6")

        st.write(q)

        # =========================================
        # VOICE MODE
        # =========================================

        if answer_mode == "Voice":

            audio = st.audio_input(
                "🎤 Speak Your Answer",
                key=f"audio_{i}"
            )

            if audio is not None:

                if st.button(
                    "🧠 Transcribe",
                    key=f"transcribe_{i}"
                ):

                    with st.spinner("Transcribing..."):

                        text = transcribe_audio(
                            audio.getvalue()
                        )

                        st.session_state.voice_answers[i] = text

                    st.success("Transcription Complete ✅")

            answer = st.session_state.voice_answers.get(i, "")

            if answer:

                st.text_area(
                    "Transcribed Answer",
                    value=answer,
                    disabled=True,
                    height=180,
                    key=f"display_{i}"
                )

        # =========================================
        # TEXT MODE
        # =========================================

        else:

            answer = st.text_area(
                "✍️ Your Answer",
                height=180,
                key=f"text_{i}"
            )

        # =========================================
        # BUTTONS
        # =========================================

        col1, col2 = st.columns(2)

        with col1:

            if st.button(
                "✅ Submit",
                key=f"submit_{i}"
            ):

                if answer.strip() == "":

                    st.error("Please answer first")

                else:

                    if st.session_state.mode == "Student Practice":

                        with st.spinner("Evaluating Answer..."):

                            evaluation = evaluate_answer(
                                q,
                                answer
                            )

                        st.success(evaluation)

                    else:

                        st.success("Answer Saved ✅")

        with col2:

            if st.button(
                "➡️ Next",
                key=f"next_{i}"
            ):

                if answer.strip() == "":

                    st.error("Please answer first")

                else:

                    if len(st.session_state.answers) <= i:

                        st.session_state.answers.append(answer)

                    else:

                        st.session_state.answers[i] = answer

                    st.session_state.q_index += 1

                    st.rerun()

# =====================================================
# FINAL EVALUATION
# =====================================================

if (
    st.session_state.mode == "University Final Exam"
    and st.session_state.questions
    and st.session_state.q_index >= len(st.session_state.questions)
):

    st.markdown("---")

    st.subheader("🏁 Final Viva Evaluation")

    if st.button("Generate Final Report"):

        qa = ""

        for i, q in enumerate(st.session_state.questions):

            ans = (
                st.session_state.answers[i]
                if i < len(st.session_state.answers)
                else ""
            )

            qa += f"""
QUESTION {i+1}: {q}

ANSWER {i+1}: {ans}

"""

        with st.spinner("Generating Final Evaluation..."):

            result = generate_final_result(
                qa,
                name,
                roll,
                dept,
                project_title
            )

        st.session_state.final_result = result

import re
from datetime import datetime

def save_to_excel(name, roll, dept, project_title, result):

    file = "student_results.xlsx"

    # =========================
    # Extract Marks
    # =========================

    marks_match = re.search(r'Overall Marks:\s*(\d+\/100)', result)

    if marks_match:
        marks = marks_match.group(1)
    else:
        marks = "N/A"

    # =========================
    # Extract PASS/FAIL
    # =========================

    if "PASS" in result.upper():
        final_status = "PASS"

    elif "FAIL" in result.upper():
        final_status = "FAIL"

    else:
        final_status = "UNKNOWN"

    # =========================
    # Create Row
    # =========================

    df_new = pd.DataFrame([{
        "Student Name": name,
        "Roll Number": roll,
        "Department": dept,
        "Project Title": project_title,
        "Marks": marks,
        "Status": final_status,
        "Full Evaluation": result,
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }])

    # =========================
    # Append Old Data
    # =========================

    if os.path.exists(file):

        old = pd.read_excel(file, engine="openpyxl")

        df_new = pd.concat([old, df_new], ignore_index=True)

# ======================
# save to excel
# ======================

def save_to_excel(name, roll, dept, project_title, result):

    try:
        file_path = os.path.join(os.getcwd(), "student_results.xlsx")

        import re

        marks_match = re.search(r'Overall Marks:\s*(\d+\/100)', result)
        marks = marks_match.group(1) if marks_match else "N/A"

        status = "PASS" if "PASS" in result.upper() else "FAIL" if "FAIL" in result.upper() else "UNKNOWN"

        new_data = pd.DataFrame([{
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
            new_data = pd.concat([old, new_data], ignore_index=True)

        new_data.to_excel(file_path, index=False, engine="openpyxl")

        st.success("✅ Saved to database")

    except Exception as e:
        st.error(f"Save failed: {e}")
# =====================================================
# PROFESSIONAL RESULT UI
# =====================================================

if st.session_state.final_result:

    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="metric-card">
        <h3>📋 Status</h3>
        <h2>Completed</h2>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="metric-card">
        <h3>🎓 Evaluation</h3>
        <h2>Generated</h2>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="metric-card">
        <h3>💾 Saved</h3>
        <h2>Excel Database</h2>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="result-box">
        <h2>📑 Final Viva Evaluation</h2>
        <br>
        <p>{st.session_state.final_result}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # PDF DOWNLOAD

    pdf_path = create_pdf_report(
        name,
        roll,
        dept,
        project_title,
        st.session_state.final_result
    )

    with open(pdf_path, "rb") as pdf_file:

        st.download_button(
            label="📄 Download PDF Report",
            data=pdf_file,
            file_name=pdf_path,
            mime="application/pdf"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("🔄 Next Student"):

        st.session_state.questions = []
        st.session_state.answers = []
        st.session_state.q_index = 0
        st.session_state.final_result = None
        st.session_state.voice_answers = {}

        st.rerun()


# =====================================================
# VIEW SAVED RESULTS
# =====================================================

if st.session_state.mode == "University Final Exam":

    st.markdown("---")
    st.subheader("📊 Saved Student Results")

    if os.path.exists("student_results.xlsx"):

        df = pd.read_excel("student_results.xlsx")

        st.dataframe(df, use_container_width=True)

        st.success(f"{len(df)} student records found")

    else:

        st.info("No saved records yet.")


# =====================================================
# VIEW DB
# =====================================================

if st.session_state.mode == "University Final Exam":

    if os.path.exists("student_results.xlsx"):
        df = pd.read_excel("student_results.xlsx")
        st.dataframe(df)
