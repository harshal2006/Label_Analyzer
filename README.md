# 🏷️ Nutrition Label Analyzer

A production-quality **FastAPI** backend that accepts images of nutrition / supplement labels, extracts text via **Google Cloud Vision OCR**, and stores results in **PostgreSQL**.

> **Week 1 deliverable** – image upload, OCR extraction, and database persistence.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Tech Stack](#tech-stack)
3. [Folder Structure](#folder-structure)
4. [Setup Instructions](#setup-instructions)
5. [PostgreSQL Setup](#postgresql-setup)
6. [Google Vision API Setup](#google-vision-api-setup)
7. [Environment Variables](#environment-variables)
8. [Running the Server](#running-the-server)
9. [API Usage Examples](#api-usage-examples)
10. [Swagger Documentation](#swagger-documentation)

---

## Project Overview

A user uploads an image of a supplement or food nutrition label. The backend:

1. **Accepts** the image upload (`POST /upload`)
2. **Validates** the file type (JPG, JPEG, PNG, WEBP)
3. **Stores** the image on local disk with a UUID filename
4. **Saves** upload metadata in PostgreSQL
5. **Runs OCR** using Google Cloud Vision API
6. **Stores** the extracted text in the database
7. **Returns** the OCR text in a structured JSON response

---

## Tech Stack

| Component          | Technology                   |
|--------------------|------------------------------|
| Language           | Python 3.12                  |
| Framework          | FastAPI                      |
| Database           | PostgreSQL                   |
| ORM                | SQLAlchemy 2.x               |
| Validation         | Pydantic v2                  |
| OCR                | Google Cloud Vision API      |
| Config             | python-dotenv                |
| Server             | Uvicorn                      |

---

## Folder Structure

```
nutrition-label-analyzer/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── database.py           # SQLAlchemy engine, session, Base
│   ├── routers/
│   │   ├── __init__.py
│   │   └── upload.py         # POST /upload endpoint
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py           # User ORM model
│   │   ├── upload.py         # Upload ORM model
│   │   └── analysis.py       # AnalysisResult ORM model
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── upload.py         # Pydantic request/response schemas
│   └── services/
│       ├── __init__.py
│       ├── ocr_service.py    # Google Vision OCR wrapper
│       └── storage_service.py # Image storage & validation
├── uploads/                   # Uploaded images (git-ignored)
├── requirements.txt
├── .env.example
├── .env                       # Your local config (git-ignored)
├── .gitignore
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
python3.12 -m venv venv
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
# Edit .env with your PostgreSQL credentials and GCP key path
```

---

## PostgreSQL Setup

### Install PostgreSQL (macOS – Homebrew)

```bash
brew install postgresql@16
brew services start postgresql@16
```

### Create the database

```bash
psql -U postgres
```

```sql
CREATE DATABASE nutrition_label_db;
-- Optionally create a dedicated user:
-- CREATE USER nla_user WITH PASSWORD 'secure_password';
-- GRANT ALL PRIVILEGES ON DATABASE nutrition_label_db TO nla_user;
\q
```

### Verify connection

```bash
psql -U postgres -d nutrition_label_db -c "SELECT 1;"
```

> **Note:** Tables are created automatically on first server startup via `Base.metadata.create_all()`. For production, migrate to **Alembic**.

---

## Google Vision API Setup

### 1. Create a GCP project

Go to [Google Cloud Console](https://console.cloud.google.com/) and create a new project (or use an existing one).

### 2. Enable the Vision API

```
APIs & Services → Library → Search "Cloud Vision API" → Enable
```

### 3. Create a service account

```
IAM & Admin → Service Accounts → Create Service Account
```

- Name: `nutrition-label-ocr`
- Role: `Cloud Vision API User` (or `Editor` for development)

### 4. Download the JSON key

```
Service Account → Keys → Add Key → Create New Key → JSON
```

Save the file to a secure location on your machine, e.g.:

```
~/keys/nutrition-label-sa.json
```

### 5. Set the environment variable

In your `.env` file:

```
GOOGLE_APPLICATION_CREDENTIALS=/Users/yourname/keys/nutrition-label-sa.json
```

---

## Environment Variables

| Variable                         | Required | Description                              |
|----------------------------------|----------|------------------------------------------|
| `DB_USER`                        | Yes      | PostgreSQL username                      |
| `DB_PASSWORD`                    | Yes      | PostgreSQL password                      |
| `DB_HOST`                        | Yes      | PostgreSQL host (default: `localhost`)    |
| `DB_PORT`                        | Yes      | PostgreSQL port (default: `5432`)        |
| `DB_NAME`                        | Yes      | Database name                            |
| `DATABASE_URL`                   | No       | Full URL (overrides individual DB vars)  |
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes      | Path to GCP service-account JSON key     |

---

## Running the Server

```bash
# Development (with auto-reload)
uvicorn app.main:app --reload

# Custom host/port
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server starts at: **http://127.0.0.1:8000**

---

## API Usage Examples

### Health Check

```bash
curl http://127.0.0.1:8000/health
```

Response:
```json
{"status": "healthy"}
```

### Upload Image (cURL)

```bash
curl -X POST http://127.0.0.1:8000/upload \
  -F "file=@/path/to/nutrition-label.jpg"
```

### Upload Image (Python)

```python
import requests

url = "http://127.0.0.1:8000/upload"
files = {"file": open("nutrition-label.jpg", "rb")}
response = requests.post(url, files=files)
print(response.json())
```

### Success Response (201 Created)

```json
{
  "success": true,
  "upload_id": 1,
  "image_path": "uploads/abc123.jpg",
  "ocr_text": "Protein 24g..."
}
```

### Error Response – Invalid File Type (400)

```json
{
  "detail": "Unsupported file type '.pdf'. Allowed types: .jpeg, .jpg, .png, .webp"
}
```

### Error Response – OCR Failure (500)

```json
{
  "detail": "OCR failure: GOOGLE_APPLICATION_CREDENTIALS is not set."
}
```

---

## Swagger Documentation

Once the server is running, interactive API docs are available at:

| Interface  | URL                                    |
|------------|----------------------------------------|
| Swagger UI | http://127.0.0.1:8000/docs             |
| ReDoc      | http://127.0.0.1:8000/redoc            |
| OpenAPI    | http://127.0.0.1:8000/openapi.json     |

---

## Database Schema

```
┌──────────────┐       ┌──────────────┐       ┌───────────────────┐
│    users     │       │   uploads    │       │ analysis_results  │
├──────────────┤       ├──────────────┤       ├───────────────────┤
│ id (PK)      │◄──┐   │ id (PK)      │◄──┐   │ id (PK)           │
│ name         │   └───│ user_id (FK) │   └───│ upload_id (FK)    │
│ email        │       │ image_path   │       │ ocr_text          │
│ created_at   │       │ uploaded_at  │       │ health_score      │
└──────────────┘       └──────────────┘       │ analysis_json     │
                                               │ created_at        │
                                               └───────────────────┘
```

---

## Next Steps (Week 2+)

- [ ] Ingredient parsing from OCR text
- [ ] Health score calculation
- [ ] Allergen detection
- [ ] User authentication
- [ ] Alembic database migrations
- [ ] Deployment (Docker + Cloud Run)

---

## License

Internal project – Nutrabay Internship 2026.
