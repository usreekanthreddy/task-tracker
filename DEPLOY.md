# Deploy to Azure (`azd up`) — one-command deployment

This deploys the React frontend to **Azure Static Web Apps** and the FastAPI backend to **Azure Container Apps**, both in your Azure subscription.

## Architecture provisioned

| Resource | Purpose |
| --- | --- |
| Static Web App (Free tier) | Hosts React build, global CDN |
| Container Apps Environment | Compute boundary for backend |
| Container App | Runs the FastAPI Docker image |
| Container Registry (Basic) | Stores the FastAPI image |
| User-assigned Managed Identity | Lets Container App pull from ACR with no creds |
| Log Analytics + Application Insights | Logs + telemetry |

Rough cost (idle): about **$2–5/month** for Container Apps (scales to zero) + ACR Basic + Log Analytics ingestion. Static Web App Free tier costs $0.

## Prerequisites — one-time setup

1. **Azure CLI** installed: https://aka.ms/InstallAzureCLI
2. **Azure Developer CLI (`azd`)** installed: https://aka.ms/azd-install
3. **Docker Desktop** running (azd needs it to build the backend image): https://www.docker.com/products/docker-desktop
4. An Azure subscription you can deploy into. A free trial subscription works.
5. **Sign in:**
   ```powershell
   az login
   azd auth login
   ```

## Deploy

From the project root:

```powershell
cd C:\dev\task-tracker-project
azd init                  # accept defaults; pick subscription & region (e.g. eastus)
azd env set API_CLIENT_SECRET '<YOUR_API_CLIENT_SECRET>'
azd up
```

`azd up` will:
1. Provision the resource group + all resources from `infra/main.bicep` (~3 min)
2. Build the FastAPI Docker image and push to ACR (~2 min)
3. Build the React app with `npm run build` and upload to Static Web App (~1 min)
4. Print the final URLs

Total: ~6–8 minutes.

## Post-deploy — TWO short manual steps

`azd` prints the deployed URLs at the end. You'll see something like:

```
Resource group:    rg-task-tracker-prod
Static Web App:    https://gentle-cliff-0123abcd.5.azurestaticapps.net
Container App API: https://tt-api-xxxxxxxx.kindforest-12345678.eastus.azurecontainerapps.io
```

### Step 1 — Add the SWA URL to your SPA app registration

The SPA's MSAL config trusts only registered redirect URIs. You need to add the new HTTPS hostname.

1. Go to https://entra.microsoft.com → App registrations → **Task Tracker SPA** → **Authentication**.
2. Under "Single-page application", click **Add URI**.
3. Paste your Static Web App URL (e.g. `https://gentle-cliff-0123abcd.5.azurestaticapps.net`).
4. Save.

### Step 2 — Rebuild the SPA with the production API URL

The deployed React app needs to know the deployed API's URL. Get it from `azd`:

```powershell
azd env get-values
# look at API_BASE_URL
```

Then update `frontend/.env.production` with that URL:

```
VITE_TENANT_ID=<YOUR_TENANT_ID>
VITE_SPA_CLIENT_ID=<YOUR_SPA_CLIENT_ID>
VITE_API_CLIENT_ID=<YOUR_API_CLIENT_ID>
VITE_API_BASE_URL=https://tt-api-xxxxxxxx.kindforest-12345678.eastus.azurecontainerapps.io
VITE_API_SCOPE_NAME=access_as_user
```

Then redeploy just the frontend:

```powershell
azd deploy web
```

## Verify

1. Open the Static Web App URL in your browser.
2. Click **Sign in with Microsoft**.
3. Sign in with your tenant account.
4. Click **Load tasks** — first call cold-starts the Container App (~10 sec); subsequent calls are fast.

## Iteration

| Change | Command |
| --- | --- |
| Edit backend code | `azd deploy api` |
| Edit frontend code | `azd deploy web` |
| Change Bicep | `azd provision` |
| Tear it all down | `azd down --purge` |

## Production-readiness notes

This template gets you to production safely, but for real workloads consider:

- **Tighten ACR SKU** — Basic is fine for one image but can't replicate.
- **Add a custom domain + cert** on the Static Web App (Settings → Custom domains).
- **Restrict Container App CORS** — `main.bicep` allows `*` for first-time setup; the runtime env var `ALLOWED_ORIGINS` is set to just the SWA URL, but the ingress-level CORS is permissive. Tighten by replacing the `corsPolicy.allowedOrigins: ['*']` line with the SWA hostname after first deploy.
- **Rotate the client secret** before it expires (180 days from creation).
- **Switch the backend** from SQLite to Dataverse (or Postgres on Azure Database for PostgreSQL Flexible Server) — Container Apps' filesystem is ephemeral.
- **Enable Container App revisions** for blue-green deploys (`activeRevisionsMode: 'Multiple'`).
- **Add a CI workflow** that runs `azd deploy` on push to main.

## Tear down

```powershell
azd down --purge
```

Removes the resource group and everything in it. Confirmed twice.

## Troubleshooting

- **`Subscription not found`** → run `azd auth login` and pick the right tenant.
- **Docker build fails** → make sure Docker Desktop is running.
- **`AADSTS50011` redirect URI mismatch** after sign-in → didn't do post-deploy Step 1.
- **CORS error after Step 2** → wait 30 seconds for Container App to pick up the new env var, or run `az containerapp update --name <name> --resource-group <rg> --set-env-vars ALLOWED_ORIGINS=https://<swa-url>`.
- **Static Web App build fails** → check the Action logs in the SWA resource; usually missing env var in `.env.production`.
