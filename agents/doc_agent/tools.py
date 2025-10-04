"""
Google Docs tooling for DocAgent.
"""
import asyncio
import os
from functools import lru_cache
from typing import Any, Dict

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")


def _load_credentials():
    if not SERVICE_ACCOUNT_FILE:
        raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS environment variable is not set")
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise RuntimeError(f"Service account file not found: {SERVICE_ACCOUNT_FILE}")
    return service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )


@lru_cache(maxsize=1)
def _get_docs_service():
    creds = _load_credentials()
    return build("docs", "v1", credentials=creds)


@lru_cache(maxsize=1)
def _get_drive_service():
    creds = _load_credentials()
    return build("drive", "v3", credentials=creds)


def _create_doc_sync(title: str, content: str, fmt: str) -> Dict[str, Any]:
    service = _get_docs_service()
    doc = service.documents().create(body={"title": title}).execute()
    doc_id = doc.get("documentId")
    if content:
        requests = [
            {
                "insertText": {
                    "location": {"index": 1},
                    "text": content,
                }
            }
        ]
        service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()
    return {"doc_id": doc_id, "url": f"https://docs.google.com/document/d/{doc_id}/edit"}


def _update_doc_sync(doc_id: str, content: str, fmt: str) -> Dict[str, Any]:
    service = _get_docs_service()
    requests = [
        {"insertText": {"location": {"index": 1}, "text": content}}
    ]
    service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()
    return {"doc_id": doc_id, "status": "updated"}


def _export_doc_sync(doc_id: str, fmt: str) -> Dict[str, Any]:
    if fmt.lower() != "pdf":
        return {"error": f"Format '{fmt}' not supported"}
    # Provide a download link; actual export can be performed by the caller.
    return {
        "doc_id": doc_id,
        "download_url": f"https://docs.google.com/document/d/{doc_id}/export?format=pdf",
    }


async def create_doc(title: str, content: str, fmt: str = "google_docs") -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(_create_doc_sync, title, content, fmt)
    except (RuntimeError, HttpError) as exc:
        return {"error": str(exc)}


async def update_doc(doc_id: str, content: str, fmt: str = "google_docs") -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(_update_doc_sync, doc_id, content, fmt)
    except (RuntimeError, HttpError) as exc:
        return {"error": str(exc)}


async def export_doc(doc_id: str, fmt: str = "pdf") -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(_export_doc_sync, doc_id, fmt)
    except (RuntimeError, HttpError) as exc:
        return {"error": str(exc)}
