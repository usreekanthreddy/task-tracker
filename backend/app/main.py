"""FastAPI app entrypoint.

Run locally:
    uvicorn app.main:app --reload --port 8000

Storage backend selection (pick ONE of the two imports below).
"""
from fastapi import FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware

# --- pick your storage backend here ---
from . import dataverse as store           # Microsoft Dataverse (default)
# from . import sqlite_store as store      # Local SQLite fallback

from .auth import azure_scheme
from .models import TaskCreate, TaskRead, TaskUpdate
from .settings import get_settings

settings = get_settings()

app = FastAPI(
    title="Task Tracker API",
    version="1.0.0",
    description="React + PowerApps friendly API, secured by Entra ID.",
    swagger_ui_oauth2_redirect_url="/oauth2-redirect",
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
        "clientId": settings.SPA_CLIENT_ID,
        "scopes": f"api://{settings.API_CLIENT_ID}/{settings.API_SCOPE_NAME}",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/tasks", response_model=list[TaskRead], tags=["tasks"])
async def list_tasks(user=Security(azure_scheme, scopes=[settings.API_SCOPE_NAME])):
    return await store.list_tasks()


@app.post("/api/tasks", response_model=TaskRead, status_code=201, tags=["tasks"])
async def create_task(payload: TaskCreate, user=Security(azure_scheme, scopes=[settings.API_SCOPE_NAME])):
    return await store.create_task(payload.model_dump())


@app.get("/api/tasks/{task_id}", response_model=TaskRead, tags=["tasks"])
async def get_task(task_id: str, user=Security(azure_scheme, scopes=[settings.API_SCOPE_NAME])):
    record = await store.get_task(task_id)
    if not record:
        raise HTTPException(status_code=404, detail="Task not found")
    return record


@app.patch("/api/tasks/{task_id}", response_model=TaskRead, tags=["tasks"])
async def update_task(task_id: str, payload: TaskUpdate, user=Security(azure_scheme, scopes=[settings.API_SCOPE_NAME])):
    return await store.update_task(task_id, payload.model_dump(exclude_unset=True))


@app.delete("/api/tasks/{task_id}", status_code=204, tags=["tasks"])
async def delete_task(task_id: str, user=Security(azure_scheme, scopes=[settings.API_SCOPE_NAME])):
    await store.delete_task(task_id)
