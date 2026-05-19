# Task Tracker Frontend (React 19 + Vite + MSAL)

## Setup

```bash
npm install
cp .env.example .env       # fill in your Entra IDs
npm run dev
```

App runs on http://localhost:5173. Click "Sign in with Microsoft", then "Load tasks".

## Entra ID requirements

In your **SPA app registration**:
1. Add platform → "Single-page application" → redirect URI `http://localhost:5173`.
2. API permissions → Add a permission → "My APIs" → select the FastAPI app → check `access_as_user` → "Grant admin consent".
3. Copy the SPA client id into `.env` as `VITE_SPA_CLIENT_ID`.
4. Copy the API app's client id into `.env` as `VITE_API_CLIENT_ID`.
