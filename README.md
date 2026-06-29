# Nutrition Label Analyzer
An AI-powered nutrition label analysis platform

The app lets users upload nutrition label images, extracts text using OCR, analyzes nutrients and ingredients using AI, and generates a downloadable PDF report. Built with a focus on accuracy, safety, and per-user data isolation.

## Features

- Nutrition label OCR using PaddleOCR (PP-OCRv6)
- AI-powered nutrient and ingredient analysis via Groq API (llama-3.3-70b-versatile)
- Downloadable PDF report with nutrient breakdown, ingredient origins, allergen detection, and %DV calculations
- Label Compliance Checker — checks which mandatory fields are visible on the label
- Per-user authentication via Supabase Auth (ES256 JWT)
- Cloud image storage via Supabase Storage
- Data Management Tool (DMT) — view, download, and delete past uploads
- Allergen detection using rule-based logic (not LLM) for reliability
- FDA-standard %DV calculations (rule-based)
- Macronutrient pie chart in PDF report
- Dark mode compatible UI

## Tech Stack

| Component | Technology |
| --- | --- |
| Backend | FastAPI |
| Frontend | Streamlit |
| OCR | PaddleOCR (PP-OCRv6) |
| AI/LLM | Groq API (llama-3.3-70b-versatile) |
| Database | PostgreSQL via SQLAlchemy (hosted on Supabase) |
| Auth | Supabase Auth (ES256 JWT + JWKS verification) |
| Storage | Supabase Storage |
| PDF Generation | ReportLab |
| Deployment | Render (backend) + Streamlit Cloud (frontend) |

## Project Structure

```
nutrition-label-analyzer/
├── .env.example
├── README.md
├── requirements.txt
├── app/
│   ├── auth.py
│   ├── database.py
│   ├── main.py
│   ├── models/
│   ├── routers/
│   │   ├── admin.py
│   │   ├── label_checker.py
│   │   ├── report.py
│   │   └── upload.py
│   ├── schemas/
│   ├── services/
│   └── utils/
├── pages/
├── auth_page.py
└── streamlit_app.py
```

## Setup Instructions

1. Clone the repo
2. Create and activate virtual environment
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and fill in values
5. Run backend: `uvicorn app.main:app --reload`
6. Run frontend: `streamlit run streamlit_app.py`

## Environment Variables

| Variable | Description | Where to find it |
| --- | --- | --- |
| SUPABASE_URL | Base URL of your Supabase project | Settings > General |
| SUPABASE_ANON_KEY | Legacy anon public key (eyJhbG... format) | Settings > API Keys > Legacy tab |
| SUPABASE_SERVICE_KEY | Legacy service_role secret key | Settings > API Keys > Legacy tab |
| DATABASE_URL | PostgreSQL connection string | Supabase Dashboard > Connect button > Direct |
| GROQ_API_KEY | Groq API key for LLM analysis | console.groq.com |

## Supabase Setup

- Create a Supabase project
- Use legacy API key format (eyJhbG...) not the new sb_publishable format
- Create a private storage bucket called label-images
- Enable Email provider under Authentication > Providers
- JWT verification uses ES256 via JWKS endpoint, not HS256

## API Endpoints

| Method | Endpoint | Auth Required | Description |
| --- | --- | --- | --- |
| GET | /health | No | Health check |
| POST | /upload | Yes | Upload and analyze a label image |
| GET | /report/{upload_id}/download | Yes | Download PDF report |
| GET | /admin/uploads | Yes | List all uploads for current user |
| DELETE | /admin/uploads/{upload_id} | Yes | Delete an upload and its files |
| POST | /check-label | Yes | Run compliance check on a label image |

## Architecture Note

Safety-critical features (allergen detection, %DV calculations) use deterministic rule-based logic rather than LLM generation to avoid hallucination risk. LLM is only used for contextual analysis (ingredient origins, usage context, product summary) where minor inaccuracies are acceptable.

## Deployment

### Backend

Deploy to Render as a web service. 
Build command: `pip install -r requirements.txt`
Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
Add all .env variables in Render's environment settings.

### Frontend

Deploy to Streamlit Community Cloud. Connect GitHub repo, set main file to `streamlit_app.py`, add `BACKEND_URL` as a secret pointing to your Render URL.
