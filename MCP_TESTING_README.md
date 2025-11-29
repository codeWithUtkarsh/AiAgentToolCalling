# GitHub MCP Testing Tools

This directory contains testing tools to verify and diagnose GitHub MCP (Model Context Protocol) integration.

## 📋 Available Test Scripts

### 1. Quick Test (`quick_test_mcp.py`)

**Purpose:** Fast connection check (< 10 seconds)

**Use when:**
- You want to quickly verify MCP is working
- You've already set everything up and just need confirmation
- You're debugging a specific connection issue

**Usage:**
```bash
python quick_test_mcp.py
```

**Example output:**
```
🚀 Quick GitHub MCP Connection Test
==================================================
✅ Token found (40 chars)
✅ MCP client module loaded

🔌 Connecting to GitHub MCP server...
✅ Connected to GitHub MCP server!
✅ 15 tools available

📋 Available tools (first 5):
   • create_pull_request
   • create_issue
   • get_repository
   • list_pull_requests
   • get_pull_request

==================================================
✅ GitHub MCP is working correctly!
==================================================
```

---

### 2. Comprehensive Diagnostics (`diagnose_github_mcp.py`)

**Purpose:** Complete system analysis and troubleshooting (30-60 seconds)

**Use when:**
- First-time setup
- Something isn't working and you need to find out why
- You want a complete health check
- You're setting up on a new machine

**Usage:**
```bash
python diagnose_github_mcp.py
```

**What it tests:**
1. **Prerequisites:**
   - Python version compatibility (3.8+)
   - Docker installation
   - Docker daemon status
   - Required Python packages (mcp, anthropic, dotenv)
   - GitHub Personal Access Token

2. **Docker Functionality:**
   - Ability to run containers
   - GitHub MCP Docker image availability
   - Automatic image pulling if needed

3. **MCP Integration:**
   - Connection to GitHub MCP server
   - Tool listing capability
   - Actual tool execution (non-destructive test)

**Example output:**
```
======================================================================
                GitHub MCP Integration Diagnostic Tool
======================================================================

======================================================================
                        1. Prerequisites Check
======================================================================

🧪 Testing: Python version
✅ Python 3.11.14 (compatible)
🧪 Testing: Docker installation
✅ Docker installed: Docker version 24.0.6, build ed223bc
🧪 Testing: Docker daemon status
✅ Docker daemon is running
🧪 Testing: Python packages
✅ mcp: installed (Model Context Protocol client)
✅ anthropic: installed (Anthropic API client)
✅ dotenv: installed (Environment variable loader)
🧪 Testing: GitHub Personal Access Token
✅ Token found: ghp_1234...5678
ℹ️  Token length: 40 characters

======================================================================
                     2. Docker Functionality Tests
======================================================================

🧪 Testing: Docker container execution
✅ Docker can run containers successfully
🧪 Testing: GitHub MCP Docker image
✅ Image available locally: ghcr.io/github/github-mcp-server:latest

======================================================================
                       3. MCP Integration Tests
======================================================================

🧪 Testing: MCP client connection
ℹ️  Initializing MCP client...
✅ Successfully connected to GitHub MCP server
ℹ️  Fetching available tools...
✅ Found 15 available tools:
   • create_pull_request
   • create_issue
   • get_repository
   ... and 5 more
🧪 Testing: MCP tool execution
ℹ️  Testing get_repository for github/docs...
✅ Successfully called MCP tool
   • Repository: github/docs
   • Description: The open-source repo for docs.github.com...
   • Stars: 15234

======================================================================
                         Test Results Summary
======================================================================

Python Version: PASS
Docker Installed: PASS
Docker Running: PASS
Python Packages: PASS
Github Token: PASS
Docker Run: PASS
Docker Image: PASS
Mcp Connection: PASS
Mcp Tool Call: PASS

Overall: 9/9 tests passed

======================================================================
                          ✅ All Tests Passed!
======================================================================

✅ GitHub MCP integration is working correctly!
```

---

### 3. Basic Test (`test_github_mcp.py`)

**Purpose:** Original simple test script

**Use when:**
- You prefer the original testing approach
- You want minimal output

**Usage:**
```bash
python test_github_mcp.py
```

---

## 🔧 Troubleshooting Guide

### Issue: "Docker not installed or not in PATH"

**Solution:**
```bash
# Check if Docker is installed
docker --version

# If not installed, visit: https://docs.docker.com/get-docker/
```

### Issue: "Docker daemon is not running"

**Solution:**
```bash
# Linux (systemd)
sudo systemctl start docker

# macOS/Windows
# Start Docker Desktop application
```

### Issue: "GITHUB_PERSONAL_ACCESS_TOKEN not set"

**Solution:**
```bash
# Set the token
export GITHUB_PERSONAL_ACCESS_TOKEN='your_token_here'

# To make it permanent, add to ~/.bashrc or ~/.zshrc
echo 'export GITHUB_PERSONAL_ACCESS_TOKEN="your_token"' >> ~/.bashrc
source ~/.bashrc
```

**Creating a token:**
1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `repo`, `workflow`
4. Generate and copy the token

### Issue: "Python packages not installed"

**Solution:**
```bash
pip install -r requirements.txt
```

### Issue: "Failed to pull Docker image"

**Solution:**
```bash
# Manually pull the image
docker pull ghcr.io/github/github-mcp-server

# Check if it's available
docker images | grep github-mcp-server
```

### Issue: "MCP connection failed"

**Common causes:**
- Docker not running → Start Docker
- Invalid token → Check token permissions (needs `repo`, `workflow`)
- Network issues → Check internet connection
- Firewall blocking Docker → Configure firewall

**Debug steps:**
```bash
# 1. Check Docker logs
docker ps -a | grep github-mcp-server

# 2. Try manual Docker run
docker run -i --rm \
  -e GITHUB_PERSONAL_ACCESS_TOKEN='your_token' \
  ghcr.io/github/github-mcp-server

# 3. Verify token works with GitHub API
curl -H "Authorization: token your_token" https://api.github.com/user
```

### Issue: "Connection lost" or "Async errors"

**Potential causes:**
- Token expired or revoked
- Token permissions insufficient
- Server timeout

**Solution:**
1. Regenerate GitHub token
2. Ensure token has correct scopes (`repo`, `workflow`)
3. Check token hasn't been revoked

---

## 🎯 Quick Decision Tree

```
Need to test GitHub MCP?
│
├─ First time setup or major issues?
│  └─ Use: diagnose_github_mcp.py
│     (Comprehensive diagnostics)
│
├─ Quick verification after setup?
│  └─ Use: quick_test_mcp.py
│     (Fast connection check)
│
└─ Prefer simple/original test?
   └─ Use: test_github_mcp.py
      (Basic test)
```

---

## 📦 Requirements

All test scripts require:

```txt
mcp>=1.0.0
anthropic>=0.18.0
python-dotenv>=1.0.0
```

Install with:
```bash
pip install -r requirements.txt
```

---

## 🔍 Understanding Test Results

### ✅ All tests passed
GitHub MCP is fully functional. You can use it in your application.

### ⚠️ Some tests failed (Prerequisites)
You need to install missing components (Docker, Python packages, token).

### ❌ Tests failed (MCP Connection)
Even though prerequisites are met, MCP can't connect. This usually means:
- Docker daemon issues
- Network connectivity problems
- Token permission issues

---

## 🆘 Getting Help

If tests continue to fail:

1. **Review the detailed error output** from `diagnose_github_mcp.py`
2. **Check the main documentation:** `GITHUB_MCP_SETUP.md`
3. **Verify prerequisites:**
   - Docker installed and running
   - Python 3.8+ installed
   - All packages from `requirements.txt` installed
   - Valid GitHub token with correct permissions
4. **Open an issue:**
   - Include output from `diagnose_github_mcp.py`
   - Include your OS and Docker version
   - Describe what you've already tried

---

## 📚 Additional Resources

- [GitHub MCP Setup Guide](./GITHUB_MCP_SETUP.md) - Complete setup instructions
- [GitHub MCP Server](https://github.com/github/github-mcp-server) - Official server repo
- [Model Context Protocol](https://modelcontextprotocol.io/) - MCP specification
- [Docker Documentation](https://docs.docker.com/) - Docker setup and troubleshooting

---

## 🔐 Security Notes

- **Never commit your GitHub token** to version control
- Use environment variables for token storage
- Rotate tokens regularly
- Use tokens with minimal required scopes
- Consider using GitHub Apps for production systems

---

## 📝 License

These testing tools are part of the AiAgentToolCalling project and follow the same license.
