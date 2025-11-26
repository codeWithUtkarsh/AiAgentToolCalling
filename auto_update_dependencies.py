#!/usr/bin/env python3
"""
Auto Update Dependencies - Main Entry Point

Complete workflow:
1. Analyze repository for outdated dependencies
2. Apply all updates (including major versions)
3. Test the changes
4. Roll back breaking updates if needed
5. Create PR (success) or Issue (failure)
"""

import os
import sys
import json
from typing import Dict, List, Optional
from dotenv import load_dotenv

from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic
from langchain.agents import create_agent

# Import sub-agents and tools
from dependency_analyzer import create_dependency_analyzer_agent
from smart_dependency_updater import create_smart_updater_agent
from dependency_operations import categorize_updates
from setup_github_mcp import ensure_github_mcp_server

# Load environment variables
load_dotenv()


@tool
def analyze_repository(repo_url: str) -> str:
    """
    Analyze a repository to find outdated dependencies.

    Args:
        repo_url: URL of the repository to analyze

    Returns:
        JSON with analysis results including outdated packages
    """
    try:
        print(f"\n📊 Step 1: Analyzing repository for outdated dependencies...")

        analyzer_agent = create_dependency_analyzer_agent()

        result = analyzer_agent.invoke({
            "messages": [("user", f"Analyze this repository for outdated dependencies and return a structured JSON report: {repo_url}")]
        })

        final_message = result["messages"][-1]

        return json.dumps({
            "status": "success",
            "repo_url": repo_url,
            "analysis": final_message.content
        })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error analyzing repository: {str(e)}"
        })


@tool
def smart_update_and_test(repo_path: str, outdated_packages: str, package_manager: str) -> str:
    """
    Apply updates, test them, roll back if needed, and create PR or Issue.

    Args:
        repo_path: Path to the cloned repository
        outdated_packages: JSON string with outdated packages
        package_manager: Package manager type (npm, pip, cargo, etc.)

    Returns:
        JSON with final result (PR URL or Issue URL)
    """
    try:
        print(f"\n🧠 Step 2: Applying updates and testing...")

        updater_agent = create_smart_updater_agent()

        result = updater_agent.invoke({
            "messages": [("user", f"""Update and test dependencies for repository at {repo_path}.

Outdated packages: {outdated_packages}
Package manager: {package_manager}

Workflow:
1. Apply ALL updates (including major versions)
2. Run build/test commands
3. If tests fail: identify problematic package and rollback its major update
4. Retry up to 3 times
5. If successful: create GitHub PR with changes
6. If still failing: create GitHub Issue with details

Return the final PR URL or Issue URL.""")]
        })

        final_message = result["messages"][-1]

        return json.dumps({
            "status": "success",
            "result": final_message.content
        })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error in smart update: {str(e)}"
        })


def create_main_orchestrator():
    """
    Create the main orchestrator agent that coordinates the entire workflow.
    """
    tools = [
        analyze_repository,
        smart_update_and_test,
        categorize_updates
    ]

    system_message = """You are the main orchestrator for automated dependency updates with intelligent testing.

Your complete workflow:

STEP 1: ANALYZE REPOSITORY
- Use the analyze_repository tool to clone and analyze the repo
- Extract: package manager, outdated packages list, dependency files
- Categorize updates: major, minor, patch

STEP 2: SMART UPDATE & TEST
- Use smart_update_and_test tool with the repo path and outdated packages
- This tool will:
  a) Apply all updates to dependency files
  b) Run build/test commands
  c) If tests fail: identify and rollback breaking packages
  d) Create PR if successful, or Issue if it can't be fixed
  e) Return PR URL or Issue URL

STEP 3: REPORT TO USER
- Summarize what was done
- Provide PR URL (success) or Issue URL (failure)
- List what was updated
- Explain any rollbacks that occurred

Key Points:
- Always try the most aggressive updates first
- Use testing to validate changes
- Be smart about rollbacks (only major versions)
- Create PR for successes, Issue for failures
- Provide clear, actionable reports

Example Success Report:
"✅ Successfully updated 15 dependencies!
- Applied 12 updates successfully
- Rolled back React 17→18 (breaking changes)
- Kept React at latest 17.x (17.0.2)
- All tests passing
- PR created: https://github.com/owner/repo/pull/123"

Example Failure Report:
"❌ Could not apply updates safely
- Attempted updates to 8 packages
- Multiple breaking changes detected
- Rollbacks did not resolve issues
- Issue created for manual review: https://github.com/owner/repo/issues/45"

Error Handling:
- If repository doesn't exist or is private: inform user
- If no outdated dependencies: congratulate user
- If GitHub MCP server not installed: provide installation instructions
- If GITHUB_PERSONAL_ACCESS_TOKEN not set: provide setup instructions
- If git push fails: explain authentication needed"""

    llm = ChatAnthropic(
        model="claude-sonnet-4-5-20250929",
        temperature=0
    )

    agent_executor = create_agent(llm, tools, system_prompt=system_message)

    return agent_executor


def main():
    """
    Main entry point for the automated dependency update system.
    """
    if len(sys.argv) < 2:
        print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                   Auto Update Dependencies Tool                           ║
║                                                                            ║
║  Intelligently updates dependencies with automated testing and rollback   ║
╚════════════════════════════════════════════════════════════════════════════╝

Usage: python auto_update_dependencies.py <repository>

Examples:
  python auto_update_dependencies.py https://github.com/owner/repo
  python auto_update_dependencies.py owner/repo

What it does:
  1. 📊 Analyzes your repo for outdated dependencies
  2. 🔄 Updates ALL dependencies to latest (including major versions)
  3. 🧪 Tests the changes (build, test, lint)
  4. 🔙 Rolls back breaking updates if tests fail
  5. ✅ Creates PR if successful
  6. 🔴 Creates Issue if updates can't be applied safely

Prerequisites:
  - Go installed (for automatic GitHub MCP server setup)
  - GITHUB_PERSONAL_ACCESS_TOKEN environment variable set
  - Git configured with push access to the repository
  - Package manager tools installed (npm, pip, cargo, etc.)

Note: GitHub MCP server will be automatically installed if not found!

Setup GitHub Access:
  1. Create token at: https://github.com/settings/tokens
     Required scopes: repo, workflow
  2. Set environment variable:
     export GITHUB_PERSONAL_ACCESS_TOKEN='your_token_here'
""")
        sys.exit(1)

    repo_input = sys.argv[1]

    # Convert owner/repo to full URL if needed
    if not repo_input.startswith("http"):
        repo_url = f"https://github.com/{repo_input}"
        repo_name = repo_input
    else:
        repo_url = repo_input
        parts = repo_url.rstrip('/').split('/')
        repo_name = f"{parts[-2]}/{parts[-1]}"

    print("╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "  🤖 Automated Dependency Update System".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")
    print()
    print(f"📦 Repository: {repo_name}")
    print(f"🔗 URL: {repo_url}")
    print()
    print("Starting automated update process...")
    print()

    # Check prerequisites
    print("🔍 Checking prerequisites...")

    # Check for GitHub MCP server binary (auto-install if missing)
    print("  📦 Checking GitHub MCP server...")
    if not ensure_github_mcp_server():
        print()
        print("  ❌ Failed to set up GitHub MCP server")
        print("     Manual install: https://github.com/github/github-mcp-server")
        sys.exit(1)
    print("  ✅ GitHub MCP server ready")

    # Check for GitHub Personal Access Token
    github_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if github_token:
        print("  ✅ GITHUB_PERSONAL_ACCESS_TOKEN found")
    else:
        print("  ❌ GITHUB_PERSONAL_ACCESS_TOKEN not set")
        print("     Set your GitHub token:")
        print("     export GITHUB_PERSONAL_ACCESS_TOKEN='your_token_here'")
        print()
        print("     Create a token at: https://github.com/settings/tokens")
        print("     Required scopes: repo, workflow")
        sys.exit(1)

    print()

    # Create and run orchestrator
    orchestrator = create_main_orchestrator()

    try:
        result = orchestrator.invoke({
            "messages": [("user", f"Automatically update dependencies for repository: {repo_url}")]
        })

        print("\n" + "╔" + "="*78 + "╗")
        print("║" + "  FINAL RESULT".center(78) + "║")
        print("╚" + "="*78 + "╝")
        print()

        final_message = result["messages"][-1]
        print(final_message.content)
        print()

    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
