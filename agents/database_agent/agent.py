"""
Database persistence agent.
"""
from typing import Any, Dict

from utils.base_agent import BaseAgent
from .tools import delete_record, query_data, store_data, update_record


class DatabaseAgent(BaseAgent):
    """Simple CRUD wrapper around Firestore."""

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        action = input_data.get("action", "store")
        collection = input_data.get("collection") or self.config.get(
            "default_collection", "intake_requests"
        )
        data = input_data.get("data")
        record_id = input_data.get("record_id")
        query = input_data.get("query")

        try:
            if action == "store" and data:
                return await store_data(collection, data)
            if action == "query" and query:
                return await query_data(collection, query)
            if action == "update" and record_id and data:
                return await update_record(collection, record_id, data)
            if action == "delete" and record_id:
                return await delete_record(collection, record_id)
        except Exception as exc:  # Keep agent resilient
            return {"error": str(exc)}

        return {"error": "Invalid action or missing parameters"}

    def get_dependencies(self):
        return []
