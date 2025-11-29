# Dependency Update Automation API

A REST API service that automatically analyzes and updates repository dependencies with intelligent testing and rollback capabilities.

## 🚀 Features

- **Docker-based GitHub MCP Integration**: Automatically sets up GitHub MCP server on startup
- **REST API Endpoints**: Expose repository update functionality via HTTP
- **Background Job Processing**: Long-running updates execute in the background
- **Job Status Tracking**: Monitor progress of repository updates
- **Automatic PR/Issue Creation**: Creates PRs on success, issues on failure

## 📋 Prerequisites

1. **Docker**: Must be installed and running
2. **GitHub Personal Access Token**: Required for GitHub operations
3. **Anthropic API Key**: Required for Claude AI agent

## 🏗️ Setup

### Option 1: Docker Compose (Recommended)

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd AiAgentToolCalling
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add:
   ```
   ANTHROPIC_API_KEY=your-anthropic-api-key-here
   ```

3. **Set GitHub token** (in your shell):
   ```bash
   export GITHUB_PERSONAL_ACCESS_TOKEN=your-github-token-here
   ```

4. **Start the services**:
   ```bash
   docker-compose up -d
   ```

   The API will be available at `http://localhost:8000`

### Option 2: Local Development

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and add your ANTHROPIC_API_KEY
   export GITHUB_PERSONAL_ACCESS_TOKEN=your-github-token-here
   ```

3. **Ensure Docker is running**:
   ```bash
   docker --version
   ```

4. **Start the server**:
   ```bash
   python api_server.py
   ```

   The API will be available at `http://localhost:8000`

## 📚 API Documentation

### Base URL
```
http://localhost:8000
```

### Endpoints

#### 1. Health Check
```http
GET /
```

**Response**:
```json
{
  "status": "online",
  "service": "Dependency Update Automation API",
  "version": "1.0.0"
}
```

#### 2. Detailed Health Check
```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "checks": {
    "docker": "available",
    "github_token": "configured",
    "anthropic_api_key": "configured"
  }
}
```

#### 3. Update Repository Dependencies
```http
POST /api/repositories/update
```

**Request Body**:
```json
{
  "repository": "owner/repo",
  "github_token": "optional-token-here"
}
```

**Parameters**:
- `repository` (required): Repository in format `owner/repo` or full GitHub URL
- `github_token` (optional): GitHub Personal Access Token (uses env var if not provided)

**Response**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Repository update job has been queued",
  "repository": "owner/repo"
}
```

**Example using curl**:
```bash
curl -X POST http://localhost:8000/api/repositories/update \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "facebook/react"
  }'
```

**Example using Python**:
```python
import requests

response = requests.post(
    "http://localhost:8000/api/repositories/update",
    json={"repository": "facebook/react"}
)

job = response.json()
print(f"Job ID: {job['job_id']}")
```

#### 4. Get Job Status
```http
GET /api/jobs/{job_id}
```

**Response**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "result": {
    "output": "Successfully updated dependencies and created PR #123",
    "repository": "owner/repo"
  },
  "error": null
}
```

**Job Statuses**:
- `queued`: Job is waiting to be processed
- `processing`: Job is currently being processed
- `completed`: Job completed successfully
- `failed`: Job failed with an error

**Example using curl**:
```bash
curl http://localhost:8000/api/jobs/550e8400-e29b-41d4-a716-446655440000
```

**Example using Python**:
```python
import requests
import time

# Submit job
response = requests.post(
    "http://localhost:8000/api/repositories/update",
    json={"repository": "facebook/react"}
)
job_id = response.json()["job_id"]

# Poll for status
while True:
    status_response = requests.get(
        f"http://localhost:8000/api/jobs/{job_id}"
    )
    job_status = status_response.json()

    print(f"Status: {job_status['status']}")

    if job_status["status"] in ["completed", "failed"]:
        print(f"Result: {job_status}")
        break

    time.sleep(5)
```

#### 5. List All Jobs
```http
GET /api/jobs
```

**Response**:
```json
{
  "total": 5,
  "jobs": [
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "completed",
      "repository": "owner/repo1",
      "result": {...},
      "error": null
    },
    {
      "job_id": "660e8400-e29b-41d4-a716-446655440001",
      "status": "processing",
      "repository": "owner/repo2",
      "result": null,
      "error": null
    }
  ]
}
```

## 🔧 Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key for Claude |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | Yes | GitHub token with repo permissions |
| `PORT` | No | Server port (default: 8000) |
| `HOST` | No | Server host (default: 0.0.0.0) |

### GitHub Token Permissions

Your GitHub token needs the following permissions:
- `repo` (full control of private repositories)
- `workflow` (update GitHub Action workflows)

## 🧪 Testing

### Manual Testing

1. **Check health**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Submit a test job**:
   ```bash
   curl -X POST http://localhost:8000/api/repositories/update \
     -H "Content-Type: application/json" \
     -d '{"repository": "owner/repo"}'
   ```

3. **Check job status**:
   ```bash
   curl http://localhost:8000/api/jobs/{job_id}
   ```

### Interactive API Documentation

FastAPI provides automatic interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🐳 Docker Commands

### Start services:
```bash
docker-compose up -d
```

### View logs:
```bash
docker-compose logs -f api-server
```

### Stop services:
```bash
docker-compose down
```

### Rebuild after code changes:
```bash
docker-compose up -d --build
```

## 📊 How It Works

1. **Startup**: On server start, the GitHub MCP Docker image is pulled and verified
2. **Job Submission**: Client submits repository via POST to `/api/repositories/update`
3. **Background Processing**: Job runs in background with these steps:
   - Clone repository
   - Detect package manager (npm/pip)
   - Find outdated dependencies
   - Apply updates
   - Run tests
   - If successful: Create PR
   - If failed: Rollback and create issue
4. **Status Tracking**: Client polls `/api/jobs/{job_id}` for status
5. **Completion**: Job completes with PR/issue created on GitHub

## 🔍 Monitoring

### Check running containers:
```bash
docker ps
```

### View API server logs:
```bash
docker-compose logs -f api-server
```

### View GitHub MCP logs:
```bash
docker-compose logs -f github-mcp
```

## 🚨 Troubleshooting

### "Docker is not available"
- Ensure Docker is installed and running
- Check: `docker --version`

### "GitHub token missing"
- Set: `export GITHUB_PERSONAL_ACCESS_TOKEN=your-token`
- Or include in request body

### "Anthropic API key missing"
- Add to `.env` file: `ANTHROPIC_API_KEY=your-key`

### Jobs stuck in "queued" status
- Check server logs: `docker-compose logs -f api-server`
- Verify prerequisites: `curl http://localhost:8000/health`

### Permission denied when pulling Docker image
- Login to GitHub container registry if needed
- Or use `docker pull ghcr.io/github/github-mcp-server` manually

## 🔐 Security Notes

- Never commit `.env` file with secrets
- Keep GitHub token secure (don't log or expose)
- Use environment variables for all sensitive data
- Consider implementing API authentication for production use

## 📖 Related Documentation

- [Main README](README.md) - General project overview
- [GitHub MCP Setup](GITHUB_MCP_SETUP.md) - GitHub MCP configuration
- [FastAPI Documentation](https://fastapi.tiangolo.com/) - FastAPI framework

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests.

## 📝 License

[Your License Here]
