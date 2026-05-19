# Task Tracker API (FastAPI + Dataverse + Entra ID)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then fill in the real values
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs to test endpoints. Click "Authorize" in Swagger UI to sign in with your Entra ID account.

## Required Entra ID app registrations

1. **API app** (`API_CLIENT_ID`): expose an API scope named `access_as_user`; create a client secret; grant `https://<your-dataverse>.dynamics.com/.default` application permission and admin-consent it.
2. **SPA app** (`SPA_CLIENT_ID`): add a "Single-page application" redirect URI for `http://localhost:5173`; grant delegated permission to the API scope above and admin-consent it.

## Required Dataverse setup

Create a custom table (default schema name `cr123_tasks`) with columns:
- `cr123_title` (Single Line Text)
- `cr123_description` (Multiline Text)
- `cr123_status` (Choice: Not Started / In Progress / Done)
- `cr123_priority` (Choice: Low / Medium / High)
- `cr123_assigneeemail` (Single Line Text)
- `cr123_duedate` (Date/Time)

If your prefix differs, update `FIELD_MAP` in `app/dataverse.py` and `DATAVERSE_TABLE` in `.env`.
