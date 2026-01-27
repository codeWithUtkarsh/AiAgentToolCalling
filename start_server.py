#!/usr/bin/env python3
"""
Startup script for the Dependency Update Automation API.

This script:
1. Validates all prerequisites (Docker, API keys, tokens)
2. Sets up the GitHub MCP Docker image
3. Starts the FastAPI server

Usage:
    python start_server.py [--host HOST] [--port PORT] [--no-reload]

Examples:
    python start_server.py
    python start_server.py --port 8080
    python start_server.py --host 127.0.0.1 --port 8000 --no-reload
"""

import os
import sys
import argparse
import subprocess
from dotenv import load_dotenv


def check_python_version():
    """Verify Python version is 3.9+"""
    if sys.version_info < (3, 9):
        print("Error: Python 3.9 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"Python version: {sys.version.split()[0]}")
    return True


def check_docker():
    """Verify Docker is installed and running"""
    print("\nChecking Docker...")
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f"  Docker: {result.stdout.strip()}")

            # Check if Docker daemon is running
            info_result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if info_result.returncode == 0:
                print("  Docker daemon: Running")
                return True
            else:
                print("  Error: Docker daemon is not running")
                print("  Please start Docker Desktop or the Docker service")
                return False
        else:
            print("  Error: Docker is not installed")
            return False
    except FileNotFoundError:
        print("  Error: Docker is not installed")
        print("  Please install Docker: https://docs.docker.com/get-docker/")
        return False
    except subprocess.TimeoutExpired:
        print("  Error: Docker command timed out")
        return False


def check_environment_variables():
    """Verify required environment variables are set"""
    print("\nChecking environment variables...")

    # Load .env file
    load_dotenv()

    all_set = True

    # Check ANTHROPIC_API_KEY
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        print(f"  ANTHROPIC_API_KEY: Set ({anthropic_key[:8]}...)")
    else:
        print("  ANTHROPIC_API_KEY: NOT SET")
        print("    Set it in .env file or export ANTHROPIC_API_KEY=your-key")
        all_set = False

    # Check GITHUB_PERSONAL_ACCESS_TOKEN
    github_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if github_token:
        print(f"  GITHUB_PERSONAL_ACCESS_TOKEN: Set ({github_token[:8]}...)")
    else:
        print("  GITHUB_PERSONAL_ACCESS_TOKEN: NOT SET")
        print("    Export it: export GITHUB_PERSONAL_ACCESS_TOKEN=your-token")
        all_set = False

    return all_set


def check_dependencies():
    """Verify Python dependencies are installed"""
    print("\nChecking Python dependencies...")

    required = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "langchain",
        "langchain_anthropic",
        "mcp",
        "dotenv"
    ]

    missing = []
    for package in required:
        try:
            __import__(package)
            print(f"  {package}: OK")
        except ImportError:
            print(f"  {package}: MISSING")
            missing.append(package)

    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False

    return True


def pull_mcp_image():
    """Pull the GitHub MCP Docker image"""
    print("\nPulling GitHub MCP Docker image...")
    print("  This may take a few minutes on first run...")

    try:
        result = subprocess.run(
            ["docker", "pull", "ghcr.io/github/github-mcp-server"],
            capture_output=False,  # Show progress
            timeout=600  # 10 minutes
        )

        if result.returncode == 0:
            print("  GitHub MCP image: Ready")
            return True
        else:
            print("  Warning: Could not pull image (may use cached version)")
            return True  # Don't fail, might have cached image

    except subprocess.TimeoutExpired:
        print("  Error: Pulling image timed out")
        return False


def start_server(host: str, port: int, reload: bool):
    """Start the FastAPI server"""
    print(f"\n{'='*60}")
    print(f"Starting Dependency Update Automation API")
    print(f"{'='*60}")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Auto-reload: {'Enabled' if reload else 'Disabled'}")
    print(f"  API Docs: http://{host}:{port}/docs")
    print(f"  Health Check: http://{host}:{port}/health")
    print(f"{'='*60}\n")

    import uvicorn

    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Start the Dependency Update Automation API Server"
    )
    parser.add_argument(
        "--host",
        default=os.getenv("HOST", "0.0.0.0"),
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", 8000)),
        help="Port to bind to (default: 8000)"
    )
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Disable auto-reload (for production)"
    )
    parser.add_argument(
        "--skip-checks",
        action="store_true",
        help="Skip prerequisite checks"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Dependency Update Automation API - Startup")
    print("=" * 60)

    if not args.skip_checks:
        # Run all checks
        checks_passed = True

        if not check_python_version():
            checks_passed = False

        if not check_docker():
            checks_passed = False

        if not check_environment_variables():
            checks_passed = False

        if not check_dependencies():
            checks_passed = False

        if not checks_passed:
            print("\n" + "=" * 60)
            print("STARTUP FAILED: Please fix the issues above")
            print("=" * 60)
            print("\nQuick fix commands:")
            print("  1. Start Docker Desktop (or: sudo systemctl start docker)")
            print("  2. pip install -r requirements.txt")
            print("  3. cp .env.example .env && edit .env")
            print("  4. export GITHUB_PERSONAL_ACCESS_TOKEN=your-token")
            sys.exit(1)

        # Pull MCP image
        if not pull_mcp_image():
            print("\nWarning: Could not pull MCP image, continuing anyway...")

    # Start the server
    try:
        start_server(
            host=args.host,
            port=args.port,
            reload=not args.no_reload
        )
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
    except Exception as e:
        print(f"\nError starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
