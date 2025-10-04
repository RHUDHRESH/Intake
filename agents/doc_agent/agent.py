"""
Document Management Agent
"""
from typing import Any, Dict

from utils.base_agent import BaseAgent
from .tools import create_doc, export_doc, update_doc


class DocAgent(BaseAgent):
    """Creates, updates, and exports documents via Google Docs API."""

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        action = input_data.get("action", self.config.get("default_action", "create"))
        title = input_data.get("title", "New Document")
        content = input_data.get("content", "")
        doc_id = input_data.get("doc_id")
        fmt = input_data.get("format", self.config.get("default_format", "google_docs"))

        if action == "create":
            return await create_doc(title, content, fmt)
        if action == "update" and doc_id:
            return await update_doc(doc_id, content, fmt)
        if action == "export" and doc_id:
            export_format = input_data.get("export_format", fmt)
            return await export_doc(doc_id, export_format)

        return {"error": "Invalid action or missing doc_id"}

    def get_dependencies(self):
        return []
