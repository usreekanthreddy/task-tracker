"""Pydantic models for tasks. Field names map to Dataverse column logical names."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TaskBase(BaseModel):
    title: str = Field(..., max_length=200, description="Short task title")
    description: Optional[str] = Field(None, max_length=2000)
    status: str = Field("Not Started", description="Not Started | In Progress | Done")
    priority: str = Field("Medium", description="Low | Medium | High")
    assignee_email: Optional[str] = None
    due_date: Optional[datetime] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee_email: Optional[str] = None
    due_date: Optional[datetime] = None


class TaskRead(TaskBase):
    id: str = Field(..., description="Dataverse GUID")
    created_on: Optional[datetime] = None
    modified_on: Optional[datetime] = None
