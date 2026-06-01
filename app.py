import streamlit.components.v1 as components
import streamlit as st
import requests
from PyPDF2 import PdfReader
from docx import Document
import pandas as pd
import os
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

h1, h2, h3 {
    color: #f9fafb;
}

.metric-card:hover {
    transform: translateY(-3px);
    transition: 0.3s;
    box-shadow: 0 10px 20px rgba(0,0,0,0.3);
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
    "warnings": 0,
    "project_text": "",
      # Examiner Login System
    "examiner_logged_in": False,
    "examiner_name": "",
    "examiner_email": ""
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v



# =====================================================
# ANTI CHEATING SYSTEM
# =====================================================

if st.session_state.mode == "University Final Exam":


    components.html(
        """
        <script>

        // TAB SWITCH DETECTION
        document.addEventListener("visibilitychange", function() {

            if (document.hidden) {

                alert("⚠️ Warning: Tab Switching Detected");

            }

        });

        // COPY DETECTION
        document.addEventListener("copy", function() {

            alert("⚠️ Copying is not allowed");

        });

        // PASTE DETECTION
        document.addEventListener("paste", function() {

            alert("⚠️ Pasting is not allowed");

        });

        // RIGHT CLICK BLOCK
        document.addEventListener("contextmenu", function(e) {

            e.preventDefault();

            alert("⚠️ Right Click Disabled");

        });

        </script>
        """,
        height=0
    )


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

def transcribe_audio(audio_file):

    try:

        response = requests.post(
            TRANSCRIBE_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}"
            },
            files={
                "file": (
                    "audio.wav",
                    audio_file,
                    "audio/wav"
                )
            },
            data={
                "model": "whisper-large-v3"
            }
        )

        result = response.json()

        if "text" in result:

            text = result["text"].strip()

            if text == "":
                return "No speech detected"

            return text

        return str(result)

    except Exception as e:

        return f"Transcription Error: {str(e)}"


def load_data():
    if os.path.exists("student_results.xlsx"):
        return pd.read_excel("student_results.xlsx")
    return pd.DataFrame()


# =====================================================
# AUTH SYSTEM
# =====================================================

def admin_login():

    st.markdown("---")
    st.subheader("🔐 Final Exam Authentication")

    username = st.text_input(
        "Examiner Username",
        key="admin_user"
    )

    password = st.text_input(
        "Password",
        type="password",
        key="admin_pass"
    )

    if st.button("Login to Final Exam Mode"):

        try:

            df = pd.read_excel("examiners.xlsx")

            examiner = df[
                (df["Email"] == username) &
                (df["Password"] == password)
            ]

            if not examiner.empty:

                st.session_state.admin_logged_in = True
                st.session_state.examiner_name = examiner.iloc[0]["Name"]
                st.session_state.examiner_email = examiner.iloc[0]["Email"]

                st.success("✅ Authentication Successful")
                st.rerun()

            else:

                st.error("❌ Invalid Credentials")

        except Exception as e:

            st.error(f"Login Error: {e}")



# =====================================================
# QUESTION GENERATION
# =====================================================

def generate_questions(project_text, section, difficulty, examiner_mode, system_mode):

    # =========================================
    # SECTION INSTRUCTIONS
    # =========================================

    section_instruction = ""

    if section == "Basic":
        section_instruction = """
- Ask beginner-friendly understanding questions
- Focus on project purpose and simple concepts
- Avoid deep technical implementation
"""

    elif section == "Technical":
        section_instruction = """
- Ask highly technical implementation questions
- Focus on architecture, APIs, database, models, libraries, workflow, backend logic
- Ask code-level and system design questions
- Questions MUST test real technical understanding
"""

    elif section == "Logical":
        section_instruction = """
- Ask reasoning and problem-solving questions
- Focus on decision-making and project logic
- Ask why specific approaches were chosen
- Include edge cases and optimization thinking
"""

    elif section == "Overall":
        section_instruction = """
- Generate mixed viva questions
- Cover architecture, workflow, logic and implementation
- Simulate complete final viva exam
"""

    elif section == "Technical Depth":
        section_instruction = """
- Ask deep implementation-level technical questions
- Focus on internal working of modules
- Ask scalability, performance and architecture questions
"""

    elif section == "Presentation":
        section_instruction = """
- Ask presentation and explanation related questions
- Focus on communication and clarity
- Ask how student explains project decisions
"""

    elif section == "Defense":
        section_instruction = """
- Ask critical defense questions
- Challenge project limitations
- Ask security, scalability, weaknesses and improvements
- Simulate strict external examiner behavior
"""

    else:
        section_instruction = """
- Ask balanced project-related viva questions
"""

    # =========================================
    # DIFFICULTY INSTRUCTIONS
    # =========================================

    difficulty_instruction = ""

    if difficulty == "Easy":
        difficulty_instruction = """
- Keep questions simple
- Focus on direct understanding
- Avoid tricky or analytical questions
"""

    elif difficulty == "Medium":
        difficulty_instruction = """
- Mix conceptual and technical questions
- Moderate difficulty
"""

    elif difficulty == "Difficult":
        difficulty_instruction = """
- Ask advanced implementation questions
- Include reasoning and architecture analysis
"""

    elif difficulty == "Expert":
        difficulty_instruction = """
- Ask extremely challenging viva questions
- Include optimization, scalability, edge cases and defense
- Simulate expert-level university examiner
"""

    # =========================================
    # EXAMINER MODE INSTRUCTIONS
    # =========================================

    examiner_instruction = ""

    if "Friendly" in examiner_mode:
        examiner_instruction = """
- Tone should be supportive and student-friendly
"""

    elif "Strict" in examiner_mode:
        examiner_instruction = """
- Tone should be strict and professional
- Ask direct and serious viva questions
"""

    elif "Interview" in examiner_mode:
        examiner_instruction = """
- Questions should feel like technical interview
- Focus on real-world implementation
"""

    elif "Rapid Fire" in examiner_mode:
        examiner_instruction = """
- Questions should be short and quick
- Fast-paced viva style
"""

    elif "Defense Panel" in examiner_mode:
        examiner_instruction = """
- Questions should challenge project deeply
- Simulate thesis defense panel
"""

    elif "External Examiner" in examiner_mode:
        examiner_instruction = """
- Professional and strict university external examiner
"""

    elif "AI Strict Judge" in examiner_mode:
        examiner_instruction = """
- Extremely strict evaluation style
- Deep analytical questioning
"""

    # =========================================
    # FINAL PROMPT
    # =========================================

    prompt = f"""
You are an expert university viva examiner.

Your task is to generate EXACTLY 6 viva questions.

==================================================
SYSTEM MODE
==================================================
{system_mode}

==================================================
SECTION TYPE
==================================================
{section}

{section_instruction}

==================================================
DIFFICULTY
==================================================
{difficulty}

{difficulty_instruction}

==================================================
EXAMINER STYLE
==================================================
{examiner_mode}

{examiner_instruction}

==================================================
STRICT RULES
==================================================
- Questions MUST follow selected section strictly
- Questions MUST follow selected difficulty strictly
- Questions MUST follow selected examiner style strictly
- Questions MUST come ONLY from uploaded project
- Do NOT ask generic theory questions
- Do NOT ask unrelated questions
- Each question should focus on DIFFERENT project aspect
- Q1 easiest
- Q6 hardest
- Technical section MUST contain technical questions
- Logical section MUST contain reasoning questions
- Defense section MUST contain critical challenge questions
- Presentation section MUST contain explanation/presentation questions

==================================================
PROJECT CONTENT
==================================================
{project_text[:12000]}

==================================================
OUTPUT FORMAT
==================================================
Q1: ...
Q2: ...
Q3: ...
Q4: ...
Q5: ...
Q6: ...
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
                "temperature": 0.7
            }
        )

        data = res.json()

        if "choices" not in data:

            return [
                f"Explain the {section} aspects of your project.",
                "Describe your project workflow.",
                "What technologies did you use?",
                "Explain your implementation approach.",
                "What challenges did you face?",
                "What future improvements can be made?"
            ]

        raw = data["choices"][0]["message"]["content"]

        questions = []

        for line in raw.split("\n"):

            line = line.strip()

            if line.startswith("Q") and ":" in line:

                q = line.split(":", 1)[1].strip()

                if q:
                    questions.append(q)

        # =========================================
        # SAFETY FALLBACK
        # =========================================

        if len(questions) < 6:

            return [
                f"Explain the {section} aspects of your project.",
                "Describe your project architecture.",
                "Explain the technologies used.",
                "How does your system work internally?",
                "What challenges did you face?",
                "What improvements can be made?"
            ]

        return questions[:6]

    except Exception:

        return [
            f"Explain the {section} aspects of your project.",
            "Describe your project architecture.",
            "Explain the technologies used.",
            "How does your system work internally?",
            "What challenges did you face?",
            "What improvements can be made?"
        ]
# =====================================================
# ANSWER EVALUATION
# =====================================================

def evaluate_answer(q, a):

    prompt = f"""
Question: {q}

Student Answer:
{a}

Evaluate the answer.

Return ONLY in this format:

Marks: X/10
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
# CORRECT ANSWER GENERATION
# =====================================================

def generate_correct_answer(question, project_text):

    prompt = f"""
You are an academic viva examiner.

Based ONLY on the uploaded project content below, provide a simple ideal answer.

Rules:
- Answer ONLY from the project content.
- Do not invent technologies.
- Keep answer short (3-5 lines).
- Use simple student-friendly language.

PROJECT CONTENT:
{project_text[:10000]}

QUESTION:
{question}

IDEAL ANSWER:
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

        return res.json()["choices"][0]["message"]["content"]

    except:
        return "Unable to generate model answer."

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
    pdf.cell(
        200,
        10,
        f"Examiner: {st.session_state.examiner_name}",
        ln=True
    )

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


if st.session_state.mode == "University Final Exam":

    admin_view = st.sidebar.selectbox(
        "Admin Dashboard View",
        ["Off", "Overview", "Students", "Analytics"]
    )

    # MUST be logged in first
    if not st.session_state.admin_logged_in:
        admin_login()
        st.stop()

    st.success("🔐 Examiner Authenticated")
    st.info(
        f"👨‍🏫 Welcome Examiner: {st.session_state.examiner_name}"
    )

    name = st.text_input("Student Name")
    roll = st.text_input("Roll Number")
    dept = st.text_input("Department")
    project_title = st.text_input("Project Title")

    st.markdown("---")

    st.sidebar.error(
        f"⚠️ Warnings: {st.session_state.warnings}/3"
    )
  

# =====================================================
# AUTO TERMINATION
# =====================================================

if st.session_state.warnings >= 3:

    st.error("❌ Exam Terminated Due To Cheating")

    st.stop()

# =====================================================
# FILE UPLOAD
# =====================================================

uploaded_file = st.file_uploader(
    "📄 Upload Project",
    type=["pdf", "docx", "txt", "py", "ipynb"]
)


# =====================================================
# GENERATE QUESTIONS
# =====================================================

if st.button("🚀 Generate Viva Questions"):

    if uploaded_file:

        text = extract_text(uploaded_file)
        st.session_state.project_text = text

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

            answer = ""

            if audio is not None:

                st.audio(audio)

                if st.button(
                    "🧠 Transcribe",
                    key=f"transcribe_{i}"
                ):

                    with st.spinner("Transcribing..."):

                        # READ AUDIO PROPERLY
                        text = transcribe_audio(audio)

                        st.session_state.voice_answers[i] = text

                    st.success("Transcription Complete ✅")

            answer = st.session_state.voice_answers.get(i, "")

            if answer:

                st.text_area(
                    "Transcribed Answer",
                    value=answer,
                    disabled=False,
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

                           marks = evaluate_answer(
                               q,
                               answer
                           )

                           model_answer = generate_correct_answer(
                               q,
                               st.session_state.project_text
                           )
                           

                       st.success("✅ Evaluation Complete")

                       st.metric("Marks", marks)

                       st.markdown("### 🎯 Correct Answer")

                       st.info(model_answer)

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


# ======================
# save to excel
# ======================

def save_to_excel(name, roll, dept, project_title, result):

    try:
        file_path = os.path.join(os.getcwd(), "student_results.xlsx")

        import re

        marks_match = re.search(r'(\d+)', result)

        total_marks = int(marks_match.group(1)) if marks_match else 0

        marks = f"{total_marks}/100"

        status = "PASS" if total_marks >= 50 else "FAIL"

        new_data = pd.DataFrame([{
            "Examiner Name": st.session_state.examiner_name,
            "Student Name": name,
            "Roll Number": roll,
            "Department": dept,
            "Project Title": project_title,
            "Marks": f"{total_marks}/100",
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

        # =====================================================
    # SAVE TO DATABASE BUTTON (ADDED ONLY)
    # =====================================================

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("💾 Save to Database"):

        save_to_excel(
            name,
            roll,
            dept,
            project_title,
            st.session_state.final_result
        )

        st.success("✅ Saved successfully to Excel database!")

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("🔄 Next Student"):

        st.session_state.questions = []
        st.session_state.answers = []
        st.session_state.q_index = 0
        st.session_state.final_result = None
        st.session_state.voice_answers = {}

        st.rerun()


# =====================================================
# ADMIN DASHBOARD (SAAS UI)
# =====================================================

if st.session_state.mode == "University Final Exam" and admin_view != "Off":

    df = load_data()

    st.markdown("## 🧑‍💼 Official Admin Panel")

    # ================= OVERVIEW =================
    if admin_view == "Overview":

        col1, col2, col3, col4 = st.columns(4)

        total = len(df)
        pass_count = len(df[df["Status"] == "PASS"]) if not df.empty else 0
        fail_count = len(df[df["Status"] == "FAIL"]) if not df.empty else 0
        if not df.empty and "Marks" in df.columns:

            df["Marks"] = df["Marks"].astype(str).str.extract(r"(\d+)")[0]
            df["Marks"] = pd.to_numeric(df["Marks"], errors="coerce")

            avg = round(df["Marks"].mean(), 2)

        else:
            avg = 0

        with col1:
            st.markdown(f"""
            <div class="metric-card">
            <h3>🎓 Total Students</h3>
            <h2>{total}</h2>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="metric-card">
            <h3>✅ Passed</h3>
            <h2>{pass_count}</h2>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class="metric-card">
            <h3>❌ Failed</h3>
            <h2>{fail_count}</h2>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            st.markdown(f"""
            <div class="metric-card">
            <h3>📊 Avg Score</h3>
            <h2>{avg}</h2>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        if not df.empty:
            st.bar_chart(df["Status"].value_counts())

    # ================= STUDENTS =================
    elif admin_view == "Students":

        st.subheader("📋 Student Records")

        if not df.empty:
            st.dataframe(df, use_container_width=True)

            search = st.text_input("🔍 Search Student")

            if search:
                filtered = df[df["Student Name"].str.contains(search, case=False)]
                st.dataframe(filtered)
        else:
            st.info("No student records yet.")

    # ================= ANALYTICS =================
    elif admin_view == "Analytics":

        st.subheader("📊 Analytics Dashboard")

        if not df.empty:

            col1, col2 = st.columns(2)

            with col1:
                st.bar_chart(df["Department"].value_counts())

            with col2:
                df["Marks"] = df["Marks"].astype(str).str.extract(r"(\d+)")[0]
                df["Marks"] = pd.to_numeric(df["Marks"], errors="coerce")
                
                st.bar_chart(df["Marks"])

        else:
            st.info("No data available.")

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


