"""
Database Manager for Firestore
"""
import os
from typing import Dict, Any, Optional
from datetime import datetime
import structlog
from google.cloud import firestore
from google.oauth2 import service_account

logger = structlog.get_logger()

class DatabaseManager:
    """Firestore database manager for the intake system"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.db = None
        self.initialize_db()

    def initialize_db(self) -> None:
        """Initialize Firestore client"""
        try:
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
            credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

            if credentials_path and os.path.exists(credentials_path):
                credentials = service_account.Credentials.from_service_account_file(credentials_path)
                self.db = firestore.Client(project=project_id, credentials=credentials)
            else:
                # Use default credentials (for deployment environments)
                self.db = firestore.Client(project=project_id)

            logger.info("Firestore client initialized", project=project_id)

        except Exception as e:
            logger.error("Failed to initialize Firestore", error=str(e))
            self.db = None

    def get_collection(self, collection_name: str):
        """Get a Firestore collection"""
        if not self.db:
            raise RuntimeError("Database not initialized")

        return self.db.collection(collection_name)

    async def store_workflow(self, workflow_data: Dict[str, Any]) -> str:
        """Store a new workflow"""
        try:
            collection = self.get_collection("workflows")

            # Add timestamp if not present
            if "created_at" not in workflow_data:
                workflow_data["created_at"] = datetime.utcnow().isoformat()

            # Store in Firestore
            doc_ref = collection.document(workflow_data["request_id"])
            doc_ref.set(workflow_data)

            logger.info("Workflow stored",
                       request_id=workflow_data["request_id"])

            return workflow_data["request_id"]

        except Exception as e:
            logger.error("Failed to store workflow",
                        error=str(e), request_id=workflow_data.get("request_id"))
            raise

    async def update_workflow(self, request_id: str, update_data: Dict[str, Any]) -> None:
        """Update an existing workflow"""
        try:
            collection = self.get_collection("workflows")
            doc_ref = collection.document(request_id)

            # Add update timestamp
            update_data["updated_at"] = datetime.utcnow().isoformat()

            doc_ref.update(update_data)

            logger.info("Workflow updated", request_id=request_id)

        except Exception as e:
            logger.error("Failed to update workflow",
                        error=str(e), request_id=request_id)
            raise

    async def get_workflow_status(self, request_id: str) -> Dict[str, Any]:
        """Get workflow status"""
        try:
            collection = self.get_collection("workflows")
            doc_ref = collection.document(request_id)
            doc = doc_ref.get()

            if doc.exists:
                return doc.to_dict()
            else:
                return {"error": "Workflow not found", "request_id": request_id}

        except Exception as e:
            logger.error("Failed to get workflow status",
                        error=str(e), request_id=request_id)
            return {"error": str(e), "request_id": request_id}

    async def store_intake_request(self, request_data: Dict[str, Any]) -> str:
        """Store an intake request"""
        try:
            collection = self.get_collection("intake_requests")

            # Add metadata
            request_data["created_at"] = datetime.utcnow().isoformat()
            request_data["status"] = "pending"

            doc_ref = collection.document()
            request_id = doc_ref.id
            request_data["request_id"] = request_id

            doc_ref.set(request_data)

            logger.info("Intake request stored", request_id=request_id)

            return request_id

        except Exception as e:
            logger.error("Failed to store intake request", error=str(e))
            raise

    async def store_agent_output(self, agent_name: str, request_id: str,
                               output_data: Dict[str, Any]) -> None:
        """Store output from a specific agent"""
        try:
            collection = self.get_collection("agent_outputs")

            doc_data = {
                "agent_name": agent_name,
                "request_id": request_id,
                "output_data": output_data,
                "created_at": datetime.utcnow().isoformat()
            }

            doc_ref = collection.document(f"{request_id}_{agent_name}")
            doc_ref.set(doc_data)

            logger.info("Agent output stored",
                       agent=agent_name, request_id=request_id)

        except Exception as e:
            logger.error("Failed to store agent output",
                        error=str(e), agent=agent_name, request_id=request_id)
            raise

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile data"""
        try:
            collection = self.get_collection("user_profiles")
            doc_ref = collection.document(user_id)
            doc = doc_ref.get()

            if doc.exists:
                return doc.to_dict()
            else:
                return {"user_id": user_id, "created_at": datetime.utcnow().isoformat()}

        except Exception as e:
            logger.error("Failed to get user profile",
                        error=str(e), user_id=user_id)
            return {"error": str(e), "user_id": user_id}

    async def update_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> None:
        """Update user profile"""
        try:
            collection = self.get_collection("user_profiles")
            doc_ref = collection.document(user_id)

            profile_data["updated_at"] = datetime.utcnow().isoformat()

            doc_ref.set(profile_data, merge=True)

            logger.info("User profile updated", user_id=user_id)

        except Exception as e:
            logger.error("Failed to update user profile",
                        error=str(e), user_id=user_id)
            raise

    async def get_collection_data(self, collection_name: str,
                                limit: int = 100) -> List[Dict[str, Any]]:
        """Get all documents from a collection"""
        try:
            collection = self.get_collection(collection_name)
            docs = collection.limit(limit).stream()

            results = []
            for doc in docs:
                doc_data = doc.to_dict()
                doc_data["document_id"] = doc.id
                results.append(doc_data)

            return results

        except Exception as e:
            logger.error("Failed to get collection data",
                        error=str(e), collection=collection_name)
            return []

    def is_healthy(self) -> bool:
        """Check if database connection is healthy"""
        return self.db is not None
