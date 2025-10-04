"""
Export helpers providing CSV, PDF, Google Drive, and email delivery.
"""
import asyncio
import csv
import os
import smtplib
from collections.abc import Iterable, Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from email.message import EmailMessage

from fpdf import FPDF
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

CSV_MIMETYPE = "text/csv"
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))


def _normalise_records(data: Iterable[Any]) -> List[Dict[str, Any]]:
    if isinstance(data, (str, bytes)):
        raise TypeError("data must be an iterable of mapping objects")
    if not isinstance(data, Iterable):
        raise TypeError("data must be an iterable of mapping objects")

    records: List[Dict[str, Any]] = []
    for row in data:
        if isinstance(row, Mapping):
            records.append(dict(row))
        else:
            raise TypeError("Each record must be a mapping")
    return records


def _derive_fieldnames(rows: List[Dict[str, Any]]) -> List[str]:
    fieldnames = []
    seen = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(str(key))
    return fieldnames


def _export_csv_sync(data: Iterable[Any], filename: str, target: str) -> Dict[str, Any]:
    rows = _normalise_records(data)
    filepath = Path(f"{filename}.csv")
    fieldnames = _derive_fieldnames(rows)

    with filepath.open("w", newline="", encoding="utf-8") as handle:
        if fieldnames:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        else:
            # Create an empty file to signal the export occurred.
            handle.write("")

    return {"file": str(filepath), "target": target}


def _export_pdf_sync(data: Iterable[Any], filename: str, target: str) -> Dict[str, Any]:
    rows = _normalise_records(data)
    filepath = Path(f"{filename}.pdf")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    if not rows:
        pdf.cell(0, 10, txt="No data available", ln=1)
    else:
        for row in rows:
            line = ", ".join(f"{key}: {value}" for key, value in row.items())
            pdf.multi_cell(0, 8, txt=line)

    pdf.output(str(filepath))
    return {"file": str(filepath), "target": target}


def _load_drive_credentials():
    if not SERVICE_ACCOUNT_FILE:
        raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS environment variable is not set")
    credentials_path = Path(SERVICE_ACCOUNT_FILE)
    if not credentials_path.exists():
        raise RuntimeError(f"Service account file not found: {credentials_path}")
    return service_account.Credentials.from_service_account_file(
        str(credentials_path), scopes=DRIVE_SCOPES
    )


@lru_cache(maxsize=1)
def _get_drive_service():
    creds = _load_drive_credentials()
    return build("drive", "v3", credentials=creds)


def _export_drive_sync(data: Iterable[Any], filename: str) -> Dict[str, Any]:
    export_result = _export_csv_sync(data, filename, "drive")
    filepath = Path(export_result["file"])

    service = _get_drive_service()
    media = MediaFileUpload(str(filepath), mimetype=CSV_MIMETYPE, resumable=False)
    metadata = {"name": filepath.name}
    created_file = service.files().create(body=metadata, media_body=media).execute()

    export_result.update({
        "file_id": created_file.get("id"),
        "status": "uploaded",
    })
    return export_result


def _build_email(recipient: str, filepath: Path) -> EmailMessage:
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        raise RuntimeError("Email configuration missing")

    message = EmailMessage()
    message["Subject"] = "Exported Data"
    message["From"] = EMAIL_SENDER
    message["To"] = recipient
    message.set_content("Please find the exported data attached.")

    with filepath.open("rb") as attachment:
        message.add_attachment(
            attachment.read(),
            maintype="text",
            subtype="csv",
            filename=filepath.name,
        )
    return message


def _export_email_sync(data: Iterable[Any], filename: str, recipient: str) -> Dict[str, Any]:
    export_result = _export_csv_sync(data, filename, "email")
    filepath = Path(export_result["file"])
    message = _build_email(recipient, filepath)

    with smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(message)

    export_result.update({"status": "sent", "to": recipient})
    return export_result


async def export_csv(data: Iterable[Any], filename: str, target: str) -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(_export_csv_sync, data, filename, target)
    except (TypeError, OSError) as exc:
        return {"error": str(exc)}


async def export_pdf(data: Iterable[Any], filename: str, target: str) -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(_export_pdf_sync, data, filename, target)
    except (TypeError, OSError) as exc:
        return {"error": str(exc)}


async def export_drive(data: Iterable[Any], filename: str) -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(_export_drive_sync, data, filename)
    except (TypeError, RuntimeError, HttpError, OSError) as exc:
        return {"error": str(exc)}


async def export_email(data: Iterable[Any], filename: str, recipient: str) -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(_export_email_sync, data, filename, recipient)
    except (TypeError, RuntimeError, smtplib.SMTPException, OSError) as exc:
        return {"error": str(exc)}
