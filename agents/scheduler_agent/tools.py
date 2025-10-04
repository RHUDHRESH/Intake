"""
Google Calendar and Cloud Scheduler helpers.
"""
import asyncio
import os
from functools import lru_cache
from typing import Any, Dict

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar"]
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")


def _load_credentials():
    if not SERVICE_ACCOUNT_FILE:
        raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS environment variable is not set")
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise RuntimeError(f"Service account file not found: {SERVICE_ACCOUNT_FILE}")
    return service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )


@lru_cache(maxsize=1)
def _get_calendar_service():
    creds = _load_credentials()
    return build("calendar", "v3", credentials=creds)


def _create_event_sync(event_data: Dict[str, Any]) -> Dict[str, Any]:
    service = _get_calendar_service()
    event = service.events().insert(calendarId=CALENDAR_ID, body=event_data).execute()
    return {
        "event_id": event.get("id"),
        "status": "created",
        "link": event.get("htmlLink"),
    }


def _update_event_sync(event_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
    service = _get_calendar_service()
    event = (
        service.events()
        .update(calendarId=CALENDAR_ID, eventId=event_id, body=event_data)
        .execute()
    )
    return {
        "event_id": event_id,
        "status": "updated",
        "link": event.get("htmlLink"),
    }


def _delete_event_sync(event_id: str) -> Dict[str, Any]:
    service = _get_calendar_service()
    service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
    return {"event_id": event_id, "status": "deleted"}


def _create_cloud_job_sync(job_data: Dict[str, Any]) -> Dict[str, Any]:
    # Placeholder until google-cloud-scheduler integration is added.
    print(f"Cloud job scheduled: {job_data}")
    name = job_data.get("name", "unnamed")
    return {"job_id": f"job_{name}", "status": "scheduled"}


async def create_calendar_event(event_data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(_create_event_sync, event_data)
    except (RuntimeError, HttpError) as exc:
        return {"error": str(exc)}


async def update_calendar_event(event_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(_update_event_sync, event_id, event_data)
    except (RuntimeError, HttpError) as exc:
        return {"error": str(exc)}


async def delete_calendar_event(event_id: str) -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(_delete_event_sync, event_id)
    except (RuntimeError, HttpError) as exc:
        return {"error": str(exc)}


async def create_cloud_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(_create_cloud_job_sync, job_data)
    except RuntimeError as exc:
        return {"error": str(exc)}
