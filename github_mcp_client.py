#!/usr/bin/env python3
"""
GitHub MCP Client - Integration with GitHub MCP Server

This module provides integration with the GitHub MCP (Model Context Protocol) server
to perform GitHub operations like creating PRs and issues without requiring the gh CLI.
"""

import os
import json
import subprocess
import threading
from typing import Dict, Optional, Any

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Thread-local storage for event loops
_thread_local = threading.local()

load_dotenv()

def _get_event_loop():
    """Get or create an event loop for the current thread."""
    import asyncio

    if not hasattr(_thread_local, 'loop') or _thread_local.loop is None or _thread_local.loop.is_closed():
        try:
            # Try to get the current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If there's a running loop in this thread, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            # No event loop exists in this thread, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        _thread_local.loop = loop

    return _thread_local.loop


def _find_command_path(command: str) -> Optional[str]:
    """
    Find the full path to a command, checking common locations.

    Args:
        command: Command name to find (e.g., 'docker', 'podman')

    Returns:
        Full path to command if found, None otherwise
    """
    import shutil

    # First try using shutil.which (respects PATH)
    cmd_path = shutil.which(command)
    if cmd_path:
        return cmd_path

    # Common installation paths for macOS
    common_paths = [
        f'/usr/local/bin/{command}',
        f'/opt/homebrew/bin/{command}',
        f'/usr/bin/{command}',
        f'/opt/local/bin/{command}',
        # OrbStack specific paths
        f'/Applications/OrbStack.app/Contents/MacOS/{command}',
        f'~/.orbstack/bin/{command}',
    ]

    # Expand ~ and check if file exists
    for path in common_paths:
        expanded_path = os.path.expanduser(path)
        if os.path.isfile(expanded_path) and os.access(expanded_path, os.X_OK):
            return expanded_path

    return None


def _detect_container_runtime() -> str:
    """
    Auto-detect available container runtime.

    Checks for container runtimes in order of preference:
    1. docker (Docker Desktop, OrbStack, Rancher Desktop)
    2. podman (Podman Desktop, native Podman)
    3. nerdctl (containerd with nerdctl)

    Returns:
        Full path or name of the detected container runtime command

    Raises:
        RuntimeError: If no container runtime is found
    """
    runtimes = ['docker', 'podman', 'nerdctl']

    for runtime in runtimes:
        # Try to find the command path
        cmd_path = _find_command_path(runtime)

        if cmd_path:
            # Verify it works by running --version
            try:
                result = subprocess.run(
                    [cmd_path, '--version'],
                    capture_output=True,
                    timeout=5,
                    text=True
                )
                if result.returncode == 0:
                    # Return the full path if it's not standard, otherwise just the name
                    if cmd_path != runtime and not cmd_path.startswith('/usr/'):
                        return cmd_path
                    return runtime
            except (subprocess.TimeoutExpired, Exception):
                continue

    # Provide helpful error message
    error_msg = (
        "No container runtime found. Please ensure one of the following is installed and in PATH:\n"
        "  • Docker Desktop: https://www.docker.com/products/docker-desktop\n"
        "  • OrbStack (macOS): https://orbstack.dev/\n"
        "  • Podman Desktop: https://podman-desktop.io/\n"
        "  • Rancher Desktop: https://rancherdesktop.io/\n\n"
        "If you have OrbStack or Docker installed, try:\n"
        "  1. Restart your terminal\n"
        "  2. Ensure OrbStack/Docker Desktop is running\n"
        "  3. Run: which docker (should show the docker path)\n"
        "  4. Add to PATH if needed: export PATH=\"/usr/local/bin:$PATH\""
    )
    raise RuntimeError(error_msg)


class GitHubMCPClient:
    """
    Client for interacting with GitHub via MCP server running inside a container.

    Supports multiple container runtimes:
    - Docker Desktop
    - OrbStack (macOS Docker alternative)
    - Podman Desktop
    - Rancher Desktop
    - Native Podman
    - containerd with nerdctl
    """

    def __init__(self, github_token: Optional[str] = None, toolsets: Optional[str] = None,
                 container_runtime: Optional[str] = None):
        """
        Initialize GitHub MCP client.

        Args:
            github_token: GitHub Personal Access Token (falls back to env var)
            toolsets: Comma-separated list of toolsets to enable (e.g., "repos,issues,pull_requests")
                     Use "all" to enable all toolsets. Defaults to basic toolsets.
            container_runtime: Container runtime to use (docker, podman, nerdctl)
                              If not specified, auto-detects available runtime.
                              Works with Docker Desktop, OrbStack, Podman, etc.
        """
        self.github_token = github_token or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
        if not self.github_token:
            raise ValueError(
                "GitHub token not provided. Set GITHUB_PERSONAL_ACCESS_TOKEN "
                "environment variable or pass token to constructor."
            )

        # Auto-detect or use specified container runtime
        # Works with Docker Desktop, OrbStack, Podman, Rancher Desktop, etc.
        if container_runtime:
            self.container_runtime = container_runtime
        else:
            self.container_runtime = _detect_container_runtime()

        # Build container arguments
        # Based on: https://github.com/github/github-mcp-server
        container_args = [
            "run",
            "-i",
            "--rm",
            "-e", f"GITHUB_PERSONAL_ACCESS_TOKEN={self.github_token}",
        ]

        # Add optional toolsets configuration
        if toolsets:
            container_args.extend(["-e", f"GITHUB_TOOLSETS={toolsets}"])

        container_args.extend([
            "ghcr.io/github/github-mcp-server",
            "stdio"  # Run in stdio mode for MCP communication
        ])

        self.server_params = StdioServerParameters(
            command=self.container_runtime,
            args=container_args,
            env={
                "GITHUB_PERSONAL_ACCESS_TOKEN": self.github_token
            }
        )

        self.session: Optional[ClientSession] = None
        self.stdio_context = None
        self.stdio = None
        self.write = None

    async def __aenter__(self):
        """Async context manager entry."""
        try:
            self.stdio_context = stdio_client(self.server_params)
            transport = await self.stdio_context.__aenter__()
            self.stdio, self.write = transport

            self.session = ClientSession(self.stdio, self.write)
            await self.session.__aenter__()
            await self.session.initialize()

            return self

        except Exception as e:
            await self._cleanup()
            raise RuntimeError(f"Failed to initialize GitHub MCP client: {str(e)}")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._cleanup()
        return False

    async def _cleanup(self):
        """Clean up resources."""
        if self.session:
            try:
                await self.session.__aexit__(None, None, None)
            except Exception:
                pass
            self.session = None

        if self.stdio_context:
            try:
                await self.stdio_context.__aexit__(None, None, None)
            except Exception:
                pass
            self.stdio_context = None

        self.stdio = None
        self.write = None

    async def list_available_tools(self) -> list:
        """
        List all available tools from the GitHub MCP server.

        Returns:
            List of available tool names
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        tools_result = await self.session.list_tools()
        return [tool.name for tool in tools_result.tools]

    async def create_pull_request(
        self,
        repo_owner: str,
        repo_name: str,
        title: str,
        body: str,
        head: str,
        base: str = "main"
    ) -> Dict[str, Any]:
        """
        Create a GitHub Pull Request using MCP.

        Args:
            repo_owner: Repository owner (username or organization)
            repo_name: Repository name
            title: PR title
            body: PR description
            head: Source branch
            base: Target branch (default: main)

        Returns:
            Dictionary with PR details or error
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        try:
            result = await self.session.call_tool(
                "create_pull_request",
                arguments={
                    "owner": repo_owner,
                    "repo": repo_name,
                    "title": title,
                    "body": body,
                    "head": head,
                    "base": base
                }
            )

            if result.content and len(result.content) > 0:
                response_text = (
                    result.content[0].text if hasattr(result.content[0], 'text')
                    else str(result.content[0])
                )

                try:
                    pr_data = json.loads(response_text)
                except json.JSONDecodeError:
                    return {"status": "success", "message": response_text, "raw_response": response_text}

                return {
                    "status": "success",
                    "pr_url": pr_data.get("html_url", ""),
                    "pr_number": pr_data.get("number", ""),
                    "message": f"Successfully created PR #{pr_data.get('number', '')}",
                    "data": pr_data
                }

            return {"status": "error", "message": "No response from MCP server"}

        except Exception as e:
            return {"status": "error", "message": f"Error creating PR via MCP: {str(e)}"}

    async def create_issue(
        self,
        repo_owner: str,
        repo_name: str,
        title: str,
        body: str,
        labels: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Create a GitHub Issue using MCP.

        Args:
            repo_owner: Repository owner (username or organization)
            repo_name: Repository name
            title: Issue title
            body: Issue description
            labels: List of label names (default: ["dependencies"])

        Returns:
            Dictionary with Issue details or error
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        if labels is None:
            labels = ["dependencies"]

        try:
            # Use issue_write tool (actual tool name in GitHub MCP)
            result = await self.session.call_tool(
                "issue_write",
                arguments={
                    "owner": repo_owner,
                    "repo": repo_name,
                    "title": title,
                    "body": body,
                    "labels": labels
                }
            )

            if result.content and len(result.content) > 0:
                response_text = (
                    result.content[0].text if hasattr(result.content[0], 'text')
                    else str(result.content[0])
                )

                try:
                    issue_data = json.loads(response_text)
                except json.JSONDecodeError:
                    return {"status": "success", "message": response_text, "raw_response": response_text}

                return {
                    "status": "success",
                    "issue_url": issue_data.get("html_url", ""),
                    "issue_number": issue_data.get("number", ""),
                    "message": f"Successfully created issue #{issue_data.get('number', '')}",
                    "data": issue_data
                }

            return {"status": "error", "message": "No response from MCP server"}

        except Exception as e:
            return {"status": "error", "message": f"Error creating issue via MCP: {str(e)}"}

    async def get_repository_info(self, repo_owner: str, repo_name: str) -> Dict[str, Any]:
        """
        Get repository information using MCP.

        Args:
            repo_owner: Repository owner
            repo_name: Repository name

        Returns:
            Dictionary with repository details or error
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        try:
            # Use search_repositories to find the repo
            result = await self.session.call_tool(
                "search_repositories",
                arguments={
                    "query": f"repo:{repo_owner}/{repo_name}"
                }
            )

            if result.content and len(result.content) > 0:
                response = result.content[0].text
                repo_data = json.loads(response) if isinstance(response, str) else response

                return {
                    "status": "success",
                    "data": repo_data
                }
            else:
                return {
                    "status": "error",
                    "message": "No response from MCP server"
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error getting repository info: {str(e)}"
            }


# Synchronous wrapper functions for compatibility with existing code
def create_pr_sync(
    repo_name: str,
    branch_name: str,
    title: str,
    body: str,
    base_branch: str = "main",
    github_token: Optional[str] = None
) -> Dict:
    """
    Synchronous wrapper for creating a PR via GitHub MCP.

    Args:
        repo_name: Repository in owner/repo format
        branch_name: Source branch for the PR
        title: PR title
        body: PR description
        base_branch: Target branch (default: main)
        github_token: GitHub token (optional, uses env var if not provided)

    Returns:
        Dictionary with PR URL or error
    """
    import asyncio
    import threading

    # Parse repo_name
    parts = repo_name.split("/")
    if len(parts) != 2:
        return {
            "status": "error",
            "message": f"Invalid repo_name format. Expected 'owner/repo', got '{repo_name}'"
        }

    owner, repo = parts

    async def _create_pr():
        async with GitHubMCPClient(github_token) as client:
            return await client.create_pull_request(
                repo_owner=owner,
                repo_name=repo,
                title=title,
                body=body,
                head=branch_name,
                base=base_branch
            )

    try:
        # Get or create event loop for this thread
        loop = _get_event_loop()
        return loop.run_until_complete(_create_pr())
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error in MCP client: {str(e)}"
        }


def create_issue_sync(
    repo_name: str,
    title: str,
    body: str,
    labels: Optional[str] = "dependencies",
    github_token: Optional[str] = None
) -> Dict:
    """
    Synchronous wrapper for creating an issue via GitHub MCP.

    Args:
        repo_name: Repository in owner/repo format
        title: Issue title
        body: Issue description
        labels: Comma-separated labels or single label (default: dependencies)
        github_token: GitHub token (optional, uses env var if not provided)

    Returns:
        Dictionary with Issue URL or error
    """
    import asyncio
    import threading

    # Parse repo_name
    parts = repo_name.split("/")
    if len(parts) != 2:
        return {
            "status": "error",
            "message": f"Invalid repo_name format. Expected 'owner/repo', got '{repo_name}'"
        }

    owner, repo = parts

    # Parse labels
    label_list = labels.split(",") if labels else ["dependencies"]
    label_list = [label.strip() for label in label_list]

    async def _create_issue():
        async with GitHubMCPClient(github_token) as client:
            return await client.create_issue(
                repo_owner=owner,
                repo_name=repo,
                title=title,
                body=body,
                labels=label_list
            )

    try:
        # Get or create event loop for this thread
        loop = _get_event_loop()
        return loop.run_until_complete(_create_issue())
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error in MCP client: {str(e)}"
        }


# CLI testing
if __name__ == "__main__":
    import asyncio

    async def test_connection():
        """Test GitHub MCP connection and list available tools."""
        try:
            async with GitHubMCPClient() as client:
                print("✅ Successfully connected to GitHub MCP server")
                print("\n📋 Available tools:")
                tools = await client.list_available_tools()
                for tool in tools:
                    print(f"  - {tool}")
        except Exception as e:
            print(f"❌ Error connecting to GitHub MCP: {e}")

    print("Testing GitHub MCP connection...")
    asyncio.run(test_connection())
