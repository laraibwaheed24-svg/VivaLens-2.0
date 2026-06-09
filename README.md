# 🎓 VivaLens 2.0

### Next-Generation Viva Examination System

VivaLens 2.0 is an intelligent viva examination and thesis defense platform that automates project-based oral assessments using Artificial Intelligence. The system generates project-specific viva questions, evaluates student responses, supports voice-based interaction, and provides detailed assessment reports for both students and examiners.

---

## 🚀 Features

### 🎯 AI-Powered Question Generation

* Generates project-specific viva questions from uploaded documents.
* Supports:

  * Basic Questions
  * Technical Questions
  * Logical Questions
  * Technical Depth Questions
  * Presentation Questions
  * Defense Questions

### 🎓 Student Practice Mode

* Practice unlimited AI-generated viva sessions.
* Text and voice answer support.
* Instant answer evaluation.
* Marks awarded for each response.
* AI-generated model answers based on uploaded project content.
* Progress tracking throughout the viva.

### 🏛 University Final Exam Mode

* Secure examiner authentication.
* Professional viva examination workflow.
* Student information collection.
* AI-assisted final evaluation.
* Detailed performance report generation.

### 🎤 Voice-Based Viva

* Speech-to-text transcription using AI.
* Students can answer questions verbally.
* Automatic answer conversion for evaluation.

### 📄 Project Document Support

Supports multiple file formats:

* PDF
* DOCX
* TXT
* Python Files (.py)
* Jupyter Notebooks (.ipynb)

### 📊 Automated Final Evaluation

Generates:

* Overall Score (/100)
* Technical Skills Assessment
* Communication Skills Assessment
* Strengths
* Weaknesses
* Final Verdict

### 📑 PDF Report Generation

Automatically generates downloadable viva reports containing:

* Student Details
* Project Information
* Examiner Information
* Final Evaluation Results

### 🧑‍🏫 Examiner Authentication System

* Secure examiner login.
* Multiple examiner support.
* Examiner name attached to reports and records.
* Separate access for official examinations.

### 💾 Excel Database Storage

Stores:

* Examiner Name
* Student Name
* Roll Number
* Department
* Project Title
* Marks
* Status (PASS/FAIL)
* Timestamp

### 📈 Admin Dashboard

#### Overview

* Total Students
* Passed Students
* Failed Students
* Average Score

#### Student Records

* View all saved records
* Search students instantly

#### Analytics

* Department-wise statistics
* Student marks analytics

#### Examiner Management

* Add new examiners
* Manage examiner credentials

### 🛡 Anti-Cheating Features

* Tab-switch detection
* Copy detection
* Paste detection
* Right-click blocking
* Warning tracking system
* Automatic termination after multiple violations

### 🔄 Resume Viva Capability

* Save unfinished viva sessions
* Resume progress after re-login
* Continue from the last answered question

---

## 🏗 System Architecture

1. User uploads project document.
2. Project content is extracted and processed.
3. AI generates project-specific viva questions.
4. Student responds using text or voice.
5. AI evaluates answers.
6. Results are stored in the database.
7. Final report is generated.
8. PDF report becomes available for download.
9. Admin dashboard provides analytics and monitoring.

---

## 🛠 Technologies Used

### Frontend

* Streamlit

### Backend

* Python

### AI Models

* Groq API
* Llama 3.1
* Whisper Speech Recognition

### Data Processing

* Pandas
* OpenPyXL

### Document Processing

* PyPDF2
* Python-Docx

### Reporting

* FPDF

### Storage

* Excel Database (.xlsx)

---

## 📂 Project Structure

```text
VivaLens/
│
├── app.py
├── examiners.xlsx
├── student_results.xlsx
├── ongoing_vivas.xlsx
├── requirements.txt
├── README.md
│
├── reports/
│   └── generated_pdf_reports
│
└── assets/
    └── images
```

---

## ⚙ Installation

### Clone Repository

```bash
git clone https://github.com/yourusername/VivaLens.git
cd VivaLens
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure API Key

Create a Streamlit secrets file:

```toml
GROQ_API_KEY = "your_api_key_here"
```

### Run Application

```bash
streamlit run app.py
```

---

## 🎯 Future Enhancements

* Face detection for candidate verification
* Live proctoring system
* Webcam-based cheating detection
* Cloud database integration
* Multi-university deployment
* Role-based access control
* Email report delivery
* Performance benchmarking across departments

---

## 👨‍💻 Developer

**Laraib**
AI & Machine Learning Enthusiast

VivaLens 2.0 was developed to modernize traditional viva examinations through AI-powered automation, intelligent assessment, and scalable academic evaluation workflows.

---

## 📜 License

This project is developed for educational and research purposes.
All rights reserved.
