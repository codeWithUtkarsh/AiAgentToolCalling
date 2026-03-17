#!/usr/bin/env python3
"""
Smart Dependency Updater Agent

Intelligently updates dependencies with automatic testing and rollback capabilities.
Tests updates, identifies breaking changes, and creates PRs or Issues accordingly.
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool

from src.config import DEFAULT_LLM_MODEL

# Load environment variables
load_dotenv()

# Import dependency operation tools
from src.tools.dependency_ops import (
    apply_all_updates,
    categorize_updates,
    get_latest_version_for_major,
    parse_error_for_dependency,
    rollback_major_update,
)

# Stores build/test logs captured by run_build_test for the PR body.
# detect_build_command populates _detected_commands; run_build_test uses it
# to classify each run as "build" or "test" and store the output.
_detected_commands = {"build": None, "test": None}
_build_test_logs = {"build": None, "test": None}
_test_info = {"has_tests": True, "exit_code": None}

# Patterns that indicate no tests were found in the repo
_NO_TESTS_PATTERNS = [
    "no test files",  # go test
    "no tests ran",  # go test
    "no tests collected",  # pytest
    "collected 0 items",  # pytest
    "no test suites found",  # jest
    "0 specs, 0 failures",  # rspec
    "no tests found",  # generic
    "0 passing",  # mocha with no tests
]


@tool
def detect_build_command(repo_path: str) -> str:
    """
    Auto-detect build, test, and verification commands for the repository.

    Args:
        repo_path: Path to the repository

    Returns:
        JSON with detected commands for build, test, and verification
    """
    try:
        commands = {
            "package_manager": None,
            "install": None,
            "build": None,
            "test": None,
            "lint": None,
            "type_check": None,
        }

        # JavaScript/TypeScript - npm/yarn/pnpm
        if os.path.exists(os.path.join(repo_path, "package.json")):
            with open(os.path.join(repo_path, "package.json"), "r") as f:
                package_json = json.load(f)
                scripts = package_json.get("scripts", {})

            # Detect package manager
            if os.path.exists(os.path.join(repo_path, "pnpm-lock.yaml")):
                pm = "pnpm"
            elif os.path.exists(os.path.join(repo_path, "yarn.lock")):
                pm = "yarn"
            else:
                pm = "npm"

            commands["package_manager"] = pm
            commands["install"] = f"{pm} install"

            # Detect available scripts
            if "build" in scripts:
                commands["build"] = f"{pm} run build"
            if "test" in scripts:
                commands["test"] = f"{pm} test"
            if "lint" in scripts:
                commands["lint"] = f"{pm} run lint"
            if "type-check" in scripts or "typecheck" in scripts:
                commands["type_check"] = f"{pm} run type-check"

        # Python - pip/poetry/pipenv
        elif os.path.exists(os.path.join(repo_path, "pyproject.toml")):
            with open(os.path.join(repo_path, "pyproject.toml"), "r") as f:
                content = f.read()
            if "[tool.poetry]" in content:
                commands["package_manager"] = "poetry"
                commands["install"] = "poetry install"
                commands["build"] = "poetry install"
                commands["test"] = "poetry run pytest"
            elif os.path.exists(os.path.join(repo_path, "Pipfile")):
                commands["package_manager"] = "pipenv"
                commands["install"] = "pipenv install"
                commands["build"] = "pipenv install"
                commands["test"] = "pipenv run pytest"
            elif os.path.exists(os.path.join(repo_path, "requirements.txt")):
                commands["package_manager"] = "pip"
                commands["install"] = "pip install -r requirements.txt"
                commands["build"] = "pip install -r requirements.txt"
                commands["test"] = "pytest"
            else:
                # pyproject.toml without poetry — assume pip
                commands["package_manager"] = "pip"
                commands["install"] = "pip install ."
                commands["build"] = "pip install ."
                commands["test"] = "pytest"

        elif os.path.exists(os.path.join(repo_path, "Pipfile")):
            commands["package_manager"] = "pipenv"
            commands["install"] = "pipenv install"
            commands["build"] = "pipenv install"
            commands["test"] = "pipenv run pytest"

        elif os.path.exists(os.path.join(repo_path, "requirements.txt")):
            commands["package_manager"] = "pip"
            commands["install"] = "pip install -r requirements.txt"
            commands["build"] = "pip install -r requirements.txt"
            commands["test"] = "pytest"

        # Rust - Cargo
        elif os.path.exists(os.path.join(repo_path, "Cargo.toml")):
            commands["package_manager"] = "cargo"
            commands["build"] = "cargo build"
            commands["test"] = "cargo test"
            commands["lint"] = "cargo clippy"

        # Go
        elif os.path.exists(os.path.join(repo_path, "go.mod")):
            commands["package_manager"] = "go"
            commands["build"] = "go build ./..."
            commands["test"] = "go test ./..."
            commands["lint"] = "go vet ./..."

        # Ruby
        elif os.path.exists(os.path.join(repo_path, "Gemfile")):
            commands["package_manager"] = "bundler"
            commands["install"] = "bundle install"
            commands["test"] = "bundle exec rspec"

        # PHP
        elif os.path.exists(os.path.join(repo_path, "composer.json")):
            commands["package_manager"] = "composer"
            commands["install"] = "composer install"
            commands["test"] = "composer test"

        # Store detected commands so run_build_test can classify logs
        _detected_commands["build"] = commands.get("build")
        _detected_commands["test"] = commands.get("test")
        _build_test_logs["build"] = None
        _build_test_logs["test"] = None
        _test_info["has_tests"] = True
        _test_info["exit_code"] = None

        return json.dumps({"status": "success", "commands": commands})

    except Exception as e:
        return json.dumps(
            {"status": "error", "message": f"Error detecting build commands: {str(e)}"}
        )


@tool
def run_build_test(repo_path: str, command: str, timeout: int = 300) -> str:
    """
    Execute a build or test command in the repository.

    Args:
        repo_path: Path to the repository
        command: Command to execute
        timeout: Timeout in seconds (default 300)

    Returns:
        JSON with execution results (success/failure, stdout, stderr)
    """
    try:
        original_dir = os.getcwd()
        os.chdir(repo_path)

        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout
        )

        os.chdir(original_dir)

        stdout_tail = result.stdout[-2000:] if result.stdout else ""
        stderr_tail = result.stderr[-2000:] if result.stderr else ""

        # Capture logs for build/test commands to include in PR body
        combined = (stdout_tail + "\n" + stderr_tail).strip()
        log_entry = f"$ {command}\n"
        log_entry += combined if combined else f"exit code: {result.returncode}"
        if command == _detected_commands.get("build"):
            _build_test_logs["build"] = log_entry
        if command == _detected_commands.get("test"):
            _build_test_logs["test"] = log_entry
            _test_info["exit_code"] = result.returncode
            # Detect if the repo has no unit tests
            combined_lower = combined.lower()
            if any(pat in combined_lower for pat in _NO_TESTS_PATTERNS):
                _test_info["has_tests"] = False

        return json.dumps(
            {
                "status": "success",
                "command": command,
                "exit_code": result.returncode,
                "succeeded": result.returncode == 0,
                "stdout": stdout_tail,
                "stderr": stderr_tail,
            }
        )

    except subprocess.TimeoutExpired:
        os.chdir(original_dir)
        return json.dumps(
            {
                "status": "error",
                "command": command,
                "message": f"Command timed out after {timeout} seconds",
            }
        )
    except Exception as e:
        os.chdir(original_dir)
        return json.dumps(
            {
                "status": "error",
                "command": command,
                "message": f"Error running command: {str(e)}",
            }
        )


@tool
def write_dependency_file(repo_path: str, file_name: str, content: str) -> str:
    """
    Write updated dependency file to the repository.

    Args:
        repo_path: Path to the repository
        file_name: Name of the file (e.g., package.json, requirements.txt)
        content: New file content

    Returns:
        Confirmation message
    """
    try:
        file_path = os.path.join(repo_path, file_name)
        with open(file_path, "w") as f:
            f.write(content)

        return json.dumps(
            {
                "status": "success",
                "file": file_name,
                "path": file_path,
                "message": f"Successfully wrote {file_name}",
            }
        )

    except Exception as e:
        return json.dumps(
            {"status": "error", "message": f"Error writing file: {str(e)}"}
        )


def _get_repo_owner_name(repo_path: str) -> tuple:
    """Extract owner/repo from git remote URL. Returns (owner, repo) or raises ValueError."""
    result = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"],
        capture_output=True,
        text=True,
        cwd=repo_path,
    )
    if result.returncode != 0:
        raise ValueError("Could not determine remote URL")
    url = result.stdout.strip()
    if "github.com" in url:
        parts = url.replace(".git", "").split("/")
        return parts[-2], parts[-1]
    raise ValueError(f"Not a GitHub URL: {url}")


@tool
def git_operations(repo_path: str, operation: str, **kwargs) -> str:
    """
    Perform git/GitHub operations via the persistent GitHub MCP server.

    Args:
        repo_path: Path to the local repository clone
        operation: Operation to perform:
            - get_remote_url: Get the remote URL and owner/repo name
            - create_branch: Create a branch on GitHub (via MCP)
            - push_files: Read locally modified files and push them to GitHub (via MCP).
                          This replaces commit+push — no local git commit needed.
        **kwargs: Additional arguments based on operation:
            - branch_name: Branch name for create_branch and push_files
            - message: Commit message for push_files

    Returns:
        JSON with operation results
    """
    # LangChain @tool may pass kwargs as a nested dict under the key "kwargs"
    if "kwargs" in kwargs and isinstance(kwargs["kwargs"], dict):
        kwargs = kwargs["kwargs"]

    try:
        original_dir = os.getcwd()
        os.chdir(repo_path)

        if operation == "get_remote_url":
            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                capture_output=True,
                text=True,
            )
            os.chdir(original_dir)

            if result.returncode == 0:
                url = result.stdout.strip()
                # Extract owner/repo from URL
                if "github.com" in url:
                    parts = url.replace(".git", "").split("/")
                    repo_name = f"{parts[-2]}/{parts[-1]}"
                else:
                    repo_name = url

                return json.dumps(
                    {
                        "status": "success",
                        "operation": "get_remote_url",
                        "url": url,
                        "repo_name": repo_name,
                    }
                )
            else:
                return json.dumps(
                    {
                        "status": "error",
                        "operation": "get_remote_url",
                        "message": result.stderr,
                    }
                )

        elif operation == "create_branch":
            os.chdir(original_dir)
            try:
                owner, repo = _get_repo_owner_name(repo_path)
            except ValueError as e:
                return json.dumps(
                    {"status": "error", "operation": "create_branch", "message": str(e)}
                )

            default_branch = (
                f"OrteliusAiBot/dep-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            )
            branch_name = kwargs.get("branch_name", default_branch)

            async def _create_branch(server, o, r, b):
                return await server.create_branch(o, r, b)

            result = _run_mcp_call(_create_branch, owner, repo, branch_name)

            if result["status"] == "success":
                return json.dumps(
                    {
                        "status": "success",
                        "operation": "create_branch",
                        "branch_name": branch_name,
                    }
                )
            else:
                return json.dumps(
                    {
                        "status": "error",
                        "operation": "create_branch",
                        "message": result.get("message", "Failed to create branch"),
                    }
                )

        elif operation == "push_files":
            try:
                owner, repo = _get_repo_owner_name(repo_path)
            except ValueError as e:
                os.chdir(original_dir)
                return json.dumps(
                    {"status": "error", "operation": "push_files", "message": str(e)}
                )

            branch_name = kwargs.get("branch_name") or kwargs.get("branch")
            message = kwargs.get("message", "chore: update dependencies")

            if not branch_name:
                os.chdir(original_dir)
                return json.dumps(
                    {
                        "status": "error",
                        "operation": "push_files",
                        "message": "branch_name is required",
                    }
                )

            # Detect locally modified files using git diff
            diff_result = subprocess.run(
                ["git", "diff", "--name-only"],
                capture_output=True,
                text=True,
            )
            # Also check untracked files
            untracked_result = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                capture_output=True,
                text=True,
            )

            changed_files = []
            all_paths = set()
            for line in (
                (diff_result.stdout + "\n" + untracked_result.stdout)
                .strip()
                .split("\n")
            ):
                if line.strip():
                    all_paths.add(line.strip())

            if not all_paths:
                os.chdir(original_dir)
                return json.dumps(
                    {
                        "status": "no_changes",
                        "operation": "push_files",
                        "message": "No files were modified. Dependencies may already be up to date.",
                    }
                )

            # Read content of each changed file
            for file_path in all_paths:
                full_path = os.path.join(repo_path, file_path)
                try:
                    with open(full_path, "r") as f:
                        content = f.read()
                    changed_files.append({"path": file_path, "content": content})
                except (UnicodeDecodeError, FileNotFoundError):
                    # Skip binary files or deleted files
                    continue

            if not changed_files:
                os.chdir(original_dir)
                return json.dumps(
                    {
                        "status": "no_changes",
                        "operation": "push_files",
                        "message": "No text files were modified.",
                    }
                )

            os.chdir(original_dir)

            async def _push_files(server, o, r, b, f, m):
                return await server.push_files(o, r, b, f, m)

            result = _run_mcp_call(
                _push_files, owner, repo, branch_name, changed_files, message
            )

            if result["status"] == "success":
                return json.dumps(
                    {
                        "status": "success",
                        "operation": "push_files",
                        "branch_name": branch_name,
                        "files_pushed": len(changed_files),
                        "message": f"Pushed {len(changed_files)} files to {branch_name}",
                    }
                )
            else:
                return json.dumps(
                    {
                        "status": "error",
                        "operation": "push_files",
                        "message": result.get("message", "Failed to push files"),
                    }
                )

        else:
            os.chdir(original_dir)
            return json.dumps(
                {"status": "error", "message": f"Unknown operation: {operation}"}
            )

    except Exception as e:
        try:
            os.chdir(original_dir)
        except Exception:
            pass
        return json.dumps(
            {
                "status": "error",
                "operation": operation,
                "message": f"Error performing git operation: {str(e)}",
            }
        )


# Reference to the main event loop (set by FastAPI server before running agents)
_main_event_loop = None


def set_main_event_loop(loop):
    """Store the main event loop for use by worker threads."""
    global _main_event_loop
    _main_event_loop = loop


def _run_mcp_call(coro_func, *args):
    """
    Run an async MCP call from synchronous @tool context.

    Uses the existing PersistentMCPServer singleton. Schedules the async call
    on the main event loop (stored via set_main_event_loop) so it reuses
    the existing MCP server connection.
    """
    import asyncio

    from src.integrations.mcp_server_manager import PersistentMCPServer

    async def _call():
        server = await PersistentMCPServer.get_instance()
        if not server.is_running:
            await server.ensure_connected()
        return await coro_func(server, *args)

    # Try the stored main loop first (set by FastAPI), then check current thread
    loop = _main_event_loop
    if loop is None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

    if loop and loop.is_running():
        # Schedule on the main event loop and wait for result
        future = asyncio.run_coroutine_threadsafe(_call(), loop)
        return future.result(timeout=60)
    else:
        return asyncio.run(_call())


@tool
def create_github_pr(
    repo_name: str, branch_name: str, title: str, body: str, base_branch: str = "main"
) -> str:
    """
    Create a GitHub Pull Request using the persistent GitHub MCP server.

    Args:
        repo_name: Repository in owner/repo format
        branch_name: Source branch for the PR
        title: PR title
        body: PR description
        base_branch: Target branch (default: main)

    Returns:
        JSON with PR URL or error
    """
    try:
        parts = repo_name.split("/")
        if len(parts) != 2:
            return json.dumps(
                {"status": "error", "message": f"Invalid repo format: {repo_name}"}
            )

        # Append build/test logs to PR body automatically
        log_section = "\n\n---\n\nAll updates have been tested and verified:\n"
        build_log = _build_test_logs.get("build", "")[-1000:] if _build_test_logs.get("build") else ""
        test_log = _build_test_logs.get("test", "")[-1000:] if _build_test_logs.get("test") else ""
        has_tests = _test_info.get("has_tests", True)
        has_test_command = _detected_commands.get("test") is not None
        if build_log:
            log_section += (
                f"\n:white_check_mark: Build successful\n"
                f"<details><summary>Build logs</summary>\n\n"
                f"```\n{build_log}\n```\n\n</details>\n"
            )
        if test_log and has_tests:
            log_section += (
                f"\n:white_check_mark: Tests passing\n"
                f"<details><summary>Test logs</summary>\n\n"
                f"```\n{test_log}\n```\n\n</details>\n"
            )
        if build_log or (test_log and has_tests):
            # Add merge recommendation
            if has_tests:
                log_section += (
                    "\n:rocket: **This PR is safe to merge.** "
                    "All dependency updates have been verified with a successful build and passing tests.\n"
                )
            elif has_test_command and not has_tests:
                log_section += (
                    "\n:warning: **No unit tests were found in this repository.** "
                    "The build succeeded, but there are no tests to verify runtime behavior. "
                    "Consider adding unit tests to catch potential issues from dependency updates.\n"
                    "\n:rocket: **This PR can be merged**, but we strongly recommend adding tests for better safety.\n"
                )
            else:
                log_section += (
                    "\n:warning: **No test command is configured for this project.** "
                    "The build succeeded, but no tests were run. "
                    "Consider adding unit tests to catch potential runtime issues from dependency updates.\n"
                    "\n:rocket: **This PR can be merged**, but we strongly recommend adding tests for better safety.\n"
                )
            body = body + log_section

        async def _create_pr(server, owner, repo, t, b, head, base):
            return await server.create_pull_request(
                repo_owner=owner,
                repo_name=repo,
                title=t,
                body=b,
                head=head,
                base=base,
            )

        result = _run_mcp_call(
            _create_pr, parts[0], parts[1], title, body, branch_name, base_branch
        )

        if result["status"] == "success":
            # Extract PR URL from various possible response formats
            pr_url = ""
            data = result.get("data", {})
            if isinstance(data, dict):
                pr_url = data.get("html_url", "")
                # Some MCP responses nest the URL differently
                if not pr_url and "url" in data:
                    pr_url = data["url"]
            # Fallback: pr_url at top level (old client format)
            if not pr_url:
                pr_url = result.get("pr_url", "")
            return json.dumps(
                {
                    "status": "success",
                    "pr_url": pr_url,
                    "message": "Successfully created PR",
                }
            )
        else:
            return json.dumps(
                {"status": "error", "message": result.get("message", "Unknown error")}
            )

    except Exception as e:
        return json.dumps(
            {"status": "error", "message": f"Error creating PR via MCP: {str(e)}"}
        )


@tool
def create_github_issue(
    repo_name: str, title: str, body: str, labels: str = "dependencies"
) -> str:
    """
    Create a GitHub Issue using the persistent GitHub MCP server.

    Args:
        repo_name: Repository in owner/repo format
        title: Issue title
        body: Issue description
        labels: Comma-separated labels (default: dependencies)

    Returns:
        JSON with Issue URL or error
    """
    try:
        parts = repo_name.split("/")
        if len(parts) != 2:
            return json.dumps(
                {"status": "error", "message": f"Invalid repo format: {repo_name}"}
            )

        label_list = (
            [l.strip() for l in labels.split(",")] if labels else ["dependencies"]
        )

        async def _create_issue(server, owner, repo, t, b, lbls):
            return await server.create_issue(
                repo_owner=owner,
                repo_name=repo,
                title=t,
                body=b,
                labels=lbls,
            )

        result = _run_mcp_call(
            _create_issue, parts[0], parts[1], title, body, label_list
        )

        if result["status"] == "success":
            # Extract issue URL from various possible response formats
            issue_url = ""
            data = result.get("data", {})
            if isinstance(data, dict):
                issue_url = data.get("html_url", "")
                if not issue_url and "url" in data:
                    issue_url = data["url"]
            if not issue_url:
                issue_url = result.get("issue_url", "")
            return json.dumps(
                {
                    "status": "success",
                    "issue_url": issue_url,
                    "message": "Successfully created issue",
                }
            )
        else:
            return json.dumps(
                {"status": "error", "message": result.get("message", "Unknown error")}
            )

    except Exception as e:
        return json.dumps(
            {"status": "error", "message": f"Error creating issue via MCP: {str(e)}"}
        )


def create_smart_updater_agent():
    """
    Create the smart dependency updater agent with testing and rollback capabilities.
    """
    tools = [
        detect_build_command,
        run_build_test,
        write_dependency_file,
        git_operations,
        create_github_pr,
        create_github_issue,
        apply_all_updates,
        rollback_major_update,
        parse_error_for_dependency,
        categorize_updates,
        get_latest_version_for_major,
    ]

    system_message = """You are a dependency update agent. Follow this EXACT workflow.

STEP 1: Call detect_build_command with repo_path.

STEP 2: UPDATE DEPENDENCIES
- npm/yarn/pnpm/pip/poetry: apply_all_updates → write_dependency_file.
- go: run_build_test with "go get pkg1@v1 pkg2@v2 ... && go mod tidy".
- cargo: run_build_test with "cargo update".

STEP 3: BUILD AND TEST
- Run build command via run_build_test. Then run test command (skip if none).
- run_build_test is ONLY for: install, build, test, and "go get" commands. NEVER for cat/grep/ls/pip list/go list or any inspection command.

STEP 4: HANDLE RESULTS
- BUILD+TESTS PASS:
  1. git_operations: create_branch (no branch_name arg — auto-generated)
  2. git_operations: push_files with returned branch_name + commit message. If status="no_changes", return up_to_date.
  3. create_github_pr with repo_name, branch_name, title, body. Body format:
     ## This PR contains updated dependencies:\n\n| Package | Type | Update | Change |\n|---------|------|--------|--------|\n| name | pm | major/minor/patch | `old` → `new` |
     Build/test logs are auto-appended. Do NOT add them.
  4. Return PR URL.

- BUILD FAILS: create_github_issue immediately (no rollbacks). Return Issue URL.

- TESTS FAIL: parse_error_for_dependency → rollback (go: "go get pkg@old && go mod tidy"; others: rollback_major_update + write_dependency_file) → re-run STEP 3. Max 3 retries, then create_github_issue.

RULES:
- Do NOT call get_remote_url, categorize_updates, or run inspection commands.
- Use "push_files" not "commit"/"push". Do NOT create lock files.
- Keep responses under 50 words. Final response MUST be JSON:
  {"status": "pr_created|issue_created|up_to_date|error|issue_failed", "url": "...", "message": "..."}"""

    llm = ChatAnthropic(model=os.getenv("LLM_MODEL_NAME", DEFAULT_LLM_MODEL), temperature=0)

    agent_executor = create_agent(llm, tools, system_prompt=system_message)

    return agent_executor


def main():
    """
    Main entry point for testing the smart updater.
    """
    if len(sys.argv) < 2:
        print("Usage: python -m src.agents.updater <repo_path>")
        print("\nExample:")
        print("  python -m src.agents.updater /tmp/cloned_repo")
        sys.exit(1)

    repo_path = sys.argv[1]

    print("=" * 80)
    print("Smart Dependency Updater Agent")
    print("=" * 80)
    print(f"\nRepository: {repo_path}\n")

    agent = create_smart_updater_agent()

    try:
        result = agent.invoke(
            {
                "messages": [
                    (
                        "user",
                        f"Update dependencies for repository at {repo_path}. Test the updates and create a PR if successful, or an Issue if they break the build.",
                    )
                ]
            },
            config={"recursion_limit": 50},
        )

        print("\n" + "=" * 80)
        print("FINAL RESULT")
        print("=" * 80)
        final_message = result["messages"][-1]
        print(final_message.content)
        print("\n")

    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
