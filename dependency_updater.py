#!/usr/bin/env python3
"""
Dependency Updater Agent

Takes a list of outdated dependencies and creates updated versions of dependency files
with appropriate testing strategies.
"""

import os
import json
import re
from typing import Dict, List, Optional
from pathlib import Path
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic
from langchain.agents import create_agent

# Load environment variables from .env file
load_dotenv()


@tool
def read_file_content(file_path: str) -> str:
    """
    Read the content of a file.

    Args:
        file_path: Path to the file to read

    Returns:
        File contents as string
    """
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        return json.dumps({
            "status": "success",
            "content": content,
            "file": file_path
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error reading file: {str(e)}"
        })


@tool
def update_package_json(current_content: str, updates: str) -> str:
    """
    Update package.json with new dependency versions.

    Args:
        current_content: Current package.json content
        updates: JSON string with dependency updates [{"name": "pkg", "current": "1.0.0", "latest": "2.0.0"}]

    Returns:
        Updated package.json content
    """
    try:
        updates_list = json.loads(updates)
        package_data = json.loads(current_content)

        # Update dependencies
        if "dependencies" in package_data:
            for update in updates_list:
                pkg_name = update["name"]
                new_version = update["latest"]
                if pkg_name in package_data["dependencies"]:
                    # Preserve version prefix (^, ~, etc.)
                    old_version = package_data["dependencies"][pkg_name]
                    prefix = ""
                    if old_version.startswith("^"):
                        prefix = "^"
                    elif old_version.startswith("~"):
                        prefix = "~"
                    package_data["dependencies"][pkg_name] = f"{prefix}{new_version}"

        # Update devDependencies
        if "devDependencies" in package_data:
            for update in updates_list:
                pkg_name = update["name"]
                new_version = update["latest"]
                if pkg_name in package_data["devDependencies"]:
                    old_version = package_data["devDependencies"][pkg_name]
                    prefix = ""
                    if old_version.startswith("^"):
                        prefix = "^"
                    elif old_version.startswith("~"):
                        prefix = "~"
                    package_data["devDependencies"][pkg_name] = f"{prefix}{new_version}"

        updated_content = json.dumps(package_data, indent=2)
        return json.dumps({
            "status": "success",
            "updated_content": updated_content
        })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error updating package.json: {str(e)}"
        })


@tool
def update_requirements_txt(current_content: str, updates: str) -> str:
    """
    Update requirements.txt with new dependency versions.

    Args:
        current_content: Current requirements.txt content
        updates: JSON string with dependency updates

    Returns:
        Updated requirements.txt content
    """
    try:
        updates_list = json.loads(updates)
        lines = current_content.split('\n')
        updated_lines = []

        # Create a dict for quick lookup
        updates_dict = {u["name"].lower(): u["latest"] for u in updates_list}

        for line in lines:
            stripped = line.strip()

            # Keep comments and empty lines as is
            if not stripped or stripped.startswith('#'):
                updated_lines.append(line)
                continue

            # Parse package name
            pkg_name = None
            if '==' in stripped:
                pkg_name = stripped.split('==')[0].strip()
            elif '>=' in stripped:
                pkg_name = stripped.split('>=')[0].strip()
            elif '<=' in stripped:
                pkg_name = stripped.split('<=')[0].strip()
            else:
                # No version specified
                pkg_name = stripped

            # Update if found in updates
            if pkg_name and pkg_name.lower() in updates_dict:
                new_version = updates_dict[pkg_name.lower()]
                updated_lines.append(f"{pkg_name}=={new_version}")
            else:
                updated_lines.append(line)

        updated_content = '\n'.join(updated_lines)
        return json.dumps({
            "status": "success",
            "updated_content": updated_content
        })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error updating requirements.txt: {str(e)}"
        })


@tool
def determine_testing_strategy(package_manager: str, repo_path: str = "") -> str:
    """
    Determine the appropriate testing strategy based on package manager.

    Args:
        package_manager: The package manager (npm, pip, cargo, etc.)
        repo_path: Optional path to repository to check for test scripts

    Returns:
        JSON with testing commands
    """
    strategies = {
        "npm": {
            "install": "npm install",
            "build": "npm run build",
            "test": "npm test",
            "lint": "npm run lint",
            "type_check": "npm run type-check or tsc --noEmit"
        },
        "yarn": {
            "install": "yarn install",
            "build": "yarn build",
            "test": "yarn test",
            "lint": "yarn lint"
        },
        "pnpm": {
            "install": "pnpm install",
            "build": "pnpm build",
            "test": "pnpm test",
            "lint": "pnpm lint"
        },
        "pip": {
            "install": "pip install -r requirements.txt",
            "test": "pytest or python -m pytest",
            "lint": "flake8 or pylint",
            "type_check": "mypy ."
        },
        "pipenv": {
            "install": "pipenv install",
            "test": "pipenv run pytest",
            "lint": "pipenv run flake8"
        },
        "poetry": {
            "install": "poetry install",
            "test": "poetry run pytest",
            "build": "poetry build",
            "lint": "poetry run flake8"
        },
        "cargo": {
            "build": "cargo build",
            "test": "cargo test",
            "check": "cargo check",
            "fmt": "cargo fmt --check"
        },
        "go": {
            "build": "go build ./...",
            "test": "go test ./...",
            "vet": "go vet ./...",
            "fmt": "go fmt ./..."
        },
        "maven": {
            "build": "mvn clean install",
            "test": "mvn test",
            "package": "mvn package"
        },
        "gradle": {
            "build": "gradle build",
            "test": "gradle test",
            "check": "gradle check"
        }
    }

    strategy = strategies.get(package_manager, {
        "install": f"{package_manager} install",
        "build": f"{package_manager} build",
        "test": f"{package_manager} test"
    })

    return json.dumps({
        "status": "success",
        "package_manager": package_manager,
        "testing_strategy": strategy
    }, indent=2)


@tool
def generate_pr_description(package_manager: str, updates: str, testing_strategy: str) -> str:
    """
    Generate a comprehensive PR description.

    Args:
        package_manager: The package manager used
        updates: JSON string with dependency updates
        testing_strategy: JSON string with testing commands

    Returns:
        Formatted PR description
    """
    try:
        updates_list = json.loads(updates)
        strategy = json.loads(testing_strategy)

        # Build PR description
        description = "# Dependency Updates\n\n"
        description += "This PR updates outdated dependencies to their latest versions.\n\n"

        # List updates
        description += "## Updated Dependencies\n\n"

        # Categorize by update type
        major_updates = []
        minor_updates = []
        patch_updates = []

        for update in updates_list:
            current = update.get("current", "unknown")
            latest = update.get("latest", "unknown")
            name = update["name"]

            # Try to determine update type
            try:
                current_parts = current.lstrip('^~').split('.')
                latest_parts = latest.split('.')

                if len(current_parts) >= 1 and len(latest_parts) >= 1:
                    if current_parts[0] != latest_parts[0]:
                        major_updates.append(f"- **{name}**: `{current}` → `{latest}` ⚠️ MAJOR")
                    elif len(current_parts) >= 2 and len(latest_parts) >= 2 and current_parts[1] != latest_parts[1]:
                        minor_updates.append(f"- **{name}**: `{current}` → `{latest}` (minor)")
                    else:
                        patch_updates.append(f"- **{name}**: `{current}` → `{latest}` (patch)")
                else:
                    minor_updates.append(f"- **{name}**: `{current}` → `{latest}`")
            except:
                minor_updates.append(f"- **{name}**: `{current}` → `{latest}`")

        if major_updates:
            description += "### Major Updates (Breaking Changes Possible)\n\n"
            description += "\n".join(major_updates) + "\n\n"

        if minor_updates:
            description += "### Minor Updates\n\n"
            description += "\n".join(minor_updates) + "\n\n"

        if patch_updates:
            description += "### Patch Updates\n\n"
            description += "\n".join(patch_updates) + "\n\n"

        # Add testing instructions
        description += "## Testing Strategy\n\n"
        description += "Please run the following commands to verify the updates:\n\n"

        if "testing_strategy" in strategy:
            test_strategy = strategy["testing_strategy"]
            description += "```bash\n"

            if "install" in test_strategy:
                description += f"# Install dependencies\n{test_strategy['install']}\n\n"

            if "build" in test_strategy:
                description += f"# Build the project\n{test_strategy['build']}\n\n"

            if "test" in test_strategy:
                description += f"# Run tests\n{test_strategy['test']}\n\n"

            if "lint" in test_strategy:
                description += f"# Run linter\n{test_strategy['lint']}\n\n"

            if "type_check" in test_strategy:
                description += f"# Check types\n{test_strategy['type_check']}\n"

            description += "```\n\n"

        # Add warnings
        description += "## ⚠️ Important Notes\n\n"

        if major_updates:
            description += "- This PR includes **MAJOR version updates** which may contain breaking changes\n"
            description += "- Please review the changelogs of updated packages carefully\n"

        description += "- Please run the full test suite before merging\n"
        description += "- Check for any deprecation warnings in the build output\n"
        description += "- Review any changes to peer dependencies\n\n"

        description += f"---\n\n*Total dependencies updated: {len(updates_list)}*\n"
        description += f"*Package manager: {package_manager}*\n"

        return json.dumps({
            "status": "success",
            "description": description
        })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error generating PR description: {str(e)}"
        })


def create_dependency_updater_agent():
    """
    Create the dependency updater agent.
    """
    tools = [
        read_file_content,
        update_package_json,
        update_requirements_txt,
        determine_testing_strategy,
        generate_pr_description
    ]

    system_message = """You are a dependency update specialist. Your task is to update dependency files with new versions and determine the appropriate testing strategy.

Your Process:

1. Receive Input: You will be provided with:
   - Repository name
   - Dependency file path(s)
   - List of dependencies to update with current and target versions

2. Retrieve Current Files: Fetch the current dependency files from the repository.

3. Update Versions: Modify the dependency files to update the versions of outdated dependencies to their latest versions. Preserve the file format and structure exactly.

4. Determine Testing Strategy: Based on the package manager and repository type, identify:
   - Build commands (e.g., npm run build, python setup.py build, cargo build)
   - Test commands (e.g., npm test, pytest, cargo test)
   - Any other verification steps

Output Format:

Return a structured report with:

Updated Files:

[file-path]:
```
[complete updated file contents]
```

Testing Strategy:
1. [command to run or verification step]
2. [command to run or verification step]
...

Summary:
- Updated [count] dependencies
- Files modified: [list]

Be precise with file contents and ensure all syntax is correct for the package manager being used."""

    llm = ChatAnthropic(
        model="claude-sonnet-4-5-20250929",
        temperature=0
    )

    agent_executor = create_agent(llm, tools, system_prompt=system_message)

    return agent_executor


def main():
    """
    Main function for testing the dependency updater agent.
    """
    import sys

    if len(sys.argv) < 3:
        print("Usage: python dependency_updater.py <package_manager> <updates_json>")
        print("\nExample:")
        print('  python dependency_updater.py npm \'[{"name":"express","current":"4.17.1","latest":"4.18.2"}]\'')
        sys.exit(1)

    package_manager = sys.argv[1]
    updates_json = sys.argv[2]

    print(f"🔧 Updating dependencies for {package_manager}\n")

    agent_executor = create_dependency_updater_agent()

    try:
        result = agent_executor.invoke({
            "input": f"Update dependency files for {package_manager} with these updates: {updates_json}"
        })

        print("\n" + "="*80)
        print("DEPENDENCY UPDATE REPORT")
        print("="*80)
        print(result["output"])

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
