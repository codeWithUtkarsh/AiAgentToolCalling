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
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Thread-local storage for event loops
_thread_local = threading.local()


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


class GitHubMCPClient:
    """Client for interacting with GitHub via MCP server running inside Docker."""

    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize GitHub MCP client.

        Args:
            github_token: GitHub Personal Access Token (falls back to env var)
        """
        self.github_token = github_token or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
        if not self.github_token:
            raise ValueError(
                "GitHub token not provided. Set GITHUB_PERSONAL_ACCESS_TOKEN "
                "environment variable or pass token to constructor."
            )

        # Updated: Use Docker to run the GitHub MCP Server
        self.server_params = StdioServerParameters(
            command="docker",
            args=[
                "run",
                "-i",
                "--rm",
                "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",  # Pass through env var
                "ghcr.io/github/github-mcp-server"
            ],
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
            result = await self.session.call_tool(
                "create_issue",
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
            result = await self.session.call_tool(
                "get_repository",
                arguments={
                    "owner": repo_owner,
                    "repo": repo_name
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
