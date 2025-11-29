# AI Agent Tool Calling - Automated Dependency Update System

A multi-agent Python system that uses LangChain's tool calling pattern to **automatically update dependencies with intelligent testing and rollback capabilities**. It analyzes repositories, updates dependencies, tests the changes, rolls back breaking updates, and creates Pull Requests or Issues automatically.

## 🌟 Features

### Core Capabilities
- **🤖 Fully Automated Updates**: End-to-end automation from analysis to PR creation
- **🧪 Intelligent Testing**: Automatically runs build/test commands to verify updates
- **🔙 Smart Rollback**: Identifies breaking changes and rolls back only problematic major updates
- **✅ Auto PR Creation**: Creates GitHub Pull Requests with successful updates
- **🔴 Auto Issue Creation**: Creates GitHub Issues when updates can't be applied safely
- **📊 Multi-Agent Architecture**: Orchestrator pattern with specialized sub-agents
- **🧠 AI-Powered Analysis**: Uses Claude to analyze errors and identify problematic dependencies

### Language Support
Detects and updates dependencies for:
- **JavaScript/Node.js** (npm, yarn, pnpm)
- **Python** (pip, pipenv, poetry)
- **Rust** (cargo)
- **Ruby** (bundler)
- **Java** (Maven, Gradle)
- **PHP** (Composer)
- **Go** (go modules)

### Smart Features
- **Automatic Build Detection**: Detects how to build, test, and verify your project
- **Error Analysis**: AI-powered parsing of error messages to identify culprits
- **Iterative Rollback**: Tries to salvage as many updates as possible
- **Version Categorization**: Categorizes updates as major/minor/patch
- **Comprehensive Reporting**: Detailed PR descriptions with what was updated and why

## 🏗️ Architecture

This project implements a multi-agent system following the [LangChain Tool Calling](https://blog.langchain.com/tool-calling-with-langchain/) pattern:

### Agent Hierarchy

```
auto_update_dependencies.py (Main Orchestrator)
├── dependency_analyzer.py (Analysis Agent)
│   └── Tools: clone, detect, check outdated
├── smart_dependency_updater.py (Smart Update Agent)
│   ├── Tools: detect build, test, write files, git ops
│   └── Sub-tools: apply updates, rollback, parse errors
└── dependency_operations.py (Helper Tools)
    └── Tools: categorize, version lookup, error analysis
```

### Complete Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  USER INPUT: Repository URL                                 │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: ANALYZE REPOSITORY                                 │
│  • Clone repository                                          │
│  • Detect package manager                                    │
│  • Find outdated dependencies                                │
│  • Categorize: major/minor/patch                             │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: APPLY ALL UPDATES                                  │
│  • Update ALL dependencies to latest                         │
│  • Including major version updates                           │
│  • Write updated dependency files                            │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: TEST UPDATES                                       │
│  • Run install command                                       │
│  • Run build command                                         │
│  • Run test command                                          │
│  • Capture all output                                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                ┌─────────┴─────────┐
                │                   │
         Tests Pass?         Tests Fail?
                │                   │
                ▼                   ▼
       ┌────────────────┐  ┌────────────────────────────┐
       │ CREATE PR      │  │ ANALYZE ERROR              │
       │                │  │ • Use AI to parse errors   │
       │ • Git branch   │  │ • Identify problematic pkg │
       │ • Commit       │  └───────────┬────────────────┘
       │ • Push         │              │
       │ • gh pr create │              ▼
       └────────┬───────┘  ┌────────────────────────────┐
                │          │ ROLLBACK MAJOR UPDATE      │
                │          │ • Find latest in major ver │
                │          │ • Update dependency file   │
                │          │ • Write file               │
                │          └───────────┬────────────────┘
                │                      │
                │                      ▼
                │          ┌────────────────────────────┐
                │          │ TEST AGAIN (Max 3x)        │
                │          └───┬──────────────────┬─────┘
                │              │                  │
                │         Now Pass?          Still Fail?
                │              │                  │
                │              └──────┐    ┌──────┘
                │                     │    │
                ▼                     ▼    ▼
       ┌────────────────┐  ┌──────────────────────────┐
       │ SUCCESS!       │  │ CREATE ISSUE             │
       │ PR Created     │  │ • Document what failed   │
       │                │  │ • Include error logs     │
       │ Output:        │  │ • Tag: dependencies      │
       │ • PR URL       │  │                          │
       │ • Summary      │  │ Output:                  │
       │ • Rollbacks    │  │ • Issue URL              │
       └────────────────┘  │ • Failure details        │
                           └──────────────────────────┘
```

### 1. **Auto Update Orchestrator** (Main Entry Point)

Main coordinator (`auto_update_dependencies.py`) that manages the complete workflow:
- Receives repository URL or name
- Checks prerequisites (Docker, GitHub token)
- Orchestrates analysis and update agents
- Manages end-to-end automated updates with PR/Issue creation

**Functions:**
- `analyze_repository()` - Invokes the analyzer agent
- `smart_update_and_test()` - Invokes the smart updater agent
- Docker and GitHub token validation

### 2. **Dependency Analyzer Agent** (Analysis)

Specialized in finding outdated dependencies (`dependency_analyzer.py`):
- Clones repositories
- Detects package managers
- Identifies outdated packages
- Returns structured analysis reports

**Tools:**
- `clone_repository` - Clones git repos to temp directories
- `detect_package_manager` - Identifies package managers and config files
- `read_dependency_file` - Reads dependency configuration files
- `check_npm_outdated` - Checks outdated npm packages
- `check_pip_outdated` - Checks outdated Python packages (via PyPI API)
- `cleanup_repository` - Removes temporary files

### 3. **Smart Dependency Updater Agent** (Update & Test)

Specialized in updating with intelligent testing and rollback (`smart_dependency_updater.py`):
- Applies dependency updates
- Runs build and test commands
- Automatically rolls back breaking changes
- Creates GitHub PRs on success
- Creates GitHub Issues on failure

**Tools:**
- `detect_build_command` - Auto-detects build/test commands
- `apply_updates` - Updates dependency files
- `test_updates` - Runs build/test commands
- `rollback_major_update` - Rolls back problematic updates
- `create_github_pr` - Creates PRs using MCP
- `create_github_issue` - Creates issues using MCP
- `parse_error_for_dependency` - AI-powered error analysis

### 4. **Dependency Operations** (Helper Module)

Utility functions for dependency manipulation (`dependency_operations.py`):
- Applies updates to various dependency file formats
- Rolls back specific package updates
- Categorizes updates (major/minor/patch)
- Finds latest versions within major releases

**Functions:**
- `apply_all_updates()` - Applies all updates to dependency files
- `rollback_major_update()` - Rolls back specific package versions
- `parse_error_for_dependency()` - AI analysis of build errors
- `categorize_updates()` - Categorizes updates by type
- `get_latest_version_for_major()` - Finds latest version in major release

## 📦 Installation

### Prerequisites

- Python 3.8 or higher
- Git
- Node.js and npm (for checking npm packages)
- pip (for checking Python packages)
- Other package managers as needed (cargo, go, etc.)

### Setup

1. Clone this repository:
```bash
git clone https://github.com/codeWithUtkarsh/AiAgentToolCalling.git
cd AiAgentToolCalling
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your Anthropic API key:
```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

Or create a `.env` file (copy from `.env.example`):
```bash
cp .env.example .env
# Edit .env and add your API key
```

### GitHub MCP Setup (Required for PR/Issue Creation)

The system uses GitHub MCP (Model Context Protocol) to create Pull Requests and Issues automatically.

#### Prerequisites

1. **Container Runtime** (Docker, OrbStack, Podman, etc.)
   - **macOS**: Install [OrbStack](https://orbstack.dev/) (recommended) or [Docker Desktop](https://www.docker.com/products/docker-desktop)
   - **Windows/Linux**: Install [Docker Desktop](https://www.docker.com/products/docker-desktop)

2. **GitHub Personal Access Token**
   - Create at: https://github.com/settings/tokens
   - Required scopes: `repo`, `workflow`

#### Setup Steps

**1. Install Container Runtime (if not already installed)**

macOS (choose one):
```bash
# Option 1: OrbStack (recommended - lightweight and fast)
brew install orbstack

# Option 2: Docker Desktop
# Download from https://www.docker.com/products/docker-desktop
```

**2. Fix PATH for macOS/OrbStack Users**

If you're on macOS and encounter "docker: command not found" errors in Python:

```bash
# Add to your shell configuration
echo 'export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

For bash users:
```bash
echo 'export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"' >> ~/.bash_profile
source ~/.bash_profile
```

**3. Set GitHub Token**

```bash
export GITHUB_PERSONAL_ACCESS_TOKEN='your_github_token_here'
```

To make it permanent:
```bash
# For zsh (macOS default)
echo 'export GITHUB_PERSONAL_ACCESS_TOKEN="your_token"' >> ~/.zshrc
source ~/.zshrc

# For bash
echo 'export GITHUB_PERSONAL_ACCESS_TOKEN="your_token"' >> ~/.bash_profile
source ~/.bash_profile
```

**4. Verify Setup**

Test your GitHub MCP setup:
```bash
python diagnose_github_mcp.py
```

Expected output:
```
✅ Container runtime: PASS
✅ GitHub token: PASS
✅ MCP connection: PASS
✅ MCP tool call: PASS
```

If any tests fail, the diagnostic tool will show specific instructions to fix the issue.

#### Supported Container Runtimes

The system automatically detects and works with:
- **Docker Desktop** - Official Docker
- **OrbStack** - Lightweight Docker alternative for macOS
- **Podman Desktop** - Daemonless container engine
- **Rancher Desktop** - Kubernetes + containers

No configuration needed - it auto-detects which one you have installed!

## 🚀 Usage

### Automated Update with Testing (New! Recommended)

The fully automated system that updates dependencies, tests them, and creates PRs:

```bash
python auto_update_dependencies.py <repository>
```

**Examples:**

```bash
# Using full URL
python auto_update_dependencies.py https://github.com/expressjs/express

# Using owner/repo format
python auto_update_dependencies.py expressjs/express
```

**What it does:**
1. 📊 Clones and analyzes your repository
2. 🔄 Updates **all** dependencies to latest (including major versions)
3. 🧪 Runs build and test commands
4. 🔙 If tests fail: identifies problematic packages and rolls back major updates
5. ✅ Creates a Pull Request if successful
6. 🔴 Creates an Issue if updates can't be applied safely

**Prerequisites:**
- Docker installed and running: `docker --version`
- GitHub Personal Access Token set: `export GITHUB_PERSONAL_ACCESS_TOKEN='your_token'`
- Git push access to the repository
- Package manager tools installed (npm, pip, cargo, etc.)

## 📊 Sample Workflows

### Workflow 1: Successful Update with Rollback

```
Repository: myapp (Node.js project)

📊 Analysis found 10 outdated packages:
  - express: 4.17.0 → 5.0.0 (MAJOR)
  - lodash: 4.17.20 → 4.17.21 (PATCH)
  - react: 17.0.0 → 18.2.0 (MAJOR)
  - axios: 0.21.0 → 1.6.0 (MAJOR)
  ... 6 more

🔄 Applying all updates...
✅ Updated package.json

🧪 Testing updates...
  ❌ npm test failed

🔍 Analyzing error...
  Identified: React 18 breaking change in test utilities

🔙 Rolling back React 18 → 17...
  Finding latest React 17.x: 17.0.2
  ✅ Rolled back to react@17.0.2

🧪 Testing again...
  ✅ npm install - success
  ✅ npm run build - success
  ✅ npm test - success

✅ Creating Pull Request...
  Branch: deps/auto-update-20250126
  PR: https://github.com/owner/myapp/pull/123

RESULT:
✅ Successfully updated 10 dependencies!
  - Applied 9 updates to latest versions
  - Rolled back React 18.2.0 → 17.0.2 (breaking changes)
  - All tests passing

📝 PR Summary:
  - express 4.17.0 → 5.0.0 ✅
  - lodash 4.17.20 → 4.17.21 ✅
  - react 17.0.0 → 17.0.2 (rolled back from 18.2.0)
  - axios 0.21.0 → 1.6.0 ✅
  - ... 6 more ✅
```

### Workflow 2: Failed Update (Issue Created)

```
Repository: legacy-app (Python project)

📊 Analysis found 5 outdated packages:
  - django: 2.2 → 4.2 (MAJOR)
  - requests: 2.25.0 → 2.31.0 (MINOR)
  ... 3 more

🔄 Applying all updates...
✅ Updated requirements.txt

🧪 Testing updates...
  ❌ pytest failed

🔍 Analyzing error...
  Identified: Django 4.x breaking changes in models

🔙 Rolling back Django 4.2 → 2.2...
  Finding latest Django 2.x: 2.2.28
  ✅ Rolled back to Django 2.2.28

🧪 Testing again...
  ❌ pytest still failing

🔍 Analyzing error...
  Identified: Compatibility issues with Python version

🔴 Cannot apply updates safely

📋 Creating Issue...
  Issue: https://github.com/owner/legacy-app/issues/45

RESULT:
❌ Updates could not be applied safely

Issue created with details:
  - Attempted updates to 5 packages
  - Django major update causes breaking changes
  - Python version compatibility issues detected
  - Manual review and migration needed
```

## 📊 Sample Output (Legacy Mode)

### Orchestrator Agent Output

```
================================================================================
🤖 Dependency Update Agent
================================================================================

📦 Repository: expressjs/express
🔗 URL: https://github.com/expressjs/express

📊 Running dependency analyzer on https://github.com/expressjs/express...

> Entering new AgentExecutor chain...
Cloning repository...
Repository cloned successfully

Detecting package managers...
Found: npm (package.json)

Checking outdated packages...
Found 8 outdated npm packages

================================================================================
✅ FINAL REPORT
================================================================================

# 🔄 Dependency Updates for expressjs/express

## 📦 Updated Dependencies

### ⚠️ Major Updates
- 🔴 **body-parser**: `1.19.0` → `2.0.0` (MAJOR - may have breaking changes)

### Minor Updates
- 🟡 **cookie**: `0.4.1` → `0.5.0` (minor)
- 🟡 **debug**: `2.6.9` → `2.7.0` (minor)

### Patch Updates
- 🟢 **accepts**: `1.3.7` → `1.3.8` (patch)
- 🟢 **etag**: `1.8.1` → `1.8.2` (patch)

## 🧪 Testing Instructions

Please run the following commands to verify the updates:

```bash
# Install dependencies
npm install

# Run tests
npm test

# Run build
npm run build

# Check for issues
npm run lint
```

## ⚠️ Important Notes

- ⚠️ This PR includes **MAJOR version updates**
- Review changelogs for breaking changes
- Run the full test suite before merging
- Check for deprecation warnings
- Verify build succeeds
- Review any peer dependency warnings

---

📊 Total dependencies updated: 8
🤖 This PR was generated by the Dependency Update Agent
```

## 🔄 Workflow

The orchestrator agent follows this workflow:

1. **Analyze Dependencies**
   - Clone the repository
   - Detect package managers
   - Identify outdated dependencies
   - Generate analysis report

2. **Update Dependency Files**
   - Read current dependency files
   - Update version numbers
   - Preserve file formatting
   - Determine testing strategy

3. **Create PR Description**
   - Categorize updates (major/minor/patch)
   - Add testing instructions
   - Include warnings for breaking changes
   - Provide checklist

4. **Report Results**
   - Summary of updates
   - PR description ready to use
   - Next steps for the user

## 🛠️ Extending the System

### Adding New Package Manager Support

1. **Update `dependency_analyzer.py`:**

Add detection in `detect_package_manager` tool:
```python
if os.path.exists(os.path.join(repo_path, "your-config-file")):
    package_managers["your-pm"] = {
        "files": ["your-config-file"],
        "lock_files": []
    }
```

Create a checking tool:
```python
@tool
def check_yourpm_outdated(repo_path: str) -> str:
    """Check for outdated packages in your package manager."""
    # Implementation here
    pass
```

2. **Update `dependency_operations.py`:**

Add update logic:
```python
def apply_yourpm_updates(file_path: str, updates: list) -> bool:
    """Update your package manager config file."""
    # Implementation here
    pass
```

3. **Update `smart_dependency_updater.py`:**

Add testing strategy in `detect_build_command` tool:
```python
# Add detection for your package manager
if package_manager == "your-pm":
    return {
        "install": "your-pm install",
        "build": "your-pm build",
        "test": "your-pm test"
    }
```

## 🔍 Agent Communication Flow

```
User Input (repo URL)
    ↓
Auto Update Orchestrator (auto_update_dependencies.py)
    ↓
    ├─ Check Prerequisites (Docker, GitHub Token)
    ↓
    ├─→ Dependency Analyzer Agent
    │   ├─→ clone_repository
    │   ├─→ detect_package_manager
    │   ├─→ check_npm_outdated / check_pip_outdated
    │   └─→ cleanup_repository
    │   ↓
    │   Returns: Analysis Report (outdated packages)
    ↓
    ├─→ Smart Dependency Updater Agent
    │   ├─→ detect_build_command (auto-detect test commands)
    │   ├─→ apply_updates (update dependency files)
    │   ├─→ test_updates (run build/test)
    │   ├─ If tests fail:
    │   │   ├─→ parse_error_for_dependency (AI error analysis)
    │   │   ├─→ rollback_major_update (rollback problematic package)
    │   │   └─→ test_updates (retry, max 3 attempts)
    │   ├─ If tests pass:
    │   │   └─→ create_github_pr (via Docker MCP)
    │   ├─ If tests still fail after rollbacks:
    │   │   └─→ create_github_issue (via Docker MCP)
    │   ↓
    │   Returns: PR URL or Issue URL
    ↓
Returns to User: Success (PR created) or Failure (Issue created)
```

## 🔧 Using Different LLM Providers

The system currently uses Anthropic's Claude, but you can switch to OpenAI:

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0)
```

Update all three agent files and set your OpenAI API key:
```bash
export OPENAI_API_KEY='your-api-key-here'
```

## 🗂️ Caching

The system includes smart caching to improve performance and reduce API calls:

### How Caching Works

- **Repository Caching**: Cloned repositories are cached locally to avoid re-cloning
- **Analysis Caching**: Dependency analysis results are cached
- **Outdated Package Caching**: Results from package registry checks are cached
- **TTL-Based Expiration**: Cache expires after a configurable time period

### Configuration

Set cache expiry time in hours via environment variable:

```bash
# Set in .env file or export
CACHE_EXPIRY_HOURS=24  # Default: 24 hours
```

### Cache Location

Cache is stored at: `~/.cache/ai-dependency-updater/`

### Cache Management

```bash
# View cache statistics
python repository_cache.py stats

# Clean up expired cache entries
python repository_cache.py cleanup

# Clear all cache
python repository_cache.py clear
```

### Cache Benefits

- ⚡ **Faster repeated analyses** - No need to re-clone repositories
- 💰 **Reduced API calls** - Cached package registry lookups
- 🌐 **Works offline** - Can analyze previously cached repositories
- 📊 **Smart invalidation** - Automatic expiration based on TTL

## ⚠️ Limitations

- Some package managers require additional tools (e.g., `cargo-outdated` for Rust)
- Large repositories may take time to clone and analyze (first time only, then cached)
- Some checks require the package manager to be installed locally
- Network connectivity required for cloning and checking updates (unless using cache)
- Requires container runtime (Docker/OrbStack/Podman) for GitHub MCP integration
- Automatically creates PRs on success and Issues when updates fail

## 📝 Example Scenarios

### Scenario 1: Update a Node.js Project

```bash
python auto_update_dependencies.py facebook/react
```

### Scenario 2: Update a Python Project

```bash
python auto_update_dependencies.py https://github.com/pallets/flask
```

### Scenario 3: Analyze and Update with Auto-Rollback

```bash
python dependency_analyzer.py https://github.com/rust-lang/cargo
```

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

- Add more package manager support
- Implement actual GitHub PR creation
- Add support for monorepos
- Improve version parsing and semver handling
- Add caching for faster repeated analyses
- Create a web interface

Please feel free to submit a Pull Request.

## 📄 License

MIT License - see LICENSE file for details

## 📚 References

- [LangChain Tool Calling Blog Post](https://blog.langchain.com/tool-calling-with-langchain/)
- [LangChain Documentation](https://python.langchain.com/)
- [LangChain Agents](https://python.langchain.com/docs/modules/agents/)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [Multi-Agent Systems](https://python.langchain.com/docs/use_cases/multi_agent/)

## 🆘 Troubleshooting

### "Module not found" errors

Make sure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### API Key errors

Ensure your Anthropic API key is set:
```bash
export ANTHROPIC_API_KEY='your-key-here'
```

### npm/pip not found

Install the required package managers:
- npm: Install Node.js from https://nodejs.org/
- pip: Included with Python 3

### Repository cloning fails

- Check your internet connection
- Ensure you have git installed
- Verify the repository URL is correct and public

---

**Built with ❤️ using LangChain and Claude**
