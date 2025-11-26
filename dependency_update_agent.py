#!/usr/bin/env python3
"""
Dependency Update Agent (Orchestrator)

Main orchestrator agent that coordinates the dependency analysis and update process.
Uses sub-agents (dependency_analyzer and dependency_updater) to complete the workflow.
"""

import os
import sys
import json
import subprocess
from typing import Dict, List, Optional
from dotenv import load_dotenv

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic

# Load environment variables from .env file
load_dotenv()

# Import sub-agents
from dependency_analyzer import create_dependency_analyzer_agent
from dependency_updater import create_dependency_updater_agent


@tool
def run_dependency_analyzer(repo_url: str) -> str:
    """
    Run the dependency analyzer agent to check for outdated dependencies.

    Args:
        repo_url: URL of the repository to analyze (e.g., https://github.com/owner/repo)

    Returns:
        JSON string with analysis results
    """
    try:
        print(f"\n📊 Running dependency analyzer on {repo_url}...\n")

        analyzer_agent = create_dependency_analyzer_agent()

        result = analyzer_agent.invoke({
            "input": f"Analyze this repository for outdated dependencies: {repo_url}. Return results in a structured JSON format."
        })

        return json.dumps({
            "status": "success",
            "analysis": result["output"]
        })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error running analyzer: {str(e)}"
        })


@tool
def run_dependency_updater(package_manager: str, dependency_file: str, updates: str) -> str:
    """
    Run the dependency updater agent to create updated dependency files.

    Args:
        package_manager: The package manager (npm, pip, etc.)
        dependency_file: Path to the dependency file
        updates: JSON string with list of updates

    Returns:
        JSON string with updated files and testing strategy
    """
    try:
        print(f"\n🔧 Running dependency updater for {package_manager}...\n")

        updater_agent = create_dependency_updater_agent()

        result = updater_agent.invoke({
            "input": f"Update {dependency_file} for {package_manager} with these changes: {updates}. Provide updated file content and testing strategy."
        })

        return json.dumps({
            "status": "success",
            "updates": result["output"]
        })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error running updater: {str(e)}"
        })


@tool
def create_github_pr_description(repo_name: str, updates: str, testing_strategy: str) -> str:
    """
    Create a comprehensive GitHub PR description.

    Args:
        repo_name: Name of the repository (owner/repo)
        updates: JSON string with dependency updates
        testing_strategy: Testing commands and strategy

    Returns:
        Formatted PR description
    """
    try:
        updates_list = json.loads(updates) if isinstance(updates, str) else updates

        description = f"# 🔄 Dependency Updates for {repo_name}\n\n"
        description += "This PR updates outdated dependencies to their latest versions.\n\n"

        description += "## 📦 Updated Dependencies\n\n"

        # Categorize updates
        major_updates = []
        minor_updates = []
        patch_updates = []

        for update in updates_list:
            name = update.get("name", "unknown")
            current = update.get("current", "unknown")
            latest = update.get("latest", "unknown")

            # Determine update type
            try:
                current_clean = current.lstrip('^~')
                curr_parts = current_clean.split('.')
                latest_parts = latest.split('.')

                if len(curr_parts) >= 1 and len(latest_parts) >= 1:
                    if curr_parts[0] != latest_parts[0]:
                        major_updates.append(f"- 🔴 **{name}**: `{current}` → `{latest}` (MAJOR - may have breaking changes)")
                    elif len(curr_parts) >= 2 and len(latest_parts) >= 2 and curr_parts[1] != latest_parts[1]:
                        minor_updates.append(f"- 🟡 **{name}**: `{current}` → `{latest}` (minor)")
                    else:
                        patch_updates.append(f"- 🟢 **{name}**: `{current}` → `{latest}` (patch)")
                else:
                    minor_updates.append(f"- **{name}**: `{current}` → `{latest}`")
            except:
                minor_updates.append(f"- **{name}**: `{current}` → `{latest}`")

        if major_updates:
            description += "### ⚠️ Major Updates\n"
            description += "*These updates may contain breaking changes. Please review carefully.*\n\n"
            description += "\n".join(major_updates) + "\n\n"

        if minor_updates:
            description += "### Minor Updates\n\n"
            description += "\n".join(minor_updates) + "\n\n"

        if patch_updates:
            description += "### Patch Updates\n\n"
            description += "\n".join(patch_updates) + "\n\n"

        # Testing instructions
        description += "## 🧪 Testing Instructions\n\n"
        description += "Please run the following commands to verify the updates:\n\n"
        description += "```bash\n"
        description += testing_strategy + "\n"
        description += "```\n\n"

        # Important notes
        description += "## ⚠️ Important Notes\n\n"

        if major_updates:
            description += "- ⚠️ This PR includes **MAJOR version updates**\n"
            description += "- Review changelogs for breaking changes\n"

        description += "- Run the full test suite before merging\n"
        description += "- Check for deprecation warnings\n"
        description += "- Verify build succeeds\n"
        description += "- Review any peer dependency warnings\n\n"

        description += "## 📋 Checklist\n\n"
        description += "- [ ] All tests pass\n"
        description += "- [ ] Build succeeds without errors\n"
        description += "- [ ] No new warnings introduced\n"
        description += "- [ ] Changelog reviewed for breaking changes\n"
        description += "- [ ] Documentation updated if needed\n\n"

        description += "---\n\n"
        description += f"*📊 Total dependencies updated: {len(updates_list)}*\n"
        description += "*🤖 This PR was generated by the Dependency Update Agent*\n"

        return description

    except Exception as e:
        return f"Error creating PR description: {str(e)}"


@tool
def format_testing_commands(package_manager: str) -> str:
    """
    Format testing commands for the given package manager.

    Args:
        package_manager: The package manager (npm, pip, cargo, etc.)

    Returns:
        Formatted testing commands
    """
    commands = {
        "npm": """# Install dependencies
npm install

# Run tests
npm test

# Run build
npm run build

# Check for issues
npm run lint""",

        "yarn": """# Install dependencies
yarn install

# Run tests
yarn test

# Run build
yarn build""",

        "pip": """# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Type checking
mypy .""",

        "poetry": """# Install dependencies
poetry install

# Run tests
poetry run pytest

# Build
poetry build""",

        "cargo": """# Build
cargo build

# Run tests
cargo test

# Check
cargo check""",

        "go": """# Build
go build ./...

# Run tests
go test ./...

# Vet
go vet ./..."""
    }

    return commands.get(package_manager, f"# Install and test using {package_manager}")


def create_main_orchestrator_agent():
    """
    Create the main orchestrator agent.
    """
    tools = [
        run_dependency_analyzer,
        run_dependency_updater,
        create_github_pr_description,
        format_testing_commands
    ]

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a dependency update automation agent. Your goal is to check repositories for outdated dependencies, update them to their latest versions, verify the updates don't cause breaking changes, and create pull requests with the changes.

Your Workflow:

When a user provides a repository name (in owner/repo format) or repository URL, follow these steps:

Step 1: Analyze Dependencies
Use the dependency_analyzer worker to examine the repository and identify outdated dependencies. This worker will:
- Detect the package manager (npm, pip, cargo, etc.)
- Find dependency files
- Identify which dependencies are outdated
- Return a report with current vs. latest versions

Step 2: Update Dependency Files
Use the dependency_updater worker to create updated versions of the dependency files. This worker will:
- Fetch the current dependency files
- Update version numbers to the latest versions
- Determine appropriate build and test commands
- Return the updated file contents and testing strategy

Step 3: Create Pull Request Description
Once you have the updated files and testing strategy:
- Craft a comprehensive PR description that includes:
  - List of updated dependencies (old version → new version)
  - The testing strategy that should be followed
  - Clear instructions: "Please run the following commands to verify the updates..."
  - Warning about potential breaking changes
  - Summary of what was updated

Step 4: Report Results
Provide the user with:
- A summary of what dependencies were updated
- The PR description they should use
- Clear next steps for testing and verification
- Any warnings about potential breaking changes

Important Notes:
- You analyze and prepare updates, but the user creates the actual PR
- Be clear and technical when describing changes
- Use proper semantic versioning terminology (major, minor, patch updates)
- Highlight any major version updates as they're more likely to have breaking changes
- Provide actionable next steps
- Be concise but thorough in PR descriptions

Error Handling:
- If no dependency files are found, clearly state this
- If you cannot determine the package manager, ask for clarification
- If the repository doesn't exist or is inaccessible, inform the user
- If no outdated dependencies are found, congratulate them"""),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    llm = ChatAnthropic(
        model="claude-3-5-sonnet-20241022",
        temperature=0
    )

    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=20,
        handle_parsing_errors=True
    )

    return agent_executor


def main():
    """
    Main entry point for the dependency update agent.
    """
    if len(sys.argv) < 2:
        print("Usage: python dependency_update_agent.py <repository>")
        print("\nExamples:")
        print("  python dependency_update_agent.py https://github.com/owner/repo")
        print("  python dependency_update_agent.py owner/repo")
        sys.exit(1)

    repo_input = sys.argv[1]

    # Convert owner/repo to full URL if needed
    if not repo_input.startswith("http"):
        repo_url = f"https://github.com/{repo_input}"
        repo_name = repo_input
    else:
        repo_url = repo_input
        # Extract owner/repo from URL
        parts = repo_url.rstrip('/').split('/')
        repo_name = f"{parts[-2]}/{parts[-1]}"

    print("="*80)
    print("🤖 Dependency Update Agent")
    print("="*80)
    print(f"\n📦 Repository: {repo_name}")
    print(f"🔗 URL: {repo_url}\n")

    # Create and run the orchestrator agent
    agent = create_main_orchestrator_agent()

    try:
        result = agent.invoke({
            "input": f"Analyze and prepare dependency updates for repository: {repo_url} ({repo_name})"
        })

        print("\n" + "="*80)
        print("✅ FINAL REPORT")
        print("="*80)
        print(result["output"])
        print("\n")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
