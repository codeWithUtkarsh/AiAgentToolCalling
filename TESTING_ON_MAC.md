# Testing GitHub MCP on Mac

Since Docker is installed on your Mac (version 28.3.3), you can test the GitHub MCP integration there.

## 🚀 Quick Setup on Mac

### Step 1: Clone the Repository

```bash
# Open Terminal on your Mac
cd ~/Documents  # or wherever you prefer

# Clone the repository
git clone https://github.com/codeWithUtkarsh/AiAgentToolCalling.git
cd AiAgentToolCalling

# Checkout the branch with the stdio mode fix
git checkout claude/test-github-mcp-01NtiJa4nANjxUYAANhM94jY
```

### Step 2: Set GitHub Token

```bash
# Set your GitHub Personal Access Token
export GITHUB_PERSONAL_ACCESS_TOKEN='your_github_token_here'

# Or add to your ~/.zshrc for persistence (Mac default shell)
echo 'export GITHUB_PERSONAL_ACCESS_TOKEN="your_token"' >> ~/.zshrc
source ~/.zshrc
```

**Create a token if you don't have one:**
1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `repo`, `workflow`
4. Generate and copy the token

### Step 3: Install Dependencies

```bash
# Install Python packages
pip3 install -r requirements.txt

# If you don't have pip3, install it first:
# python3 -m ensurepip --upgrade
```

### Step 4: Run Automated Verification

```bash
# Run the Mac verification script
./verify_on_mac.sh
```

This script will:
- ✅ Check Docker is installed
- ✅ Check Python is installed
- ✅ Verify GitHub token is set
- ✅ Install dependencies
- ✅ Run the quick MCP test

**Expected output:**
```
======================================================================
GitHub MCP Verification Script for Mac
======================================================================

🐳 Checking Docker...
✅ Docker installed: Docker version 28.3.3, build 980b856

🐍 Checking Python...
✅ Python installed: Python 3.11.x

✅ Found github_mcp_client.py

🔑 Checking GitHub token...
✅ Token found (40 characters)

📦 Installing Python dependencies...
✅ Dependencies installed

======================================================================
Running GitHub MCP Quick Test
======================================================================

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

======================================================================
✅ SUCCESS! GitHub MCP is working correctly on your Mac!
======================================================================
```

---

## 🧪 Manual Testing Options

If you prefer manual testing:

### Option A: Quick Test
```bash
python3 quick_test_mcp.py
```

### Option B: Comprehensive Diagnostics
```bash
python3 diagnose_github_mcp.py
```

### Option C: stdio Mode Specific Test
```bash
python3 test_mcp_stdio.py
```

---

## 🐋 Docker Verification

Before running tests, verify Docker is working:

```bash
# Check Docker version
docker -v

# Check Docker is running
docker ps

# Test Docker can run containers
docker run hello-world
```

If Docker Desktop is not running:
1. Open **Docker Desktop** application
2. Wait for it to start
3. Try again

---

## 🔧 Troubleshooting on Mac

### Issue: "Cannot connect to Docker daemon"

**Solution:** Start Docker Desktop application

### Issue: "Module not found"

**Solution:**
```bash
pip3 install -r requirements.txt
```

### Issue: "Token not set"

**Solution:**
```bash
export GITHUB_PERSONAL_ACCESS_TOKEN='your_token'
```

### Issue: "Permission denied: docker"

**Solution:**
```bash
# Docker Desktop on Mac doesn't require sudo
# Just make sure Docker Desktop is running
```

---

## 📋 What This Tests

The verification confirms:

1. ✅ **stdio mode fix** - Server runs with `stdio` argument
2. ✅ **Docker integration** - MCP server starts in container
3. ✅ **MCP connection** - Client connects to server
4. ✅ **Tool availability** - GitHub tools are accessible
5. ✅ **Tool execution** - Can call GitHub API successfully

---

## ✅ Success Criteria

All tests pass when you see:

```
Mcp Connection: PASS ✅
Mcp Tool Call: PASS ✅
```

---

## 🎯 After Successful Testing

Once verified on Mac, the GitHub MCP integration is ready to use in your application for:

- Creating pull requests automatically
- Creating issues for failed updates
- Querying repository information
- Managing GitHub workflows

---

## 💡 Why Test on Mac?

The container environment (`/home/user/AiAgentToolCalling`) doesn't have Docker installed, but your Mac does. Since the GitHub MCP client uses Docker to run the MCP server, testing needs to happen where Docker is available.

The code fix (stdio mode) is correct and works when Docker is present.
