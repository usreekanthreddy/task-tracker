"""Async client for the Microsoft Dataverse Web API.

Uses MSAL ConfidentialClientApplication with client-credentials flow to get a
token for the Dataverse environment, then calls the OData v4 endpoints.
"""
from __future__ import annotations

import time
from typing import Any, Optional

import httpx
import msal

from .settings import get_settings

_settings = get_settings()
_token_cache: dict[str, Any] = {"value": None, "expires": 0}


def _get_app_token() -> str:
    now = time.time()
    if _token_cache["value"] and _token_cache["expires"] - 60 > now:
        return _token_cache["value"]
    app = msal.ConfidentialClientApplication(
        client_id=_settings.API_CLIENT_ID,
        client_credential=_settings.API_CLIENT_SECRET,
        authority=_settings.authority,
    )
    result = app.acquire_token_for_client(scopes=[_settings.dataverse_scope])
    if "access_token" not in result:
        raise RuntimeError(f"Dataverse token failed: {result.get('error_description')}")
    _token_cache["value"] = result["access_token"]
    _token_cache["expires"] = now + int(result.get("expires_in", 3600))
    return result["access_token"]


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_get_app_token()}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
        "Prefer": "return=representation",
    }


def _base_url() -> str:
    return f"{_settings.DATAVERSE_URL.rstrip('/')}/api/data/v9.2"


# Publisher prefix for the vkn2k tenant. Adjust if you import this into another env.
FIELD_MAP = {
    "title": "cr0b4_title",
    "description": "cr0b4_description",
    "status": "cr0b4_status",
    "priority": "cr0b4_priority",
    "assignee_email": "cr0b4_assigneeemail",
    "due_date": "cr0b4_duedate",
}

STATUS_TO_INT = {"Not Started": 1, "In Progress": 2, "Done": 3}
STATUS_FROM_INT = {v: k for k, v in STATUS_TO_INT.items()}
PRIORITY_TO_INT = {"Low": 1, "Medium": 2, "High": 3}
PRIORITY_FROM_INT = {v: k for k, v in PRIORITY_TO_INT.items()}


def _to_dv(payload: dict) -> dict:
    out = {}
    for k, v in payload.items():
        if v is None or k not in FIELD_MAP:
            continue
        if k == "status" and isinstance(v, str):
            v = STATUS_TO_INT.get(v, 1)
        elif k == "priority" and isinstance(v, str):
            v = PRIORITY_TO_INT.get(v, 2)
        elif k == "due_date" and hasattr(v, "isoformat"):
            v = v.isoformat()
        out[FIELD_MAP[k]] = v
    return out


def _from_dv(record: dict) -> dict:
    out = {}
    for logical, dv in FIELD_MAP.items():
        out[logical] = record.get(dv)
    if isinstance(out.get("status"), int):
        out["status"] = STATUS_FROM_INT.get(out["status"], "Not Started")
    if isinstance(out.get("priority"), int):
        out["priority"] = PRIORITY_FROM_INT.get(out["priority"], "Medium")
    out["id"] = record.get("cr0b4_taskid")
    out["created_on"] = record.get("createdon")
    out["modified_on"] = record.get("modifiedon")
    return out


async def list_tasks() -> list[dict]:
    url = f"{_base_url()}/{_settings.DATAVERSE_TABLE}"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, headers=_headers())
        r.raise_for_status()
        return [_from_dv(rec) for rec in r.json().get("value", [])]


async def get_task(task_id: str) -> Optional[dict]:
    url = f"{_base_url()}/{_settings.DATAVERSE_TABLE}({task_id})"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, headers=_headers())
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return _from_dv(r.json())


async def create_task(payload: dict) -> dict:
    url = f"{_base_url()}/{_settings.DATAVERSE_TABLE}"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers=_headers(), json=_to_dv(payload))
        r.raise_for_status()
        return _from_dv(r.json())


async def update_task(task_id: str, payload: dict) -> dict:
    url = f"{_base_url()}/{_settings.DATAVERSE_TABLE}({task_id})"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.patch(url, headers=_headers(), json=_to_dv(payload))
        r.raise_for_status()
        return _from_dv(r.json())


async def delete_task(task_id: str) -> None:
    url = f"{_base_url()}/{_settings.DATAVERSE_TABLE}({task_id})"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.delete(url, headers=_headers())
        if r.status_code not in (204, 404):
            r.raise_for_status()
