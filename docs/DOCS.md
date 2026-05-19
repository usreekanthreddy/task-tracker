# Task Tracker — Learning Documentation

A beginner-friendly walkthrough of a project that combines **React**, **Python (FastAPI)**, and **Microsoft PowerApps**, all sharing a Microsoft **Dataverse** database and authenticated through **Microsoft Entra ID** (formerly Azure AD).

---

## 1. Why these three technologies together?

Most real businesses don't standardize on one stack. Developers want React for rich, custom interfaces. Backend teams reach for Python because it has the richest ecosystem for APIs, ML, and integrations. Business users prefer **low-code** tools like PowerApps so they can build small apps without coding. The valuable lesson is that all three can coexist if they share a backend and a single identity provider.

In this project:

- **React** is the polished, customer-facing UI.
- **Python (FastAPI)** is the API that enforces business rules, secures the data, and talks to Dataverse.
- **PowerApps** is a low-code canvas app for internal users (managers, ops) who don't need the full React UI.
- **Microsoft Dataverse** stores the data once — everyone reads/writes the same table.
- **Microsoft Entra ID** issues identity tokens that all three layers trust.

---

## 2. Architecture overview

```
            +--------------------+         +--------------------+
            |    React 19 SPA    |         |  PowerApps Canvas  |
            |  (MSAL.js login)   |         |   App (Power Fx)   |
            +----------+---------+         +----------+---------+
                       |                              |
            Bearer JWT |                              | Native or
                       v                              | Custom connector
            +----------+---------+                    |
            |   FastAPI backend  |<-------------------+
            |   (Python 3.11+)   |
            +----------+---------+
                       |
            App token  |
                       v
            +----------+---------+
            | Dataverse Web API  |
            |  (cr123_tasks)     |
            +--------------------+
```

**Two paths to Dataverse:**
1. *React → FastAPI → Dataverse*: gives you a place to put server-side rules.
2. *PowerApps → Dataverse* (native connector): great for read-heavy internal views.

Both paths use **Entra ID** to authenticate the user. The same user gets the same data either way.

---

## 3. Technology cheat sheet

| Layer | Tech | What it does | Why we chose it |
| --- | --- | --- | --- |
| Frontend | React 19 + Vite + TypeScript | Single-page web app | Industry standard; React 19 brings Actions & `use` hook; Vite gives instant dev reloads |
| Auth (client) | @azure/msal-browser + @azure/msal-react | Sign-in with Microsoft + token acquisition | Official Microsoft library, handles PKCE and silent renew |
| API | FastAPI 0.115+ | REST API with auto OpenAPI docs | Async by default, fastest Python framework, great type safety |
| Auth (API) | fastapi-azure-auth | Validates incoming JWTs from Entra ID | Drop-in middleware, supports single-tenant SPA flow |
| Dataverse client | msal + httpx | Server gets its own Dataverse token | Standard MSAL flow + async HTTP |
| Database | Microsoft Dataverse | Stores tasks | Tight PowerApps integration, enterprise security, no DB to babysit |
| Low-code UI | PowerApps Canvas | Drag-and-drop UI for internal users | Lets non-developers extend the app |
| Identity | Microsoft Entra ID | Issues access tokens | Single sign-on across all three apps |

---

## 4. Setup — step by step

### 4.1 Tenant prerequisites

Open https://entra.microsoft.com (sign in as a tenant admin):

1. **Create the API app registration**
   - Name: `Task Tracker API`
   - Single tenant
   - Don't set a redirect URI
   - After creation: *Expose an API* → set Application ID URI to `api://<API_CLIENT_ID>` → add scope `access_as_user` (admin + user consent).
   - *Certificates & secrets* → New client secret → copy the **Value** immediately.
   - *API permissions* → Add `Dynamics CRM / user_impersonation` and `Dataverse / user_impersonation` → Grant admin consent.

2. **Create the SPA app registration**
   - Name: `Task Tracker SPA`
   - Single tenant, redirect type **Single-page application**, URI `http://localhost:5173`.
   - *API permissions* → Add a permission → My APIs → pick `Task Tracker API` → check `access_as_user` → Grant admin consent.

3. **Create the Dataverse environment** (https://admin.powerplatform.microsoft.com)
   - Create a Dataverse environment (note its URL — looks like `https://orgXXXXX.crm.dynamics.com`).

4. **Create the `Tasks` table** in your environment (`make.powerapps.com` → Tables → New table)
   - Display name `Task`, schema name `cr123_tasks`.
   - Columns: `cr123_title` (text), `cr123_description` (multiline), `cr123_status` (choice), `cr123_priority` (choice), `cr123_assigneeemail` (text), `cr123_duedate` (date/time).

5. **Give your API app permission to your environment**
   - Power Platform Admin Center → your environment → Settings → Users + permissions → Application users → New app user → pick `Task Tracker API` → assign the *System Customizer* or a custom role with read/write on `Tasks`.

### 4.2 Run the backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # fill values
uvicorn app.main:app --reload --port 8000
```

Visit http://localhost:8000/docs. Click **Authorize**, sign in with your Microsoft account, and you can now hit `GET /api/tasks` straight from Swagger UI.

### 4.3 Run the React frontend

```bash
cd frontend
npm install
cp .env.example .env       # fill the same values
npm run dev
```

Open http://localhost:5173 → **Sign in with Microsoft** → **Load tasks**.

### 4.4 Build the PowerApps canvas app

Follow `powerapps/BUILD_GUIDE.md`. It takes 10–15 minutes if you've already created the Tasks table.

---

## 5. How the integration actually works

### 5.1 The token dance

```
User clicks "Sign in" in React
   ↓
MSAL.js redirects to login.microsoftonline.com
   ↓
User authenticates → Entra ID redirects back with an authorization code
   ↓
MSAL.js exchanges code for two tokens:
   • id_token (proves who the user is)
   • access_token (proves they can call our API)
   ↓
React calls FastAPI: GET /api/tasks
   Authorization: Bearer <access_token>
   ↓
FastAPI (via fastapi-azure-auth) validates the token's
signature, issuer (your tenant), and audience (your API).
   ↓
FastAPI then needs its OWN token to call Dataverse:
   MSAL ConfidentialClientApplication.acquire_token_for_client(
     scopes=["https://orgXXX.crm.dynamics.com/.default"]
   )
   ↓
FastAPI calls Dataverse Web API and returns the data to React.
```

### 5.2 Why two app registrations?

- The **SPA** app is *public* — its client id is shipped to the browser. It can request tokens but cannot prove identity with a secret.
- The **API** app is *confidential* — it has a client secret. Only this app can ask Dataverse for an app-only token using client credentials.

The SPA token's `aud` claim is the API app's id, so the API can verify "this token was minted for me".

### 5.3 CORS

The React app runs on `http://localhost:5173` and calls FastAPI on `http://localhost:8000`. The browser blocks cross-origin requests unless the server explicitly opts in — that's what the `CORSMiddleware` block in `app/main.py` is doing.

### 5.4 PowerApps' shortcut

PowerApps doesn't need to call FastAPI at all for basic CRUD — its native Dataverse connector talks straight to the same `cr123_tasks` table. The user is already signed in to Power Apps, so Entra ID hands the canvas app a Dataverse token transparently.

Use the **custom connector** path when you want PowerApps to call your FastAPI (e.g. because the API runs validation that lives in Python only).

---

## 6. Common pitfalls and how to debug them

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `AADSTS65001 consent required` on React sign-in | Admin consent missing on the API scope | In SPA app → API permissions → Grant admin consent |
| `401 Unauthorized` from FastAPI | Token has wrong audience, or `API_CLIENT_ID` mismatched | Decode token at jwt.ms — check `aud` matches `api://<API_CLIENT_ID>` |
| Dataverse returns 403 | API app user not assigned a security role in environment | Power Platform Admin → Application users → assign role |
| CORS blocked in browser | Origin not in `ALLOWED_ORIGINS` | Update backend `.env`, restart uvicorn |
| `Could not get token` from MSAL Python | Wrong tenant id or expired secret | Verify `TENANT_ID` and create a new secret |
| PowerApps "Network error" calling custom connector | Redirect URL not added to API app | Copy the URL shown when saving connector into API app → Authentication → Redirect URIs |
| FastAPI startup hangs | `openid_config.load_config()` can't reach Microsoft | Check outbound network / firewall |

Practical debugging tip: paste any JWT into **https://jwt.ms** to see its claims (tenant id, audience, scopes). 80% of auth bugs become obvious from this one step.

---

## 7. Glossary

- **Entra ID**: Microsoft's identity service (renamed from Azure Active Directory in 2023). Issues tokens.
- **App registration**: A definition of an application that wants to authenticate users or call APIs.
- **Tenant**: A single instance of Entra ID (typically one per organization).
- **Dataverse**: Microsoft's enterprise data platform that powers Power Apps. Think "managed database + security + APIs".
- **MSAL**: Microsoft Authentication Library — official SDK for getting tokens. There's a flavor per language (msal-browser, MSAL Python, etc.).
- **JWT (access token)**: A signed JSON blob proving who you are and what you can do.
- **OAuth scope**: A string that names a permission, e.g. `access_as_user`.
- **OData**: A standard for REST APIs over data — Dataverse Web API speaks OData v4.
- **Power Fx**: Excel-like formula language used in PowerApps canvas apps.
- **Custom connector**: A wrapper that lets Power Platform apps call any REST API as if it were native.
- **CORS**: Cross-Origin Resource Sharing — browser security rule for cross-domain API calls.

---

## 8. Where to go next

- Add **Power Automate** flow that emails the assignee when a task is created.
- Add server-side **role-based access** in FastAPI by reading the `roles` claim from the JWT.
- Add **Application Insights** for end-to-end observability.
- Deploy: React to **Azure Static Web Apps**, FastAPI to **Azure Container Apps**, PowerApps stays in the Power Platform.

---

## Sources & official docs

- Microsoft Learn — Tutorial: React SPA + MSAL: https://learn.microsoft.com/en-us/entra/identity-platform/tutorial-single-page-app-react-prepare-app
- Microsoft Learn — Dataverse Web API authentication: https://learn.microsoft.com/en-us/power-apps/developer/data-platform/webapi/authenticate-web-api
- Microsoft Learn — Use the Dataverse Web API: https://learn.microsoft.com/en-us/power-apps/developer/data-platform/webapi/overview
- Intility — fastapi-azure-auth: https://intility.github.io/fastapi-azure-auth/
- Vite docs (current): https://vite.dev/guide/
- PowerApps custom connector with delegated permissions: https://ashiqf.com/2025/03/29/calling-dataverse-web-api-using-delegated-permissions-in-a-custom-connector/

*Last verified against Microsoft documentation: May 2026.*
