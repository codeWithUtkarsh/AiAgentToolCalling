# Container Runtime Support

The GitHub MCP integration now supports **multiple container runtimes**, making it work with various Docker alternatives.

## ✅ Supported Container Runtimes

| Runtime | Platforms | Description |
|---------|-----------|-------------|
| **Docker Desktop** | macOS, Windows, Linux | Official Docker application |
| **OrbStack** | macOS | Fast, lightweight Docker alternative for Mac |
| **Podman Desktop** | macOS, Windows, Linux | Daemonless container engine |
| **Rancher Desktop** | macOS, Windows, Linux | Kubernetes + container management |
| **Podman** | Linux, macOS | Rootless container runtime |
| **nerdctl** | Linux | Docker-compatible CLI for containerd |

## 🚀 How It Works

The GitHub MCP client **automatically detects** which container runtime is available on your system:

```python
from github_mcp_client import GitHubMCPClient

# Auto-detects: docker, podman, or nerdctl
async with GitHubMCPClient() as client:
    tools = await client.list_available_tools()
```

### Detection Order

1. Checks for `docker` command (works with Docker Desktop, OrbStack, Rancher Desktop)
2. Checks for `podman` command
3. Checks for `nerdctl` command

### Manual Override

You can specify a specific runtime:

```python
async with GitHubMCPClient(container_runtime="podman") as client:
    # Forces use of podman
    pass
```

## 🎯 OrbStack Users (macOS)

**OrbStack is fully supported!** It provides the `docker` command and works seamlessly.

### Verification

```bash
# OrbStack provides the docker command
docker --version
# Output: Docker version X.Y.Z

# Test GitHub MCP
python quick_test_mcp.py
```

### Why OrbStack?

OrbStack is a **lightweight alternative** to Docker Desktop for macOS:
- ✅ Faster startup
- ✅ Lower resource usage
- ✅ Native Mac integration
- ✅ 100% Docker-compatible

The GitHub MCP client works identically with OrbStack as it does with Docker Desktop.

## 📦 Installation Guides

### OrbStack (macOS)

```bash
# Install OrbStack
brew install orbstack

# Or download from: https://orbstack.dev/

# Verify
docker --version
```

### Docker Desktop

**macOS/Windows:**
- Download from: https://www.docker.com/products/docker-desktop

**Linux:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

### Podman Desktop

```bash
# macOS
brew install podman-desktop

# Or download from: https://podman-desktop.io/
```

### Rancher Desktop

Download from: https://rancherdesktop.io/

## 🧪 Testing Your Setup

### Quick Test

```bash
# Set your GitHub token
export GITHUB_PERSONAL_ACCESS_TOKEN='your_token'

# Run quick test (auto-detects runtime)
python quick_test_mcp.py
```

### Comprehensive Diagnostics

```bash
python diagnose_github_mcp.py
```

**Expected output:**
```
🧪 Testing: Container runtime
✅ docker installed: Docker version 28.3.3
ℹ️  Runtime type: Docker Desktop / OrbStack / Rancher Desktop

🧪 Testing: Docker runtime status
✅ Docker runtime is working
```

## 🔍 What Runtime Am I Using?

The diagnostic script shows which runtime was detected:

```python
from github_mcp_client import _detect_container_runtime

runtime = _detect_container_runtime()
print(f"Using: {runtime}")  # Output: docker, podman, or nerdctl
```

## 🐳 Container Runtime Comparison

### For macOS Users

| Feature | Docker Desktop | OrbStack | Podman Desktop |
|---------|----------------|----------|----------------|
| Speed | Good | Excellent | Good |
| Resource Usage | High | Low | Medium |
| Docker Compatibility | 100% | 100% | 95% |
| Kubernetes | Yes | No | Optional |
| Free for Commercial | Limited | Yes | Yes |
| Native Mac Integration | Good | Excellent | Good |

**Recommendation for Mac:** OrbStack or Docker Desktop

### For Linux Users

| Feature | Docker | Podman | nerdctl |
|---------|--------|--------|---------|
| Rootless | No | Yes | Yes |
| Daemonless | No | Yes | Depends |
| Docker Compatibility | 100% | 95% | 95% |
| Systemd Integration | Good | Excellent | Good |

**Recommendation for Linux:** Docker or Podman

### For Windows Users

| Feature | Docker Desktop | Podman Desktop | Rancher Desktop |
|---------|----------------|----------------|-----------------|
| WSL2 Integration | Excellent | Good | Good |
| Kubernetes | Yes | Optional | Yes |
| Free | Limited | Yes | Yes |

**Recommendation for Windows:** Docker Desktop or Rancher Desktop

## 🛠️ Troubleshooting

### OrbStack: "docker: command not found"

**Issue:** OrbStack is installed but `docker` command not found

**Solution:**
```bash
# Ensure OrbStack is running
# Open OrbStack application

# Check if docker command is available
which docker

# If not, add to PATH (OrbStack should do this automatically)
# Restart terminal
```

### Podman: "Cannot connect to Podman socket"

**Issue:** Podman installed but not running

**Solution:**
```bash
# Start Podman machine (macOS/Windows)
podman machine start

# Or start Podman socket (Linux)
systemctl --user start podman.socket
```

### "No container runtime found"

**Issue:** No supported runtime detected

**Solution:**
Install one of the supported runtimes:
- macOS: Install OrbStack or Docker Desktop
- Linux: Install Docker or Podman
- Windows: Install Docker Desktop or Podman Desktop

```bash
# Verify installation
docker --version
# or
podman --version
```

## 💡 Advanced Usage

### Using Specific Runtime

```python
# Force use of Podman
async with GitHubMCPClient(container_runtime="podman") as client:
    result = await client.create_pull_request(...)

# Force use of nerdctl
async with GitHubMCPClient(container_runtime="nerdctl") as client:
    result = await client.create_issue(...)
```

### Custom Container Runtime

If you have a Docker-compatible runtime not listed:

```python
async with GitHubMCPClient(container_runtime="your-runtime") as client:
    # Must support: your-runtime run -i --rm -e ENV=value IMAGE args
    pass
```

## 📊 Performance Comparison

Startup time for GitHub MCP server (approximate):

| Runtime | Startup Time | Resource Usage |
|---------|--------------|----------------|
| OrbStack | ~2 seconds | Low |
| Docker Desktop | ~3-5 seconds | Medium-High |
| Podman | ~3 seconds | Low-Medium |
| Rancher Desktop | ~4-6 seconds | Medium |

*Times vary based on system configuration*

## ✅ Verification Checklist

- [ ] Container runtime installed (Docker, OrbStack, Podman, etc.)
- [ ] Runtime is running (check with `docker ps` or `podman ps`)
- [ ] GitHub token set (`GITHUB_PERSONAL_ACCESS_TOKEN`)
- [ ] Python dependencies installed (`pip install -r requirements.txt`)
- [ ] Quick test passes (`python quick_test_mcp.py`)

## 🔗 Resources

- **OrbStack:** https://orbstack.dev/
- **Docker Desktop:** https://www.docker.com/products/docker-desktop
- **Podman Desktop:** https://podman-desktop.io/
- **Rancher Desktop:** https://rancherdesktop.io/
- **containerd + nerdctl:** https://github.com/containerd/nerdctl

## 🎉 Summary

The GitHub MCP integration is **container runtime agnostic**:

- ✅ Works with Docker Desktop
- ✅ Works with OrbStack (macOS Docker alternative)
- ✅ Works with Podman Desktop
- ✅ Works with Rancher Desktop
- ✅ Auto-detects available runtime
- ✅ Manual runtime selection supported
- ✅ Same API regardless of runtime

**No code changes needed** - just install your preferred container runtime and it works!
