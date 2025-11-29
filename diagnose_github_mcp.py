#!/usr/bin/env python3
"""
Comprehensive GitHub MCP Diagnostic Script

This script performs thorough testing of GitHub MCP integration:
1. Checks all prerequisites (Docker, token, Python packages)
2. Tests Docker connectivity and image availability
3. Tests MCP server startup and connection
4. Tests basic MCP operations
5. Provides detailed diagnostics for troubleshooting
"""

import os
import sys
import json
import subprocess
import asyncio
from typing import Dict, Optional, Tuple


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}\n")


def print_test(name: str):
    """Print test name."""
    print(f"{Colors.BOLD}🧪 Testing: {name}{Colors.END}")


def print_success(message: str):
    """Print success message."""
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")


def print_error(message: str):
    """Print error message."""
    print(f"{Colors.RED}❌ {message}{Colors.END}")


def print_warning(message: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")


def print_info(message: str):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")


def run_command(cmd: list, capture_output=True, timeout=30) -> Tuple[int, str, str]:
    """
    Run a shell command and return exit code, stdout, stderr.

    Args:
        cmd: Command and arguments as list
        capture_output: Whether to capture output
        timeout: Command timeout in seconds

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout} seconds"
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"
    except Exception as e:
        return -1, "", str(e)


def check_python_version() -> bool:
    """Check if Python version is compatible."""
    print_test("Python version")

    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"

    if version.major >= 3 and version.minor >= 8:
        print_success(f"Python {version_str} (compatible)")
        return True
    else:
        print_error(f"Python {version_str} (requires Python 3.8+)")
        return False


def check_docker_installed() -> bool:
    """Check if Docker is installed."""
    print_test("Docker installation")

    exit_code, stdout, stderr = run_command(["docker", "--version"])

    if exit_code == 0:
        print_success(f"Docker installed: {stdout.strip()}")
        return True
    else:
        print_error("Docker not installed or not in PATH")
        print_info("Install Docker: https://docs.docker.com/get-docker/")
        return False


def check_docker_running() -> bool:
    """Check if Docker daemon is running."""
    print_test("Docker daemon status")

    exit_code, stdout, stderr = run_command(["docker", "ps"], timeout=10)

    if exit_code == 0:
        print_success("Docker daemon is running")
        return True
    else:
        print_error("Docker daemon is not running")
        print_info("Start Docker Desktop or run: sudo systemctl start docker")
        if stderr:
            print(f"   Error: {stderr.strip()}")
        return False


def check_docker_image() -> bool:
    """Check if GitHub MCP Docker image is available."""
    print_test("GitHub MCP Docker image")

    # Check if image exists locally
    exit_code, stdout, stderr = run_command(
        ["docker", "images", "ghcr.io/github/github-mcp-server", "--format", "{{.Repository}}:{{.Tag}}"]
    )

    if exit_code == 0 and stdout.strip():
        print_success(f"Image available locally: {stdout.strip()}")
        return True
    else:
        print_warning("Image not found locally")
        print_info("Attempting to pull image...")

        # Try to pull the image
        exit_code, stdout, stderr = run_command(
            ["docker", "pull", "ghcr.io/github/github-mcp-server"],
            timeout=120
        )

        if exit_code == 0:
            print_success("Successfully pulled GitHub MCP image")
            return True
        else:
            print_error("Failed to pull Docker image")
            if stderr:
                print(f"   Error: {stderr.strip()}")
            return False


def check_github_token() -> Optional[str]:
    """Check if GitHub token is set."""
    print_test("GitHub Personal Access Token")

    token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")

    if token:
        masked_token = f"{token[:8]}...{token[-4:]}" if len(token) > 12 else "***"
        print_success(f"Token found: {masked_token}")
        print_info(f"Token length: {len(token)} characters")
        return token
    else:
        print_error("GITHUB_PERSONAL_ACCESS_TOKEN not set")
        print_info("Set token: export GITHUB_PERSONAL_ACCESS_TOKEN='your_token'")
        print_info("Create token: https://github.com/settings/tokens")
        return None


def check_python_packages() -> bool:
    """Check if required Python packages are installed."""
    print_test("Python packages")

    required_packages = {
        "mcp": "Model Context Protocol client",
        "anthropic": "Anthropic API client",
        "dotenv": "Environment variable loader"
    }

    all_installed = True

    for package, description in required_packages.items():
        try:
            if package == "dotenv":
                __import__("dotenv")
            else:
                __import__(package)
            print_success(f"{package}: installed ({description})")
        except ImportError:
            print_error(f"{package}: NOT installed ({description})")
            all_installed = False

    if not all_installed:
        print_info("Install packages: pip install -r requirements.txt")

    return all_installed


def test_docker_run() -> bool:
    """Test running a simple Docker container."""
    print_test("Docker container execution")

    exit_code, stdout, stderr = run_command(
        ["docker", "run", "--rm", "alpine", "echo", "Docker works!"],
        timeout=30
    )

    if exit_code == 0 and "Docker works!" in stdout:
        print_success("Docker can run containers successfully")
        return True
    else:
        print_error("Failed to run Docker container")
        if stderr:
            print(f"   Error: {stderr.strip()}")
        return False


async def test_mcp_connection(token: str) -> bool:
    """Test MCP client connection to GitHub MCP server."""
    print_test("MCP client connection")

    try:
        from github_mcp_client import GitHubMCPClient

        print_info("Initializing MCP client...")

        async with GitHubMCPClient(token) as client:
            print_success("Successfully connected to GitHub MCP server")

            # List available tools
            print_info("Fetching available tools...")
            tools = await client.list_available_tools()

            print_success(f"Found {len(tools)} available tools:")
            for tool in tools[:10]:  # Show first 10 tools
                print(f"   • {tool}")
            if len(tools) > 10:
                print(f"   ... and {len(tools) - 10} more")

            return True

    except ImportError as e:
        print_error(f"Failed to import github_mcp_client: {e}")
        return False
    except Exception as e:
        print_error(f"MCP connection failed: {str(e)}")

        # Provide detailed error information
        import traceback
        error_details = traceback.format_exc()
        print("\n" + Colors.YELLOW + "Detailed error trace:" + Colors.END)
        print(error_details)

        return False


async def test_mcp_tool_call(token: str) -> bool:
    """Test calling an MCP tool (non-destructive repository info query)."""
    print_test("MCP tool execution")

    try:
        from github_mcp_client import GitHubMCPClient

        # Use a well-known public repository for testing
        test_owner = "github"
        test_repo = "docs"

        print_info(f"Testing get_repository for {test_owner}/{test_repo}...")

        async with GitHubMCPClient(token) as client:
            result = await client.get_repository_info(test_owner, test_repo)

            if result.get("status") == "success":
                print_success("Successfully called MCP tool")

                repo_data = result.get("data", {})
                if repo_data:
                    print(f"   • Repository: {repo_data.get('full_name', 'N/A')}")
                    print(f"   • Description: {repo_data.get('description', 'N/A')[:60]}...")
                    print(f"   • Stars: {repo_data.get('stargazers_count', 'N/A')}")

                return True
            else:
                print_error(f"Tool call failed: {result.get('message', 'Unknown error')}")
                return False

    except Exception as e:
        print_error(f"Tool execution failed: {str(e)}")
        return False


async def run_all_tests():
    """Run all diagnostic tests."""
    print_header("GitHub MCP Integration Diagnostic Tool")

    results = {}

    # Prerequisites
    print_header("1. Prerequisites Check")
    results["python_version"] = check_python_version()
    results["docker_installed"] = check_docker_installed()
    results["docker_running"] = check_docker_running()
    results["python_packages"] = check_python_packages()

    token = check_github_token()
    results["github_token"] = token is not None

    # Docker tests
    if results["docker_installed"] and results["docker_running"]:
        print_header("2. Docker Functionality Tests")
        results["docker_run"] = test_docker_run()
        results["docker_image"] = check_docker_image()
    else:
        print_warning("Skipping Docker tests (Docker not available)")
        results["docker_run"] = False
        results["docker_image"] = False

    # MCP tests
    if all([results["python_packages"], results["github_token"],
            results["docker_installed"], results["docker_running"],
            results["docker_image"]]):
        print_header("3. MCP Integration Tests")
        results["mcp_connection"] = await test_mcp_connection(token)

        if results["mcp_connection"]:
            results["mcp_tool_call"] = await test_mcp_tool_call(token)
        else:
            print_warning("Skipping tool call test (connection failed)")
            results["mcp_tool_call"] = False
    else:
        print_warning("Skipping MCP tests (prerequisites not met)")
        results["mcp_connection"] = False
        results["mcp_tool_call"] = False

    # Summary
    print_header("Test Results Summary")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_test in results.items():
        status = f"{Colors.GREEN}PASS{Colors.END}" if passed_test else f"{Colors.RED}FAIL{Colors.END}"
        print(f"{test_name.replace('_', ' ').title()}: {status}")

    print(f"\n{Colors.BOLD}Overall: {passed}/{total} tests passed{Colors.END}")

    if passed == total:
        print_header("✅ All Tests Passed!")
        print_success("GitHub MCP integration is working correctly!")
    else:
        print_header("❌ Some Tests Failed")
        print_error("GitHub MCP integration has issues. Review the errors above.")

        # Provide troubleshooting suggestions
        print(f"\n{Colors.BOLD}Troubleshooting Suggestions:{Colors.END}")

        if not results["docker_installed"]:
            print("• Install Docker: https://docs.docker.com/get-docker/")

        if not results["docker_running"]:
            print("• Start Docker daemon or Docker Desktop")

        if not results["github_token"]:
            print("• Set GITHUB_PERSONAL_ACCESS_TOKEN environment variable")
            print("• Create token at: https://github.com/settings/tokens")

        if not results["python_packages"]:
            print("• Install Python packages: pip install -r requirements.txt")

        if not results["docker_image"]:
            print("• Manually pull image: docker pull ghcr.io/github/github-mcp-server")

        if results.get("docker_image") and not results.get("mcp_connection"):
            print("• Check Docker logs for MCP server errors")
            print("• Verify GitHub token has correct permissions (repo, workflow)")
            print("• Check network connectivity")

    return passed == total


def main():
    """Main entry point."""
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Test interrupted by user{Colors.END}")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n{Colors.RED}Unexpected error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
