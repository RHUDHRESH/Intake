"""
Marketing Intake API with Multi-Agent System
Google Cloud Platform Integration with VertexAI, Firestore, and more
"""
import os
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure structured logging
logger = structlog.get_logger()

# Import our agents and utilities
from agents.orchestrator.agent import OrchestratorAgent
from utils.base_agent import AgentInput
from utils.database import DatabaseManager

# Global variables for system components
orchestrator = None
db_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global orchestrator, db_manager

    logger.info("Starting Marketing Intake API with Multi-Agent System")

    # Initialize database manager
    db_manager = DatabaseManager({})

    # Initialize orchestrator
    config = {
        "max_parallel_agents": int(os.getenv("MAX_PARALLEL_AGENTS", "5")),
        "agent_timeout": int(os.getenv("AGENT_TIMEOUT", "300")),
        "debug": os.getenv("DEBUG", "true").lower() == "true"
    }
    orchestrator = OrchestratorAgent(config)

    # Register agents with orchestrator
    await initialize_agents()

    yield

    logger.info("Shutting down Marketing Intake API")

async def initialize_agents():
    """Initialize and register all agents"""
    global orchestrator

    if not orchestrator:
        return

    # Import and register agents here when they're created
    # For now, we'll just log that the system is ready
    logger.info("Agent system initialized",
               available_agents=len(orchestrator.available_agents))

# API Models
class IntakeRequest(BaseModel):
    intake: Dict[str, Any] = Field(..., description="Intake data for processing")
    user_id: Optional[str] = Field(None, description="User identifier")
    priority: Optional[str] = Field("normal", description="Request priority")

class WorkflowStatusRequest(BaseModel):
    request_id: str

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    database_healthy: bool
    agents_registered: int
    environment: str

# Create FastAPI app
app = FastAPI(
    title="Marketing Intake Multi-Agent API",
    description="Advanced marketing intake system with multiple AI agents",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        database_healthy=db_manager.is_healthy() if db_manager else False,
        agents_registered=len(orchestrator.available_agents) if orchestrator else 0,
        environment=os.getenv("APP_ENV", "development")
    )

@app.post("/intake")
async def process_intake(request: IntakeRequest, background_tasks: BackgroundTasks):
    """Process marketing intake request with multi-agent system"""
    logger.info("Processing intake request", data=request.intake)

    try:
        # Store the intake request
        request_id = await db_manager.store_intake_request({
            "intake_data": request.intake,
            "user_id": request.user_id,
            "priority": request.priority,
            "source": "api"
        })

        # Prepare agent input
        agent_input = AgentInput(
            request_id=request_id,
            input_data=request.intake,
            metadata={
                "user_id": request.user_id,
                "priority": request.priority,
                "submitted_at": datetime.utcnow().isoformat()
            }
        )

        # Execute agents in background for non-blocking response
        background_tasks.add_task(execute_workflow_background, agent_input)

        return {
            "success": True,
            "request_id": request_id,
            "message": "Intake request submitted successfully",
            "status": "processing",
            "estimated_completion": "2-5 minutes"
        }

    except Exception as e:
        logger.error("Error processing intake", error=str(e))
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@app.get("/status/{request_id}", response_model=Dict[str, Any])
async def get_workflow_status(request_id: str):
    """Get the status of a workflow"""
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")

    try:
        status = await orchestrator.get_workflow_status(request_id)
        return status
    except Exception as e:
        logger.error("Error getting workflow status",
                    request_id=request_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Error retrieving status: {str(e)}")

@app.get("/agents", response_model=Dict[str, Any])
async def list_agents():
    """List all available agents and their capabilities"""
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")

    try:
        agents_info = await orchestrator.list_available_agents()
        return {
            "agents": agents_info,
            "total_agents": len(agents_info)
        }
    except Exception as e:
        logger.error("Error listing agents", error=str(e))
        raise HTTPException(status_code=500, detail=f"Error listing agents: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Marketing Intake Multi-Agent API",
        "version": "2.0.0",
        "description": "Advanced marketing intake system with multiple AI agents",
        "endpoints": {
            "health": "GET /health",
            "intake": "POST /intake",
            "status": "GET /status/{request_id}",
            "agents": "GET /agents"
        },
        "features": [
            "Multi-Agent Processing",
            "Google Cloud Integration",
            "Real-time Workflow Tracking",
            "Background Processing",
            "Firestore Database",
            "VertexAI LLM Support"
        ]
    }

async def execute_workflow_background(agent_input: AgentInput):
    """Execute workflow in background"""
    try:
        logger.info("Starting background workflow execution",
                   request_id=agent_input.request_id)

        if orchestrator:
            result = await orchestrator.execute(agent_input)

            logger.info("Background workflow completed",
                       request_id=agent_input.request_id,
                       success=True)
        else:
            logger.error("Orchestrator not available for background execution",
                        request_id=agent_input.request_id)

    except Exception as e:
        logger.error("Background workflow execution failed",
                    request_id=agent_input.request_id, error=str(e))

        # Update workflow status to failed
        if db_manager:
            try:
                await db_manager.update_workflow(agent_input.request_id, {
                    "status": "failed",
                    "error": str(e),
                    "failed_at": datetime.utcnow().isoformat()
                })
            except Exception as db_error:
                logger.error("Failed to update workflow status",
                           request_id=agent_input.request_id, error=str(db_error))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
