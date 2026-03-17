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

import json
import os
import subprocess
import sys
from typing import Optional

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool

# Import sub-agents and tools
from src.agents.analyzer import create_dependency_analyzer_agent
from src.config import DEFAULT_LLM_MODEL
from src.agents.updater import create_smart_updater_agent
from src.callbacks.agent_activity import AgentActivityHandler

# Load environment variables
load_dotenv()

# Module-level reference to the current orchestrator handler so child tools
# can register their sub-agent handlers for aggregated cost tracking.
_current_orchestrator_handler: Optional[AgentActivityHandler] = None


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
        print(f"\nStep 1: Analyzing repository for outdated dependencies...")

        analyzer_agent = create_dependency_analyzer_agent()
        handler = AgentActivityHandler("analyzer")

        if _current_orchestrator_handler:
            _current_orchestrator_handler.add_child_handler(handler)

        result = analyzer_agent.invoke(
            {
                "messages": [
                    (
                        "user",
                        f"Analyze this repository for outdated dependencies and return a structured JSON report: {repo_url}",
                    )
                ]
            },
            config={"callbacks": [handler]},
        )

        final_message = result["messages"][-1]

        return json.dumps(
            {
                "status": "success",
                "repo_url": repo_url,
                "analysis": final_message.content,
            }
        )

    except Exception as e:
        return json.dumps(
            {"status": "error", "message": f"Error analyzing repository: {str(e)}"}
        )


@tool
def smart_update_and_test(
    repo_path: str, outdated_packages: str, package_manager: str
) -> str:
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
        print(f"\nStep 2: Applying updates and testing...")

        updater_agent = create_smart_updater_agent()
        handler = AgentActivityHandler("updater")

        if _current_orchestrator_handler:
            _current_orchestrator_handler.add_child_handler(handler)

        result = updater_agent.invoke(
            {
                "messages": [
                    (
                        "user",
                        f"""Update and test dependencies for repository at {repo_path}.

Outdated packages: {outdated_packages}
Package manager: {package_manager}

Workflow:
1. Apply ALL updates (including major versions)
2. Run build/test commands
3. If tests fail: identify problematic package and rollback its major update
4. Retry up to 3 times
5. If successful: create GitHub PR with changes
6. If still failing: create GitHub Issue with details

Return the final PR URL or Issue URL.""",
                    )
                ]
            },
            config={"callbacks": [handler], "recursion_limit": 50},
        )

        final_message = result["messages"][-1]

        # Extract only essential fields to avoid sending huge payloads to orchestrator LLM
        try:
            parsed = json.loads(final_message.content)
            compact = {
                "status": parsed.get("status", "success"),
                "url": parsed.get("url", ""),
                "message": parsed.get("message", ""),
            }
            return json.dumps(compact)
        except (json.JSONDecodeError, TypeError):
            # If not JSON, truncate to avoid bloating the orchestrator context
            content = final_message.content
            if len(content) > 500:
                content = content[:500]
            return json.dumps({"status": "success", "result": content})

    except Exception as e:
        return json.dumps(
            {"status": "error", "message": f"Error in smart update: {str(e)}"}
        )


def validate_prerequisites() -> tuple[bool, str]:
    """
    Validate that all prerequisites are met for running the dependency updater.

    Returns:
        tuple: (is_valid: bool, message: str)
    """
    # Check for Docker
    try:
        docker_check = subprocess.run(
            ["docker", "--version"], capture_output=True, text=True, timeout=10
        )
        if docker_check.returncode != 0:
            return (
                False,
                "Docker is not available. Please install Docker from https://docs.docker.com/get-docker/",
            )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return (
            False,
            "Docker is not available. Please install Docker from https://docs.docker.com/get-docker/",
        )

    # Check for GitHub Personal Access Token
    github_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not github_token:
        return False, (
            "GITHUB_PERSONAL_ACCESS_TOKEN not set. "
            "Please set your GitHub token: export GITHUB_PERSONAL_ACCESS_TOKEN='your_token_here'. "
            "Create a token at: https://github.com/settings/tokens (Required scopes: repo, workflow)"
        )

    # Check for Anthropic API key
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        return False, (
            "ANTHROPIC_API_KEY not set. "
            "Please set your Anthropic API key: export ANTHROPIC_API_KEY='your_key_here'"
        )

    return True, "All prerequisites validated successfully"


def create_main_orchestrator():
    """
    Create the main orchestrator agent that coordinates the entire workflow.
    """
    tools = [analyze_repository, smart_update_and_test]

    system_message = """You are the orchestrator for automated dependency updates. Follow this EXACT workflow:

STEP 1: Call analyze_repository with the repository URL.
- Extract from the result: repo_path, package_manager, and the outdated_packages list.
- If no outdated dependencies, inform the user and stop.

STEP 2: Call smart_update_and_test with repo_path, package_manager, and outdated_packages from step 1.
- This tool handles: updating deps, building, testing, creating PR or Issue.

STEP 3: Return the result as a JSON object. Extract the URL from smart_update_and_test's result.
- Your final response MUST be ONLY this JSON and nothing else:
  {"status": "pr_created", "url": "<PR_URL>"} or
  {"status": "issue_created", "url": "<ISSUE_URL>"} or
  {"status": "up_to_date", "message": "..."} or
  {"status": "error", "message": "..."}

IMPORTANT RULES:
- Do NOT call any other tools. Only use analyze_repository and smart_update_and_test.
- Pass the repo_path from analyze_repository directly to smart_update_and_test.
- Keep ALL your text responses under 50 words. No analysis, no reports, no summaries of intermediate results.
- When calling smart_update_and_test, pass the outdated_packages as a compact JSON string — do NOT reformat or annotate them."""

    llm = ChatAnthropic(model=os.getenv("LLM_MODEL_NAME", DEFAULT_LLM_MODEL), temperature=0)

    agent_executor = create_agent(llm, tools, system_prompt=system_message)

    return agent_executor


def main():
    """
    Main entry point for the automated dependency update system.
    """
    if len(sys.argv) < 2:
        print("""
Auto Update Dependencies Tool

Intelligently updates dependencies with automated testing and rollback.

Usage: python -m src.agents.orchestrator <repository>

Examples:
  python -m src.agents.orchestrator https://github.com/owner/repo
  python -m src.agents.orchestrator owner/repo

What it does:
  1. Analyzes your repo for outdated dependencies
  2. Updates ALL dependencies to latest (including major versions)
  3. Tests the changes (build, test, lint)
  4. Rolls back breaking updates if tests fail
  5. Creates PR if successful
  6. Creates Issue if updates can't be applied safely

Prerequisites:
  - Docker installed and running
  - GITHUB_PERSONAL_ACCESS_TOKEN environment variable set
  - ANTHROPIC_API_KEY environment variable set
  - Git configured with push access to the repository
""")
        sys.exit(1)

    repo_input = sys.argv[1]

    # Convert owner/repo to full URL if needed
    if not repo_input.startswith("http"):
        repo_url = f"https://github.com/{repo_input}"
        repo_name = repo_input
    else:
        repo_url = repo_input
        parts = repo_url.rstrip("/").split("/")
        repo_name = f"{parts[-2]}/{parts[-1]}"

    print("=" * 80)
    print("  Automated Dependency Update System")
    print("=" * 80)
    print()
    print(f"Repository: {repo_name}")
    print(f"URL: {repo_url}")
    print()
    print("Starting automated update process...")
    print()

    # Check prerequisites
    print("Checking prerequisites...")
    is_valid, message = validate_prerequisites()

    if not is_valid:
        print(f"\n{message}\n")
        sys.exit(1)

    print("All prerequisites validated")
    print()

    # Create and run orchestrator
    global _current_orchestrator_handler
    orchestrator = create_main_orchestrator()
    handler = AgentActivityHandler("orchestrator")
    _current_orchestrator_handler = handler

    try:
        result = orchestrator.invoke(
            {
                "messages": [
                    (
                        "user",
                        f"Automatically update dependencies for repository: {repo_url}",
                    )
                ]
            },
            config={"callbacks": [handler]},
        )

        print("\n" + "=" * 80)
        print("  FINAL RESULT")
        print("=" * 80)
        print()

        final_message = result["messages"][-1]
        try:
            result_json = json.loads(final_message.content)
            status = result_json.get("status", "unknown")
            if status == "pr_created":
                print(f"  PR Created: {result_json.get('url', 'N/A')}")
            elif status == "issue_created":
                print(f"  Issue Created: {result_json.get('url', 'N/A')}")
            elif status == "issue_failed":
                print(f"  Could not create issue: {result_json.get('message', '')}")
                if result_json.get("details"):
                    print(f"\n  Issue details:\n{result_json['details']}")
            elif status == "up_to_date":
                print(
                    f"  {result_json.get('message', 'All dependencies are up to date.')}"
                )
            else:
                print(f"  Status: {status}")
                if result_json.get("message"):
                    print(f"  {result_json['message']}")
        except (json.JSONDecodeError, TypeError):
            print(final_message.content)
        print()

        # Print cost summary
        usage = handler.get_usage_summary()
        print("=" * 80)
        print("  USAGE & COST")
        print("=" * 80)
        print(
            f"  Total tokens: {usage['total_tokens']:,} ({usage['input_tokens']:,} in, {usage['output_tokens']:,} out)"
        )
        print(f"  LLM calls:    {usage['llm_calls']}")
        print(f"  Est. cost:    ${usage['estimated_cost_usd']:.4f}")
        if usage.get("children"):
            for child in usage["children"]:
                print(
                    f"    - {child['agent']}: {child['total_tokens']:,} tokens, ${child['estimated_cost_usd']:.4f}"
                )
        print()

    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
