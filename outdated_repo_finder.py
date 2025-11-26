#!/usr/bin/env python3
"""
Outdated Repository Finder using LangChain Tool Calling

This script uses LangChain's tool calling pattern to analyze a repository
and find outdated dependencies across different package managers.
"""

import os
import subprocess
import json
from typing import Optional, List, Dict, Any
from pathlib import Path
import tempfile
import shutil
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

# Load environment variables from .env file
load_dotenv()


@tool
def clone_repository(repo_url: str) -> str:
    """
    Clone a git repository to a temporary directory.

    Args:
        repo_url: The URL of the git repository to clone

    Returns:
        The path to the cloned repository
    """
    try:
        temp_dir = tempfile.mkdtemp(prefix="repo_check_")
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, temp_dir],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            return f"Error cloning repository: {result.stderr}"

        return f"Repository cloned successfully to: {temp_dir}"
    except subprocess.TimeoutExpired:
        return "Error: Repository cloning timed out"
    except Exception as e:
        return f"Error cloning repository: {str(e)}"


@tool
def detect_package_managers(repo_path: str) -> str:
    """
    Detect which package managers are used in the repository.

    Args:
        repo_path: Path to the repository directory

    Returns:
        A JSON string listing detected package managers and their config files
    """
    package_managers = {}

    # Check for Node.js (npm/yarn)
    if os.path.exists(os.path.join(repo_path, "package.json")):
        package_managers["npm"] = "package.json"

    # Check for Python (pip)
    if os.path.exists(os.path.join(repo_path, "requirements.txt")):
        package_managers["pip"] = "requirements.txt"

    if os.path.exists(os.path.join(repo_path, "Pipfile")):
        package_managers["pipenv"] = "Pipfile"

    if os.path.exists(os.path.join(repo_path, "pyproject.toml")):
        package_managers["poetry"] = "pyproject.toml"

    # Check for Ruby
    if os.path.exists(os.path.join(repo_path, "Gemfile")):
        package_managers["bundler"] = "Gemfile"

    # Check for Java (Maven)
    if os.path.exists(os.path.join(repo_path, "pom.xml")):
        package_managers["maven"] = "pom.xml"

    # Check for Java (Gradle)
    if os.path.exists(os.path.join(repo_path, "build.gradle")) or \
       os.path.exists(os.path.join(repo_path, "build.gradle.kts")):
        package_managers["gradle"] = "build.gradle"

    # Check for PHP (Composer)
    if os.path.exists(os.path.join(repo_path, "composer.json")):
        package_managers["composer"] = "composer.json"

    # Check for Rust (Cargo)
    if os.path.exists(os.path.join(repo_path, "Cargo.toml")):
        package_managers["cargo"] = "Cargo.toml"

    # Check for Go
    if os.path.exists(os.path.join(repo_path, "go.mod")):
        package_managers["go"] = "go.mod"

    return json.dumps(package_managers, indent=2)


@tool
def check_npm_outdated(repo_path: str) -> str:
    """
    Check for outdated npm packages.

    Args:
        repo_path: Path to the repository directory

    Returns:
        Information about outdated npm packages
    """
    try:
        # Change to repo directory
        original_dir = os.getcwd()
        os.chdir(repo_path)

        # Check if package.json exists
        if not os.path.exists("package.json"):
            return "No package.json found in repository"

        # Run npm outdated (returns exit code 1 if there are outdated packages)
        result = subprocess.run(
            ["npm", "outdated", "--json"],
            capture_output=True,
            text=True,
            timeout=60
        )

        os.chdir(original_dir)

        if result.stdout:
            outdated_data = json.loads(result.stdout)
            if outdated_data:
                summary = f"Found {len(outdated_data)} outdated npm packages:\n\n"
                for package, info in outdated_data.items():
                    summary += f"- {package}: {info.get('current', 'N/A')} → {info.get('latest', 'N/A')}\n"
                return summary
            else:
                return "All npm packages are up to date!"
        else:
            return "All npm packages are up to date!"

    except subprocess.TimeoutExpired:
        os.chdir(original_dir)
        return "Error: npm outdated command timed out"
    except Exception as e:
        os.chdir(original_dir)
        return f"Error checking npm packages: {str(e)}"


@tool
def check_pip_outdated(repo_path: str) -> str:
    """
    Check for outdated pip packages.

    Args:
        repo_path: Path to the repository directory

    Returns:
        Information about outdated pip packages
    """
    try:
        requirements_file = os.path.join(repo_path, "requirements.txt")

        if not os.path.exists(requirements_file):
            return "No requirements.txt found in repository"

        # Read requirements
        with open(requirements_file, 'r') as f:
            requirements = f.read()

        # Use pip list --outdated
        result = subprocess.run(
            ["pip", "list", "--outdated", "--format=json"],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.stdout:
            outdated_data = json.loads(result.stdout)
            if outdated_data:
                summary = f"Found {len(outdated_data)} outdated pip packages:\n\n"
                for package in outdated_data:
                    summary += f"- {package['name']}: {package['version']} → {package['latest_version']}\n"
                return summary
            else:
                return "All pip packages are up to date!"
        else:
            return "All pip packages are up to date!"

    except subprocess.TimeoutExpired:
        return "Error: pip list command timed out"
    except Exception as e:
        return f"Error checking pip packages: {str(e)}"


@tool
def check_cargo_outdated(repo_path: str) -> str:
    """
    Check for outdated Rust cargo packages.

    Args:
        repo_path: Path to the repository directory

    Returns:
        Information about outdated cargo packages
    """
    try:
        cargo_file = os.path.join(repo_path, "Cargo.toml")

        if not os.path.exists(cargo_file):
            return "No Cargo.toml found in repository"

        original_dir = os.getcwd()
        os.chdir(repo_path)

        # cargo outdated requires cargo-outdated to be installed
        result = subprocess.run(
            ["cargo", "outdated", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=60
        )

        os.chdir(original_dir)

        if result.returncode != 0:
            return "Note: cargo-outdated not installed. Run: cargo install cargo-outdated"

        if result.stdout:
            return f"Cargo outdated results:\n{result.stdout}"
        else:
            return "All cargo packages are up to date!"

    except subprocess.TimeoutExpired:
        os.chdir(original_dir)
        return "Error: cargo outdated command timed out"
    except Exception as e:
        os.chdir(original_dir)
        return f"Error checking cargo packages: {str(e)}"


@tool
def cleanup_repository(repo_path: str) -> str:
    """
    Clean up the cloned repository directory.

    Args:
        repo_path: Path to the repository directory to remove

    Returns:
        Confirmation message
    """
    try:
        if os.path.exists(repo_path) and repo_path.startswith("/tmp/repo_check_"):
            shutil.rmtree(repo_path)
            return f"Successfully cleaned up repository at {repo_path}"
        else:
            return "Invalid repository path or path doesn't exist"
    except Exception as e:
        return f"Error cleaning up repository: {str(e)}"


def create_outdated_finder_agent():
    """
    Create a LangGraph agent with tools for finding outdated dependencies.
    """
    # Define the tools
    tools = [
        clone_repository,
        detect_package_managers,
        check_npm_outdated,
        check_pip_outdated,
        check_cargo_outdated,
        cleanup_repository
    ]

    # Initialize the LLM with tool calling support
    llm = ChatAnthropic(
        model="claude-3-5-sonnet-20241022",
        temperature=0
    )

    # System message for the agent
    system_message = """You are a helpful assistant that analyzes repositories for outdated dependencies.

When given a repository URL, you should:
1. Clone the repository
2. Detect which package managers are used
3. Check for outdated dependencies using the appropriate tools
4. Provide a summary of findings
5. Clean up the cloned repository

Be thorough and check all detected package managers."""

    # Create the react agent using langgraph
    agent_executor = create_react_agent(llm, tools, prompt=system_message)

    return agent_executor


def main():
    """
    Main function to run the outdated repository finder.
    """
    import sys

    if len(sys.argv) < 2:
        print("Usage: python outdated_repo_finder.py <repository_url>")
        print("\nExample:")
        print("  python outdated_repo_finder.py https://github.com/user/repo")
        sys.exit(1)

    repo_url = sys.argv[1]

    print(f"🔍 Analyzing repository: {repo_url}\n")

    # Create the agent
    agent_executor = create_outdated_finder_agent()

    # Run the agent
    try:
        result = agent_executor.invoke({
            "messages": [("user", f"Analyze this repository for outdated dependencies: {repo_url}")]
        })

        print("\n" + "="*80)
        print("FINAL REPORT")
        print("="*80)
        # Extract the final AI message from the result
        final_message = result["messages"][-1]
        print(final_message.content)

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
