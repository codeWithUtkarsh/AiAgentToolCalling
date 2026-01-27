#!/usr/bin/env python3
"""
Tests for the github_mcp_client module.

Tests container runtime detection, GitHub MCP client initialization,
and synchronous wrapper functions.
"""

import os
import subprocess
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from github_mcp_client import (
    _find_command_path,
    _detect_container_runtime,
    GitHubMCPClient,
    create_pr_sync,
    create_issue_sync
)


class TestFindCommandPath:
    """Test cases for _find_command_path function."""

    def test_find_command_in_path(self):
        """Test finding command in system PATH."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/docker"

            result = _find_command_path("docker")

            assert result == "/usr/bin/docker"

    def test_find_command_in_common_paths(self):
        """Test finding command in common installation paths."""
        with patch("shutil.which") as mock_which, \
             patch("os.path.isfile") as mock_isfile, \
             patch("os.access") as mock_access:
            mock_which.return_value = None
            mock_isfile.side_effect = lambda p: p == "/opt/homebrew/bin/docker"
            mock_access.return_value = True

            result = _find_command_path("docker")

            assert result == "/opt/homebrew/bin/docker"

    def test_command_not_found(self):
        """Test when command is not found anywhere."""
        with patch("shutil.which") as mock_which, \
             patch("os.path.isfile") as mock_isfile:
            mock_which.return_value = None
            mock_isfile.return_value = False

            result = _find_command_path("nonexistent")

            assert result is None


class TestDetectContainerRuntime:
    """Test cases for _detect_container_runtime function."""

    @patch("github_mcp_client._find_command_path")
    @patch("github_mcp_client.subprocess.run")
    def test_detect_docker(self, mock_run, mock_find):
        """Test detection of docker runtime - always returns full path."""
        mock_find.return_value = "/usr/bin/docker"
        mock_run.return_value = MagicMock(returncode=0)

        result = _detect_container_runtime()

        # Now always returns full path for consistency and PyCharm debugger compatibility
        assert result == "/usr/bin/docker"

    @patch("github_mcp_client._find_command_path")
    @patch("github_mcp_client.subprocess.run")
    def test_detect_podman_when_docker_unavailable(self, mock_run, mock_find):
        """Test fallback to podman when docker is unavailable - returns full path."""
        def find_side_effect(cmd):
            if cmd == "docker":
                return None
            elif cmd == "podman":
                return "/usr/bin/podman"
            return None

        mock_find.side_effect = find_side_effect
        mock_run.return_value = MagicMock(returncode=0)

        result = _detect_container_runtime()

        # Now always returns full path
        assert result == "/usr/bin/podman"

    @patch("github_mcp_client._find_command_path")
    def test_no_runtime_available(self, mock_find):
        """Test error when no container runtime is available."""
        mock_find.return_value = None

        with pytest.raises(RuntimeError) as exc_info:
            _detect_container_runtime()

        assert "No container runtime found" in str(exc_info.value)

    @patch("github_mcp_client._find_command_path")
    @patch("github_mcp_client.subprocess.run")
    def test_returns_full_path_for_non_standard_location(self, mock_run, mock_find):
        """Test that full path is returned for non-standard locations."""
        mock_find.return_value = "/opt/homebrew/bin/docker"
        mock_run.return_value = MagicMock(returncode=0)

        result = _detect_container_runtime()

        assert result == "/opt/homebrew/bin/docker"


class TestGitHubMCPClient:
    """Test cases for GitHubMCPClient class."""

    def test_init_without_token_raises_error(self):
        """Test that initialization without token raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure GITHUB_PERSONAL_ACCESS_TOKEN is not set
            if "GITHUB_PERSONAL_ACCESS_TOKEN" in os.environ:
                del os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"]

            with pytest.raises(ValueError) as exc_info:
                GitHubMCPClient(github_token=None)

            assert "GitHub token not provided" in str(exc_info.value)

    @patch("github_mcp_client._detect_container_runtime")
    def test_init_with_token(self, mock_detect):
        """Test successful initialization with token."""
        mock_detect.return_value = "/usr/bin/docker"

        client = GitHubMCPClient(github_token="test_token")

        assert client.github_token == "test_token"
        assert client.container_runtime == "/usr/bin/docker"

    @patch("github_mcp_client._detect_container_runtime")
    def test_init_with_custom_runtime(self, mock_detect):
        """Test initialization with custom container runtime."""
        client = GitHubMCPClient(
            github_token="test_token",
            container_runtime="/custom/path/docker"
        )

        assert client.container_runtime == "/custom/path/docker"
        mock_detect.assert_not_called()

    @patch("github_mcp_client._detect_container_runtime")
    def test_init_with_toolsets(self, mock_detect):
        """Test initialization with toolsets configuration."""
        mock_detect.return_value = "/usr/bin/docker"

        client = GitHubMCPClient(
            github_token="test_token",
            toolsets="repos,issues,pull_requests"
        )

        # Verify toolsets are included in server params
        assert "-e" in client.server_params.args
        toolsets_idx = client.server_params.args.index("GITHUB_TOOLSETS=repos,issues,pull_requests")
        assert toolsets_idx > 0


class TestCreatePRSync:
    """Test cases for create_pr_sync function."""

    def test_invalid_repo_name_format(self):
        """Test error handling for invalid repo name format."""
        result = create_pr_sync(
            repo_name="invalid-format",
            branch_name="feature",
            title="Test",
            body="Test body"
        )

        assert result["status"] == "error"
        assert "Invalid repo_name format" in result["message"]

    @patch("github_mcp_client.GitHubMCPClient")
    @patch("github_mcp_client._get_event_loop")
    def test_create_pr_success(self, mock_loop, mock_client_class):
        """Test successful PR creation."""
        # Setup mocks
        mock_client = AsyncMock()
        mock_client.create_pull_request.return_value = {
            "status": "success",
            "pr_url": "https://github.com/test/repo/pull/1"
        }
        mock_client_class.return_value.__aenter__.return_value = mock_client

        mock_event_loop = MagicMock()
        mock_event_loop.run_until_complete.return_value = {
            "status": "success",
            "pr_url": "https://github.com/test/repo/pull/1"
        }
        mock_loop.return_value = mock_event_loop

        result = create_pr_sync(
            repo_name="test/repo",
            branch_name="feature-branch",
            title="Test PR",
            body="Test body"
        )

        assert result["status"] == "success"

    @patch("github_mcp_client._get_event_loop")
    def test_create_pr_exception(self, mock_loop):
        """Test error handling when PR creation fails."""
        mock_loop.return_value.run_until_complete.side_effect = Exception("Connection failed")

        result = create_pr_sync(
            repo_name="test/repo",
            branch_name="feature",
            title="Test",
            body="Test body"
        )

        assert result["status"] == "error"
        assert "Connection failed" in result["message"]


class TestCreateIssueSync:
    """Test cases for create_issue_sync function."""

    def test_invalid_repo_name_format(self):
        """Test error handling for invalid repo name format."""
        result = create_issue_sync(
            repo_name="invalid-format",
            title="Test Issue",
            body="Test body"
        )

        assert result["status"] == "error"
        assert "Invalid repo_name format" in result["message"]

    @patch("github_mcp_client._get_event_loop")
    def test_create_issue_success(self, mock_loop):
        """Test successful issue creation."""
        mock_loop.return_value.run_until_complete.return_value = {
            "status": "success",
            "issue_url": "https://github.com/test/repo/issues/1"
        }

        result = create_issue_sync(
            repo_name="test/repo",
            title="Test Issue",
            body="Test body"
        )

        assert result["status"] == "success"

    def test_labels_parsing(self):
        """Test that labels are parsed correctly."""
        with patch("github_mcp_client._get_event_loop") as mock_loop:
            mock_loop.return_value.run_until_complete.return_value = {"status": "success"}

            # This should not raise an error
            create_issue_sync(
                repo_name="test/repo",
                title="Test",
                body="Body",
                labels="bug,enhancement,dependencies"
            )


class TestEventLoop:
    """Test cases for event loop handling."""

    def test_get_event_loop_creates_new_loop(self):
        """Test that _get_event_loop creates a new loop when needed."""
        from github_mcp_client import _get_event_loop

        loop = _get_event_loop()

        assert loop is not None
        assert not loop.is_closed()


class TestServerParams:
    """Test cases for MCP server parameters."""

    @patch("github_mcp_client._detect_container_runtime")
    def test_server_params_structure(self, mock_detect):
        """Test that server params are structured correctly."""
        mock_detect.return_value = "/usr/bin/docker"

        client = GitHubMCPClient(github_token="test_token")

        # Verify command is container runtime (full path)
        assert client.server_params.command == "/usr/bin/docker"

        # Verify required args
        assert "run" in client.server_params.args
        assert "-i" in client.server_params.args
        assert "--rm" in client.server_params.args
        assert "ghcr.io/github/github-mcp-server" in client.server_params.args
        assert "stdio" in client.server_params.args

    @patch("github_mcp_client._detect_container_runtime")
    def test_token_passed_to_container(self, mock_detect):
        """Test that GitHub token is passed to container."""
        mock_detect.return_value = "/usr/bin/docker"

        client = GitHubMCPClient(github_token="my_secret_token")

        # Find the token in args
        token_env = None
        for i, arg in enumerate(client.server_params.args):
            if "GITHUB_PERSONAL_ACCESS_TOKEN=" in arg:
                token_env = arg
                break

        assert token_env is not None
        assert "my_secret_token" in token_env


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
