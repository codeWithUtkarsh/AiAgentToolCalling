# GitHub MCP Integration Setup

This document explains how to set up and use the GitHub MCP (Model Context Protocol) integration in the Automated Dependency Update System.

## 🚀 Docker-Based Setup (Simplified!)

**The GitHub MCP server now runs using Docker - no local installation required!**

When you use the application, it will automatically:
1. Pull the official GitHub MCP Docker image if not present
2. Run the MCP server in a container
3. Connect and perform GitHub operations
4. Clean up the container after use

**Requirements:**
- Docker must be installed and running ([Install Docker](https://docs.docker.com/get-docker/))
- Internet connection to pull the Docker image
- GitHub Personal Access Token (see below)

## What is GitHub MCP?

GitHub MCP is a Model Context Protocol server that provides programmatic access to GitHub's API through a standardized interface. This integration replaces the need for the GitHub CLI (`gh`) and provides more robust, programmatic access to GitHub operations.

## Benefits of MCP Integration

- **No CLI required**: Works without installing the GitHub CLI
- **Docker-based**: Portable and easy to set up across platforms
- **No manual building**: Docker image is pre-built and ready to use
- **Programmatic access**: Direct API integration for better error handling
- **Standardized interface**: Uses the MCP protocol for consistent tool calling
- **Better error messages**: More detailed error reporting
- **Token-based auth**: Simple environment variable authentication
- **Automatic cleanup**: Docker containers are removed after use

## Prerequisites

### 1. Container Runtime (Docker, OrbStack, etc.)

Install a Docker-compatible container runtime on your system:

**macOS (recommended):**
```bash
# Option 1: OrbStack (lightweight, fast, recommended)
brew install orbstack

# Option 2: Docker Desktop
# Download from https://www.docker.com/products/docker-desktop
```

**Important for macOS Users - Fix PATH:**

If you encounter "docker: command not found" errors in Python, add docker to your PATH:

```bash
# For zsh (macOS default)
echo 'export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# For bash
echo 'export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"' >> ~/.bash_profile
source ~/.bash_profile
```

**Linux:**
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Verify installation
docker --version
```

**Windows:**
- Download Docker Desktop from https://www.docker.com/products/docker-desktop

**Verify it's working:**
```bash
docker ps
# Or for OrbStack/Podman
docker --version
```

The GitHub MCP container image will be automatically pulled when first used:
```
ghcr.io/github/github-mcp-server
```

**Supported Container Runtimes:**
The system auto-detects and works with:
- Docker Desktop
- OrbStack (macOS)
- Podman Desktop
- Rancher Desktop

### 2. Python MCP Package

Install the MCP Python package:

```bash
pip install mcp>=1.0.0
```

Or install all dependencies from requirements.txt:

```bash
pip install -r requirements.txt
```

### 3. GitHub Personal Access Token

Create a GitHub Personal Access Token with the following scopes:

**Required scopes:**
- `repo` - Full control of private repositories
- `workflow` - Update GitHub Action workflows

**Steps to create token:**

1. Go to https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a descriptive name (e.g., "Dependency Update MCP")
4. Select the required scopes: `repo`, `workflow`
5. Click "Generate token"
6. **Copy the token immediately** (you won't be able to see it again)

### 4. Set Environment Variable

Set the GitHub token as an environment variable:

```bash
export GITHUB_PERSONAL_ACCESS_TOKEN='your_token_here'
```

To make it permanent, add to your shell profile:

```bash
# For bash
echo 'export GITHUB_PERSONAL_ACCESS_TOKEN="your_token"' >> ~/.bashrc
source ~/.bashrc

# For zsh
echo 'export GITHUB_PERSONAL_ACCESS_TOKEN="your_token"' >> ~/.zshrc
source ~/.zshrc
```

## Testing the Integration

### Diagnostic Test (Recommended)

Run comprehensive diagnostics to verify everything is set up correctly:

```bash
python diagnose_github_mcp.py
```

Expected output when everything is working:

```
======================================================================
                GitHub MCP Integration Diagnostic Tool
======================================================================

======================================================================
                        1. Prerequisites Check
======================================================================

🧪 Testing: Python version
✅ Python 3.11.14 (compatible)

🧪 Testing: Container runtime
✅ docker installed: Docker version 28.3.3
ℹ️  Runtime type: Docker Desktop / OrbStack / Rancher Desktop

🧪 Testing: Docker runtime status
✅ Docker runtime is working

🧪 Testing: Python packages
✅ mcp: installed (Model Context Protocol client)
✅ anthropic: installed (Anthropic API client)
✅ dotenv: installed (Environment variable loader)

🧪 Testing: GitHub Personal Access Token
✅ Token found: ghp_****

======================================================================
              2. Container Functionality Tests (docker)
======================================================================

🧪 Testing: Container execution test
✅ Docker can run containers successfully

🧪 Testing: GitHub MCP container image
✅ Image available locally: ghcr.io/github/github-mcp-server:latest

======================================================================
                       3. MCP Integration Tests
======================================================================

🧪 Testing: MCP client connection
✅ Connected to GitHub MCP server
✅ Found 15 available tools

🧪 Testing: MCP tool execution
✅ Successfully called MCP tool

======================================================================
                         Test Results Summary
======================================================================

Python Version: PASS
Runtime Installed: PASS
Runtime Working: PASS
Python Packages: PASS
Github Token: PASS
Container Run: PASS
Container Image: PASS
Mcp Connection: PASS
Mcp Tool Call: PASS

Overall: 9/9 tests passed

======================================================================
                          ✅ All Tests Passed!
======================================================================

✅ GitHub MCP integration is working correctly!
```

**If any tests fail**, the diagnostic tool will provide specific troubleshooting instructions for your issue.

### Test from Python

```python
import asyncio
from github_mcp_client import GitHubMCPClient

async def test():
    async with GitHubMCPClient() as client:
        # List available tools
        tools = await client.list_available_tools()
        print(f"Available tools: {tools}")

        # Get repository info
        info = await client.get_repository_info("owner", "repo")
        print(info)

asyncio.run(test())
```

### Test Synchronous Functions

```python
from github_mcp_client import create_pr_sync, create_issue_sync

# Create a PR
result = create_pr_sync(
    repo_name="owner/repo",
    branch_name="feature-branch",
    title="Update dependencies",
    body="Automated dependency updates",
    base_branch="main"
)
print(result)

# Create an issue
result = create_issue_sync(
    repo_name="owner/repo",
    title="Dependency updates failed",
    body="Some updates could not be applied",
    labels="dependencies,automation"
)
print(result)
```

## Architecture

### Components

1. **github_mcp_client.py** - Main MCP client module
   - `GitHubMCPClient` class for async operations
   - `create_pr_sync()` - Synchronous PR creation wrapper
   - `create_issue_sync()` - Synchronous issue creation wrapper
   - Runs GitHub MCP server in stdio mode via Docker

2. **smart_dependency_updater.py** - Updated to use MCP
   - `create_github_pr()` tool - Uses MCP instead of gh CLI
   - `create_github_issue()` tool - Uses MCP instead of gh CLI

3. **auto_update_dependencies.py** - Updated prerequisites
   - Uses Docker to run GitHub MCP server
   - Checks for GITHUB_PERSONAL_ACCESS_TOKEN

### Data Flow

```
Application Tool Call
       ↓
smart_dependency_updater.py
  create_github_pr() or create_github_issue()
       ↓
github_mcp_client.py
  create_pr_sync() or create_issue_sync()
       ↓
GitHubMCPClient (async)
       ↓
MCP Protocol over stdio (IMPORTANT: server runs in stdio mode)
       ↓
Docker Container
  ghcr.io/github/github-mcp-server stdio
       ↓
GitHub REST API
```

### Important: stdio Mode

The GitHub MCP server **must** run in stdio mode for MCP protocol communication:

```bash
docker run -i --rm \
  -e GITHUB_PERSONAL_ACCESS_TOKEN='token' \
  ghcr.io/github/github-mcp-server \
  stdio  # ← Required argument
```

Without the `stdio` argument, the server will not respond to MCP requests.

## Available MCP Tools

The GitHub MCP server provides many tools. Here are the main ones used:

- **create_pull_request** - Create a new pull request
- **create_issue** - Create a new issue
- **get_repository** - Get repository information
- **list_pull_requests** - List pull requests
- **list_issues** - List issues
- **get_pull_request** - Get specific PR details
- **get_issue** - Get specific issue details

## Troubleshooting

### "Docker not found" or "Cannot connect to Docker daemon"

Docker is not installed or not running.

**Solution:**
```bash
# Check if Docker is installed
docker --version

# Check if Docker daemon is running
docker ps

# Start Docker (Linux systemd)
sudo systemctl start docker

# Or use Docker Desktop GUI on macOS/Windows
```

### "Cannot pull Docker image"

Network issues or Docker registry problems.

**Solution:**
```bash
# Manually pull the image
docker pull ghcr.io/github/github-mcp-server

# Check if image exists
docker images | grep github-mcp-server
```

### "GITHUB_PERSONAL_ACCESS_TOKEN not set"

The environment variable is missing.

**Solution:** Set the token:
```bash
export GITHUB_PERSONAL_ACCESS_TOKEN='your_token'
```

### "Connection lost" or async errors

The MCP server may have issues with the connection.

**Potential causes:**
- Invalid token
- Network issues
- Server not responding

**Solution:** Check token validity and retry.

### "Permission denied" when creating PR/Issue

The token doesn't have sufficient permissions.

**Solution:** Ensure token has `repo` and `workflow` scopes.

### Import errors for `mcp` module

The Python MCP package is not installed.

**Solution:**
```bash
pip install mcp>=1.0.0
```

## Comparison: GitHub CLI vs MCP

| Feature | GitHub CLI (gh) | GitHub MCP (Docker) |
|---------|----------------|---------------------|
| Installation | Requires gh CLI binary | Requires Docker only |
| Authentication | `gh auth login` | Environment variable |
| Interface | Command-line subprocess | Python async/await |
| Error Handling | Parse stderr text | Structured responses |
| Integration | Shell commands | Native Python |
| Dependencies | External binary | Docker + Python package |
| Performance | Subprocess overhead | Direct API calls |
| Flexibility | CLI flags only | Full API access |
| Portability | OS-specific binary | Cross-platform (Docker) |
| Updates | Manual upgrades | Docker image updates |

## Migration from GitHub CLI

If you were using the GitHub CLI (`gh`):

**Before (GitHub CLI):**
```bash
# Authentication
gh auth login

# Create PR
gh pr create --repo owner/repo --title "Title" --body "Body"
```

**After (GitHub MCP):**
```bash
# Authentication
export GITHUB_PERSONAL_ACCESS_TOKEN='token'

# Create PR (Python)
python -c "from github_mcp_client import create_pr_sync; print(create_pr_sync('owner/repo', 'branch', 'Title', 'Body'))"
```

## Security Notes

- **Never commit your token** to version control
- Use environment variables or secret management
- Rotate tokens regularly
- Use tokens with minimal required scopes
- Consider using GitHub Apps for production

## References

- [GitHub MCP Server](https://github.com/github/github-mcp-server)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [GitHub Personal Access Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
- [GitHub REST API](https://docs.github.com/en/rest)

## Support

For issues with:
- **GitHub MCP Server**: https://github.com/github/github-mcp-server/issues
- **This integration**: https://github.com/codeWithUtkarsh/AiAgentToolCalling/issues
