#!/usr/bin/env python3
"""
Dependency Analyzer Agent

Analyzes a repository to identify its package manager, locate dependency files,
and identify outdated dependencies.
"""

import os
import json
import subprocess
import tempfile
import shutil
import requests
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic
from langchain.agents import create_agent

# Import caching module
from repository_cache import get_cache

# Load environment variables from .env file
load_dotenv()


@tool
def clone_repository(repo_url: str) -> str:
    """
    Clone a git repository to a temporary directory with caching support.

    Args:
        repo_url: The URL of the git repository to clone (e.g., https://github.com/owner/repo)

    Returns:
        JSON string with status and repository path
    """
    try:
        cache = get_cache()

        # Check if repository is already cached
        cached_path = cache.get_cached_repository(repo_url)
        if cached_path:
            # Copy cached repo to temp directory
            temp_dir = tempfile.mkdtemp(prefix="dep_analyzer_")
            shutil.copytree(cached_path, temp_dir, dirs_exist_ok=True)

            return json.dumps({
                "status": "success",
                "repo_path": temp_dir,
                "message": f"Repository loaded from cache to {temp_dir}",
                "from_cache": True
            })

        # Clone fresh repository
        temp_dir = tempfile.mkdtemp(prefix="dep_analyzer_")
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, temp_dir],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            return json.dumps({
                "status": "error",
                "message": f"Failed to clone repository: {result.stderr}"
            })

        # Cache the cloned repository
        try:
            cache.cache_repository(repo_url, temp_dir)
        except Exception as cache_error:
            # Don't fail if caching fails
            print(f"Warning: Failed to cache repository: {cache_error}")

        return json.dumps({
            "status": "success",
            "repo_path": temp_dir,
            "message": f"Repository cloned successfully to {temp_dir}",
            "from_cache": False
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error cloning repository: {str(e)}"
        })


@tool
def detect_package_manager(repo_path: str) -> str:
    """
    Detect which package manager is used in the repository.

    Args:
        repo_path: Path to the cloned repository

    Returns:
        JSON string with detected package manager and dependency files
    """
    package_managers = {}

    # JavaScript/TypeScript - npm/yarn/pnpm
    if os.path.exists(os.path.join(repo_path, "package.json")):
        package_managers["npm"] = {
            "files": ["package.json"],
            "lock_files": []
        }
        if os.path.exists(os.path.join(repo_path, "package-lock.json")):
            package_managers["npm"]["lock_files"].append("package-lock.json")
        if os.path.exists(os.path.join(repo_path, "yarn.lock")):
            package_managers["npm"]["lock_files"].append("yarn.lock")
        if os.path.exists(os.path.join(repo_path, "pnpm-lock.yaml")):
            package_managers["npm"]["lock_files"].append("pnpm-lock.yaml")

    # Python - pip
    if os.path.exists(os.path.join(repo_path, "requirements.txt")):
        package_managers["pip"] = {
            "files": ["requirements.txt"],
            "lock_files": []
        }

    # Python - pipenv
    if os.path.exists(os.path.join(repo_path, "Pipfile")):
        package_managers["pipenv"] = {
            "files": ["Pipfile"],
            "lock_files": ["Pipfile.lock"] if os.path.exists(os.path.join(repo_path, "Pipfile.lock")) else []
        }

    # Python - poetry
    if os.path.exists(os.path.join(repo_path, "pyproject.toml")):
        # Check if it's poetry by looking for [tool.poetry] section
        pyproject_path = os.path.join(repo_path, "pyproject.toml")
        try:
            with open(pyproject_path, 'r') as f:
                content = f.read()
                if '[tool.poetry]' in content:
                    package_managers["poetry"] = {
                        "files": ["pyproject.toml"],
                        "lock_files": ["poetry.lock"] if os.path.exists(os.path.join(repo_path, "poetry.lock")) else []
                    }
        except:
            pass

    # Ruby - bundler
    if os.path.exists(os.path.join(repo_path, "Gemfile")):
        package_managers["bundler"] = {
            "files": ["Gemfile"],
            "lock_files": ["Gemfile.lock"] if os.path.exists(os.path.join(repo_path, "Gemfile.lock")) else []
        }

    # Java - Maven
    if os.path.exists(os.path.join(repo_path, "pom.xml")):
        package_managers["maven"] = {
            "files": ["pom.xml"],
            "lock_files": []
        }

    # Java - Gradle
    gradle_files = []
    if os.path.exists(os.path.join(repo_path, "build.gradle")):
        gradle_files.append("build.gradle")
    if os.path.exists(os.path.join(repo_path, "build.gradle.kts")):
        gradle_files.append("build.gradle.kts")
    if gradle_files:
        package_managers["gradle"] = {
            "files": gradle_files,
            "lock_files": []
        }

    # PHP - Composer
    if os.path.exists(os.path.join(repo_path, "composer.json")):
        package_managers["composer"] = {
            "files": ["composer.json"],
            "lock_files": ["composer.lock"] if os.path.exists(os.path.join(repo_path, "composer.lock")) else []
        }

    # Rust - Cargo
    if os.path.exists(os.path.join(repo_path, "Cargo.toml")):
        package_managers["cargo"] = {
            "files": ["Cargo.toml"],
            "lock_files": ["Cargo.lock"] if os.path.exists(os.path.join(repo_path, "Cargo.lock")) else []
        }

    # Go
    if os.path.exists(os.path.join(repo_path, "go.mod")):
        package_managers["go"] = {
            "files": ["go.mod"],
            "lock_files": ["go.sum"] if os.path.exists(os.path.join(repo_path, "go.sum")) else []
        }

    return json.dumps(package_managers, indent=2)


@tool
def read_dependency_file(repo_path: str, file_path: str) -> str:
    """
    Read the contents of a dependency file.

    Args:
        repo_path: Path to the repository
        file_path: Relative path to the dependency file

    Returns:
        File contents
    """
    try:
        full_path = os.path.join(repo_path, file_path)
        with open(full_path, 'r') as f:
            content = f.read()
        return content
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def check_npm_outdated(repo_path: str, repo_url: str = "") -> str:
    """
    Check for outdated npm packages using npm outdated command with caching.

    Args:
        repo_path: Path to the repository
        repo_url: Repository URL for caching (optional)

    Returns:
        JSON string with outdated packages information
    """
    try:
        cache = get_cache()

        # Check cache if repo_url provided
        if repo_url:
            cached_data = cache.get_cached_outdated(repo_url)
            if cached_data and cached_data.get("package_manager") == "npm":
                cached_data["from_cache"] = True
                return json.dumps(cached_data, indent=2)

        original_dir = os.getcwd()
        os.chdir(repo_path)

        if not os.path.exists("package.json"):
            return json.dumps({"status": "error", "message": "No package.json found"})

        # Run npm outdated
        result = subprocess.run(
            ["npm", "outdated", "--json"],
            capture_output=True,
            text=True,
            timeout=60
        )

        os.chdir(original_dir)

        if result.stdout:
            try:
                outdated_data = json.loads(result.stdout)
                outdated_list = []

                for package, info in outdated_data.items():
                    outdated_list.append({
                        "name": package,
                        "current": info.get("current", "N/A"),
                        "wanted": info.get("wanted", "N/A"),
                        "latest": info.get("latest", "N/A"),
                        "location": info.get("location", "N/A")
                    })

                result_data = {
                    "status": "success",
                    "package_manager": "npm",
                    "outdated_count": len(outdated_list),
                    "outdated_packages": outdated_list,
                    "from_cache": False
                }

                # Cache the results if repo_url provided
                if repo_url:
                    try:
                        cache.cache_outdated(repo_url, result_data)
                    except Exception as cache_error:
                        print(f"Warning: Failed to cache outdated data: {cache_error}")

                return json.dumps(result_data, indent=2)
            except json.JSONDecodeError:
                result_data = {
                    "status": "success",
                    "package_manager": "npm",
                    "outdated_count": 0,
                    "outdated_packages": [],
                    "message": "All packages are up to date",
                    "from_cache": False
                }

                # Cache the results if repo_url provided
                if repo_url:
                    try:
                        cache.cache_outdated(repo_url, result_data)
                    except Exception as cache_error:
                        print(f"Warning: Failed to cache outdated data: {cache_error}")

                return json.dumps(result_data, indent=2)
        else:
            return json.dumps({
                "status": "success",
                "package_manager": "npm",
                "outdated_count": 0,
                "outdated_packages": [],
                "message": "All packages are up to date"
            })

    except subprocess.TimeoutExpired:
        os.chdir(original_dir)
        return json.dumps({"status": "error", "message": "npm outdated command timed out"})
    except Exception as e:
        os.chdir(original_dir)
        return json.dumps({"status": "error", "message": f"Error checking npm packages: {str(e)}"})


@tool
def check_pip_outdated(repo_path: str, repo_url: str = "") -> str:
    """
    Check for outdated pip packages by reading requirements.txt with caching.

    Args:
        repo_path: Path to the repository
        repo_url: Repository URL for caching (optional)

    Returns:
        JSON string with outdated packages information
    """
    try:
        cache = get_cache()

        # Check cache if repo_url provided
        if repo_url:
            cached_data = cache.get_cached_outdated(repo_url)
            if cached_data and cached_data.get("package_manager") == "pip":
                cached_data["from_cache"] = True
                return json.dumps(cached_data, indent=2)

        requirements_file = os.path.join(repo_path, "requirements.txt")

        if not os.path.exists(requirements_file):
            return json.dumps({"status": "error", "message": "No requirements.txt found"})

        # Read requirements
        with open(requirements_file, 'r') as f:
            requirements = f.readlines()

        # Parse package names (basic parsing)
        packages = []
        for line in requirements:
            line = line.strip()
            if line and not line.startswith('#'):
                # Simple parsing - handle package==version
                if '==' in line:
                    parts = line.split('==')
                    packages.append({
                        "name": parts[0].strip(),
                        "current": parts[1].strip() if len(parts) > 1 else "unknown"
                    })
                elif '>=' in line:
                    parts = line.split('>=')
                    packages.append({
                        "name": parts[0].strip(),
                        "current": parts[1].strip() if len(parts) > 1 else "unknown"
                    })
                else:
                    packages.append({
                        "name": line,
                        "current": "unspecified"
                    })

        # Check each package against PyPI directly (more reliable than pip list --outdated)
        outdated_list = []

        for pkg in packages:
            try:
                pkg_name = pkg["name"]
                current_version = pkg.get("current", "unspecified")

                # Skip if no version specified
                if current_version == "unspecified":
                    continue

                # Query PyPI API for latest version
                response = requests.get(
                    f"https://pypi.org/pypi/{pkg_name}/json",
                    timeout=5
                )

                if response.status_code == 200:
                    pypi_data = response.json()
                    latest_version = pypi_data["info"]["version"]

                    # Compare versions (simple string comparison for now)
                    if current_version != latest_version:
                        outdated_list.append({
                            "name": pkg_name,
                            "current": current_version,
                            "latest": latest_version
                        })
            except Exception as e:
                # Skip packages that can't be checked
                print(f"Warning: Could not check {pkg.get('name', 'unknown')}: {e}")
                continue

        result_data = {
            "status": "success",
            "package_manager": "pip",
            "outdated_count": len(outdated_list),
            "outdated_packages": outdated_list,
            "from_cache": False
        }

        # Cache the results if repo_url provided
        if repo_url:
            try:
                cache.cache_outdated(repo_url, result_data)
            except Exception as cache_error:
                print(f"Warning: Failed to cache outdated data: {cache_error}")

        return json.dumps(result_data, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "message": f"Error checking pip packages: {str(e)}"})


@tool
def cleanup_repository(repo_path: str) -> str:
    """
    Clean up the cloned repository.

    Args:
        repo_path: Path to the repository to remove

    Returns:
        Confirmation message
    """
    try:
        if os.path.exists(repo_path) and (repo_path.startswith("/tmp/dep_analyzer_") or repo_path.startswith("/tmp/repo_check_")):
            shutil.rmtree(repo_path)
            return json.dumps({"status": "success", "message": f"Cleaned up {repo_path}"})
        return json.dumps({"status": "error", "message": "Invalid path or path doesn't exist"})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Error during cleanup: {str(e)}"})


def create_dependency_analyzer_agent():
    """
    Create the dependency analyzer agent.
    """
    tools = [
        clone_repository,
        detect_package_manager,
        read_dependency_file,
        check_npm_outdated,
        check_pip_outdated,
        cleanup_repository
    ]

    system_message = """You are a dependency analysis specialist. Your task is to analyze a repository and identify outdated dependencies.

Your Process:

1. Detect Package Manager: Examine the repository structure to identify the package manager:
   - Look for package.json (npm/yarn/pnpm for JavaScript/TypeScript)
   - Look for requirements.txt, setup.py, pyproject.toml, Pipfile (Python)
   - Look for go.mod (Go), Cargo.toml (Rust), composer.json (PHP), etc.

2. Locate Dependency Files: Find all relevant dependency definition files in the repository.

3. Parse Current Dependencies: Extract the list of dependencies and their current versions from the dependency files.

4. Check for Updates: For each dependency, check for the latest available version.

5. Identify Outdated Dependencies: Compare current versions with latest versions and create a list of dependencies that can be updated.

Output Format:

Return a structured report in the following format:

Package Manager: [detected package manager]
Dependency File(s): [list of files]

Outdated Dependencies:
- [dependency-name]: [current-version] → [latest-version]
- [dependency-name]: [current-version] → [latest-version]
...

Total outdated: [count]

Be thorough and accurate in your analysis. If you cannot determine the package manager or find dependency files, clearly state this in your report."""

    llm = ChatAnthropic(
        model="claude-sonnet-4-5-20250929",
        temperature=0
    )

    agent_executor = create_agent(llm, tools, system_prompt=system_message)

    return agent_executor


def main():
    """
    Main function for the dependency analyzer agent.
    """
    import sys

    if len(sys.argv) < 2:
        print("Usage: python dependency_analyzer.py <repository_url>")
        print("\nExample:")
        print("  python dependency_analyzer.py https://github.com/user/repo")
        sys.exit(1)

    repo_url = sys.argv[1]

    print(f"🔍 Analyzing repository: {repo_url}\n")

    agent_executor = create_dependency_analyzer_agent()

    try:
        result = agent_executor.invoke({
            "messages": [("user", f"Analyze this repository for outdated dependencies: {repo_url}")]
        })

        print("\n" + "="*80)
        print("DEPENDENCY ANALYSIS REPORT")
        print("="*80)
        final_message = result["messages"][-1]
        print(final_message.content)

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
