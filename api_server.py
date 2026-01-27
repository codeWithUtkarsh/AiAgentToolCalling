"""
FastAPI web server for dependency update automation.
Exposes REST endpoints to analyze and update repository dependencies.
"""

import os
import asyncio
import subprocess
import shutil
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from dotenv import load_dotenv


def get_docker_path():
    """Get the absolute path to the docker executable.

    Using absolute paths prevents PyCharm debugger issues where it
    tries to check if 'docker' is a Python script.
    """
    docker_path = shutil.which("docker")
    if docker_path:
        return docker_path

    # Common Docker paths on different systems
    common_paths = [
        "/usr/local/bin/docker",
        "/usr/bin/docker",
        "/opt/homebrew/bin/docker",
        "/Applications/Docker.app/Contents/Resources/bin/docker",
    ]

    for path in common_paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path

    return "docker"  # Fallback to PATH lookup

from auto_update_dependencies import (
    create_main_orchestrator,
    validate_prerequisites
)


# Load environment variables
load_dotenv()


class RepositoryRequest(BaseModel):
    """Request model for repository operations"""
    repository: str = Field(
        ...,
        description="Repository in format 'owner/repo' or full GitHub URL",
        example="facebook/react"
    )
    github_token: Optional[str] = Field(
        None,
        description="GitHub Personal Access Token (optional, uses env var if not provided)"
    )


class JobResponse(BaseModel):
    """Response model for job submissions"""
    job_id: str
    status: str
    message: str
    repository: str


class JobStatusResponse(BaseModel):
    """Response model for job status"""
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# In-memory job storage (use Redis/DB for production)
jobs_storage: Dict[str, Dict[str, Any]] = {}


async def setup_github_mcp_docker():
    """
    Pull and verify GitHub MCP Docker image on startup.
    This ensures the image is ready when endpoints are called.
    """
    print("🐳 Setting up GitHub MCP Docker image...")
    docker_cmd = get_docker_path()

    try:
        # Check if Docker is available
        result = subprocess.run(
            [docker_cmd, "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            raise RuntimeError("Docker is not available")

        print(f"✓ Docker found: {result.stdout.strip()}")

        # Pull the GitHub MCP server image
        print("📥 Pulling GitHub MCP server image (this may take a moment)...")
        pull_result = subprocess.run(
            [docker_cmd, "pull", "ghcr.io/github/github-mcp-server"],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout for pulling
        )

        if pull_result.returncode != 0:
            print(f"⚠️  Warning: Could not pull image: {pull_result.stderr}")
            print("Will attempt to use cached image if available")
        else:
            print("✓ GitHub MCP server image pulled successfully")

        # Verify the image exists
        verify_result = subprocess.run(
            [docker_cmd, "images", "ghcr.io/github/github-mcp-server", "-q"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if not verify_result.stdout.strip():
            raise RuntimeError("GitHub MCP server image not available")

        print("✓ GitHub MCP server image verified")

        # Test that the MCP server can start (quick validation)
        print("🔍 Validating MCP server can start...")
        test_result = subprocess.run(
            [docker_cmd, "run", "--rm", "ghcr.io/github/github-mcp-server", "--help"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if test_result.returncode == 0:
            print("✓ MCP server validated successfully")
        else:
            print("⚠️  MCP server validation returned non-zero (may still work)")

        print("✅ GitHub MCP Docker setup complete")

    except subprocess.TimeoutExpired:
        raise RuntimeError("Docker command timed out")
    except Exception as e:
        raise RuntimeError(f"Failed to setup GitHub MCP Docker: {str(e)}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Sets up GitHub MCP Docker on startup and cleans up on shutdown.
    """
    # Startup
    print("🚀 Starting Dependency Update API Server...")

    try:
        await setup_github_mcp_docker()
        print("✅ Server ready to accept requests")
    except Exception as e:
        print(f"❌ Startup failed: {str(e)}")
        print("⚠️  Server will start but may not function correctly")

    yield

    # Shutdown
    print("👋 Shutting down server...")


# Create FastAPI app with lifespan
app = FastAPI(
    title="Dependency Update Automation API",
    description="Automatically analyze and update repository dependencies with intelligent testing and rollback",
    version="1.0.0",
    lifespan=lifespan
)


async def process_repository_update(
    job_id: str,
    repository: str,
    github_token: Optional[str] = None
):
    """
    Background task to process repository updates.

    Args:
        job_id: Unique job identifier
        repository: Repository to process
        github_token: GitHub token for API operations
    """
    try:
        # Update job status
        jobs_storage[job_id]["status"] = "processing"

        # Validate prerequisites
        print(f"[Job {job_id}] Validating prerequisites...")
        is_valid, message = validate_prerequisites()

        if not is_valid:
            jobs_storage[job_id]["status"] = "failed"
            jobs_storage[job_id]["error"] = message
            return

        # Set GitHub token if provided
        if github_token:
            os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = github_token

        # Create orchestrator agent
        print(f"[Job {job_id}] Creating orchestrator agent...")
        agent = create_main_orchestrator()

        # Run the update process
        print(f"[Job {job_id}] Processing repository: {repository}")

        result = agent.invoke({
            "messages": [("user", f"Analyze and update dependencies for repository: {repository}")]
        })

        # Update job with results
        jobs_storage[job_id]["status"] = "completed"
        jobs_storage[job_id]["result"] = {
            "output": result.get("output", ""),
            "repository": repository
        }

        print(f"[Job {job_id}] ✅ Completed successfully")

    except Exception as e:
        print(f"[Job {job_id}] ❌ Failed: {str(e)}")
        jobs_storage[job_id]["status"] = "failed"
        jobs_storage[job_id]["error"] = str(e)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Dependency Update Automation API",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check including Docker availability"""
    try:
        # Check Docker
        docker_cmd = get_docker_path()
        docker_check = subprocess.run(
            [docker_cmd, "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        docker_available = docker_check.returncode == 0

        # Check GitHub token
        github_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
        token_configured = github_token is not None

        # Check Anthropic API key
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        api_key_configured = anthropic_key is not None

        return {
            "status": "healthy" if all([docker_available, token_configured, api_key_configured]) else "degraded",
            "checks": {
                "docker": "available" if docker_available else "unavailable",
                "github_token": "configured" if token_configured else "missing",
                "anthropic_api_key": "configured" if api_key_configured else "missing"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@app.post("/api/repositories/update", response_model=JobResponse)
async def update_repository(
    request: RepositoryRequest,
    background_tasks: BackgroundTasks
):
    """
    Analyze and update dependencies for a repository.

    This endpoint:
    1. Clones the repository
    2. Analyzes outdated dependencies
    3. Updates and tests dependencies
    4. Creates a PR if successful or an issue if it fails

    The process runs in the background and returns a job ID for status tracking.
    """
    # Generate job ID
    import uuid
    job_id = str(uuid.uuid4())

    # Initialize job
    jobs_storage[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "repository": request.repository,
        "result": None,
        "error": None
    }

    # Add to background tasks
    background_tasks.add_task(
        process_repository_update,
        job_id=job_id,
        repository=request.repository,
        github_token=request.github_token
    )

    return JobResponse(
        job_id=job_id,
        status="queued",
        message="Repository update job has been queued",
        repository=request.repository
    )


@app.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of a repository update job.

    Possible statuses:
    - queued: Job is waiting to be processed
    - processing: Job is currently being processed
    - completed: Job completed successfully
    - failed: Job failed with an error
    """
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs_storage[job_id]

    return JobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        result=job.get("result"),
        error=job.get("error")
    )


@app.get("/api/jobs")
async def list_jobs():
    """List all jobs and their current status"""
    return {
        "total": len(jobs_storage),
        "jobs": list(jobs_storage.values())
    }


if __name__ == "__main__":
    import uvicorn

    # Get port from environment or use default
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    print(f"🚀 Starting server on {host}:{port}")

    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
