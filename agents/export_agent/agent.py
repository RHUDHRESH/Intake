"""
Export Agent for generating and distributing data extracts.
"""
from typing import Any, Dict, Iterable

from utils.base_agent import BaseAgent
from .tools import export_csv, export_drive, export_email, export_pdf


class ExportAgent(BaseAgent):
    """Routes export requests to the appropriate export helper."""

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        export_format = input_data.get(
            "format", self.config.get("default_format", "csv")
        )
        if not export_format:
            return {"error": "format is required"}

        data = input_data.get("data", [])
        filename = input_data.get("filename", "export")
        target = input_data.get(
            "target", self.config.get("default_target", "local")
        )
        recipient = input_data.get("email")

        if export_format.lower() in {"csv", "pdf", "drive", "email"}:
            if not isinstance(data, Iterable):
                return {"error": "data must be an iterable of records"}

        fmt = export_format.lower()
        if fmt == "csv":
            return await export_csv(data, filename, target)
        if fmt == "pdf":
            return await export_pdf(data, filename, target)
        if fmt == "drive":
            return await export_drive(data, filename)
        if fmt == "email":
            if not recipient:
                return {"error": "email address is required for email exports"}
            return await export_email(data, filename, recipient)

        return {"error": f"Unsupported format: {export_format}"}

    def get_dependencies(self):
        return []
