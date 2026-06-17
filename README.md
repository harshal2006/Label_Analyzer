# 🏷️ Nutrition Label Analyzer

A full-stack application that accepts images of nutrition / supplement labels, extracts text via **local OCR (PaddleOCR)**, analyses ingredients using **Groq LLM**, and generates downloadable **PDF reports**.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Tech Stack](#tech-stack)
3. [Folder Structure](#folder-structure)
4. [Setup Instructions](#setup-instructions)
5. [Environment Variables](#environment-variables)
6. [Running the Application](#running-the-application)
7. [API Usage Examples](#api-usage-examples)
8. [Database Schema](#database-schema)

---

## Project Overview

A user uploads an image of a supplement or food nutrition label via a Streamlit UI. The system:

1. **Accepts** the image and saves it locally.
2. **Runs OCR** locally using PaddleOCR to extract text.
3. **Parses** nutrients and their values from the OCR text.
4. **Analyses** ingredients via the Groq LLM API to determine health scores, warnings, and purpose.
5. **Stores** the metadata, raw OCR, and analysis in a SQLite database.
6. **Displays** a rich UI with health scores, ingredient breakdowns, and risk flags.
7. **Generates** a downloadable PDF report with detailed nutrient insights.

---

## Tech Stack

| Component          | Technology                   |
|--------------------|------------------------------|
| Language           | Python 3.12                  |
| Backend            | FastAPI                      |
| Frontend           | Streamlit                    |
| Database           | SQLite                       |
| ORM                | SQLAlchemy 2.x               |
| Validation         | Pydantic v2                  |
| OCR                | PaddleOCR                    |
| AI Analysis        | Groq API (llama-3.3-70b-versatile) |
| PDF Generation     | ReportLab                    |
| Server             | Uvicorn                      |

---

## Folder Structure

```
nutrition-label-analyzer/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── database.py          # SQLAlchemy engine, session, Base
│   ├── routers/
│   │   ├── upload.py        # POST /upload endpoint
│   │   └── report.py        # GET /report/{id}/download endpoint
│   ├── models/
│   │   ├── user.py          # User ORM model
│   │   ├── upload.py        # Upload ORM model
│   │   └── analysis.py      # AnalysisResult ORM model
│   └── services/
│       ├── ocr_service.py      # Local PaddleOCR wrapper
│       ├── analysis_service.py # Groq LLM integration
│       ├── groq_service.py     # Groq batched nutrient insights
│       ├── pdf_service.py      # PDF generation using ReportLab
│       └── storage_service.py  # Image storage
├── uploads/                 # Uploaded images (git-ignored)
├── streamlit_app.py         # Streamlit UI frontend
├── requirements.txt
├── .env.example
├── .env                     # Your local config (git-ignored)
└── README.md
```

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone <repo-url>
cd nutrition-label-analyzer
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate      # macOS / Linux
# venv\Scripts\activate       # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env with your Groq API key and database URL
```

---

## Environment Variables

| Variable          | Required | Description                              |
|-------------------|----------|------------------------------------------|
| `DATABASE_URL`    | No       | SQLite URL (default: `sqlite:///./nutrition_label.db`) |
| `GROQ_API_KEY`    | Yes      | API key for Groq LLM analysis            |

---

## Running the Application

This project uses a decoupled architecture. You need to run both the FastAPI backend and the Streamlit frontend.

### 1. Start the FastAPI Backend

```bash
uvicorn app.main:app --reload
```
The API server starts at: **http://127.0.0.1:8000**
Interactive API docs: **http://127.0.0.1:8000/docs**

### 2. Start the Streamlit Frontend

In a new terminal window (ensure your virtual environment is activated):

```bash
streamlit run streamlit_app.py
```
The UI opens in your browser at: **http://localhost:8501**

---

## API Usage Examples

### Health Check

```bash
curl http://127.0.0.1:8000/health
```

### Upload & Analyze Image

```bash
curl -X POST http://127.0.0.1:8000/upload \
  -F "file=@/path/to/nutrition-label.jpg"
```

### Download PDF Report

```bash
curl -O -J http://127.0.0.1:8000/report/1/download
```

---

## Database Schema

```
┌──────────────┐       ┌──────────────┐       ┌───────────────────┐
│    users     │       │   uploads    │       │ analysis_results  │
├──────────────┤       ├──────────────┤       ├───────────────────┤
│ id (PK)      │◄──┐   │ id (PK)      │◄──┐   │ id (PK)           │
│ name         │   └───│ user_id (FK) │   └───│ upload_id (FK)    │
│ email        │       │ image_path   │       │ ocr_text          │
│ created_at   │       │ uploaded_at  │       │ analysis_json     │
└──────────────┘       └──────────────┘       │ created_at        │
                                              └───────────────────┘
```

---

## License

Internal project – Nutrabay Internship 2026.
