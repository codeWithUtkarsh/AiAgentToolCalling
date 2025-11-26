#!/usr/bin/env python3
"""
Automatic GitHub MCP Server Setup

This module automatically installs the GitHub MCP server if it's not found.
It checks for the binary, and if missing, clones and builds from source.
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path


MCP_SERVER_PATH = "/usr/local/bin/github-mcp-server"
GITHUB_MCP_REPO = "https://github.com/github/github-mcp-server.git"


def check_go_installed() -> bool:
    """Check if Go is installed and available."""
    try:
        result = subprocess.run(
            ["go", "version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_mcp_server_installed() -> bool:
    """Check if GitHub MCP server is already installed."""
    try:
        result = subprocess.run(
            [MCP_SERVER_PATH, "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def install_github_mcp_server() -> bool:
    """
    Automatically install GitHub MCP server.

    Returns:
        True if installation succeeded, False otherwise
    """
    print("  🔧 GitHub MCP server not found. Installing automatically...")
    print()

    # Check if Go is installed
    if not check_go_installed():
        print("  ❌ Go is not installed. Please install Go first:")
        print("     https://go.dev/doc/install")
        return False

    print("  ✅ Go found")

    # Create temporary directory for building
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # Clone the repository
            print("  📥 Cloning GitHub MCP server repository...")
            clone_result = subprocess.run(
                ["git", "clone", "--depth", "1", GITHUB_MCP_REPO, tmpdir],
                capture_output=True,
                text=True,
                timeout=60
            )

            if clone_result.returncode != 0:
                print(f"  ❌ Failed to clone repository: {clone_result.stderr}")
                return False

            print("  ✅ Repository cloned")

            # Build the binary
            print("  🔨 Building GitHub MCP server...")
            build_result = subprocess.run(
                ["go", "build", "-o", "github-mcp-server", "./cmd/github-mcp-server"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=120
            )

            if build_result.returncode != 0:
                print(f"  ❌ Failed to build: {build_result.stderr}")
                return False

            print("  ✅ Binary built successfully")

            # Check if we need sudo for installation
            install_dir = Path(MCP_SERVER_PATH).parent
            needs_sudo = not os.access(install_dir, os.W_OK)

            # Install the binary
            print(f"  📦 Installing to {MCP_SERVER_PATH}...")

            source_binary = os.path.join(tmpdir, "github-mcp-server")

            if needs_sudo:
                print("  🔐 Requesting sudo access to install to /usr/local/bin...")
                install_result = subprocess.run(
                    ["sudo", "cp", source_binary, MCP_SERVER_PATH],
                    timeout=60
                )

                if install_result.returncode == 0:
                    subprocess.run(
                        ["sudo", "chmod", "+x", MCP_SERVER_PATH],
                        timeout=10
                    )
            else:
                shutil.copy2(source_binary, MCP_SERVER_PATH)
                os.chmod(MCP_SERVER_PATH, 0o755)

            # Verify installation
            if check_mcp_server_installed():
                print("  ✅ GitHub MCP server installed successfully!")

                # Show version
                version_result = subprocess.run(
                    [MCP_SERVER_PATH, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if version_result.returncode == 0:
                    version = version_result.stdout.strip()
                    print(f"  📌 Version: {version}")

                return True
            else:
                print("  ❌ Installation verification failed")
                return False

        except subprocess.TimeoutExpired:
            print("  ❌ Installation timed out")
            return False
        except Exception as e:
            print(f"  ❌ Installation error: {str(e)}")
            return False


def ensure_github_mcp_server() -> bool:
    """
    Ensure GitHub MCP server is installed.
    If not found, attempt automatic installation.

    Returns:
        True if server is available, False otherwise
    """
    if check_mcp_server_installed():
        return True

    # Try to install
    return install_github_mcp_server()


def main():
    """Test the setup functionality."""
    print("="*60)
    print("GitHub MCP Server Setup Test")
    print("="*60)
    print()

    if check_mcp_server_installed():
        print("✅ GitHub MCP server is already installed")

        # Show version
        version_result = subprocess.run(
            [MCP_SERVER_PATH, "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if version_result.returncode == 0:
            print(f"📌 Version: {version_result.stdout.strip()}")
    else:
        print("❌ GitHub MCP server not found")
        print()

        if ensure_github_mcp_server():
            print()
            print("="*60)
            print("✅ Setup completed successfully!")
            print("="*60)
        else:
            print()
            print("="*60)
            print("❌ Setup failed")
            print("="*60)
            sys.exit(1)


if __name__ == "__main__":
    main()
