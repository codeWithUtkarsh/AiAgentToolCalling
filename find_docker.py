#!/usr/bin/env python3
"""
Find Docker/OrbStack on macOS

This script helps diagnose where docker is installed on your Mac.
"""

import os
import subprocess
import shutil
import sys


def check_shell_path():
    """Check what the shell sees for docker."""
    print("=" * 60)
    print("Checking Shell Environment")
    print("=" * 60)

    shells = ['bash', 'zsh', 'sh']

    for shell in shells:
        try:
            result = subprocess.run(
                [shell, '-l', '-c', 'which docker'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                print(f"✅ {shell} (login shell) sees docker at: {result.stdout.strip()}")
            else:
                print(f"❌ {shell} cannot find docker")
        except Exception as e:
            print(f"⚠️  {shell}: {e}")

    print()


def check_python_path():
    """Check what Python sees."""
    print("=" * 60)
    print("Checking Python Environment")
    print("=" * 60)

    docker_path = shutil.which('docker')
    if docker_path:
        print(f"✅ Python's shutil.which() found docker at: {docker_path}")
    else:
        print("❌ Python's shutil.which() cannot find docker")

    print(f"\n📋 Python's PATH:")
    path_var = os.environ.get('PATH', '')
    for path in path_var.split(':'):
        print(f"   - {path}")

    print()


def check_common_locations():
    """Check common installation locations."""
    print("=" * 60)
    print("Checking Common Installation Locations")
    print("=" * 60)

    locations = [
        '/usr/local/bin/docker',
        '/opt/homebrew/bin/docker',
        '/usr/bin/docker',
        '/opt/local/bin/docker',
        '~/.orbstack/bin/docker',
        '/Applications/OrbStack.app/Contents/MacOS/docker',
        '/Applications/Docker.app/Contents/Resources/bin/docker',
    ]

    found_any = False

    for location in locations:
        expanded = os.path.expanduser(location)
        if os.path.isfile(expanded):
            is_executable = os.access(expanded, os.X_OK)
            status = "✅ Executable" if is_executable else "⚠️  Not executable"
            print(f"{status}: {expanded}")

            # Try to run it
            if is_executable:
                try:
                    result = subprocess.run(
                        [expanded, '--version'],
                        capture_output=True,
                        text=True,
                        timeout=3
                    )
                    if result.returncode == 0:
                        version = result.stdout.strip().split('\n')[0]
                        print(f"         Version: {version}")
                        found_any = True
                except Exception as e:
                    print(f"         Error running: {e}")
        else:
            print(f"❌ Not found: {location}")

    print()
    return found_any


def check_orbstack_app():
    """Check if OrbStack app is installed."""
    print("=" * 60)
    print("Checking OrbStack Installation")
    print("=" * 60)

    orbstack_app = "/Applications/OrbStack.app"

    if os.path.isdir(orbstack_app):
        print(f"✅ OrbStack app found at: {orbstack_app}")

        # Check if running
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'OrbStack'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("✅ OrbStack appears to be running")
            else:
                print("⚠️  OrbStack may not be running")
                print("   Try: Open /Applications/OrbStack.app")
        except Exception as e:
            print(f"⚠️  Could not check if running: {e}")
    else:
        print(f"❌ OrbStack app not found at: {orbstack_app}")

    print()


def suggest_fix(found_docker):
    """Suggest how to fix the issue."""
    print("=" * 60)
    print("Recommended Actions")
    print("=" * 60)

    if found_docker:
        print("✅ Docker/OrbStack is installed!")
        print()
        print("To make it accessible to Python, try one of these:")
        print()
        print("Option 1: Add to .zshrc (recommended for zsh):")
        print("  echo 'export PATH=\"/usr/local/bin:/opt/homebrew/bin:$PATH\"' >> ~/.zshrc")
        print("  source ~/.zshrc")
        print()
        print("Option 2: Add to .bash_profile (for bash):")
        print("  echo 'export PATH=\"/usr/local/bin:/opt/homebrew/bin:$PATH\"' >> ~/.bash_profile")
        print("  source ~/.bash_profile")
        print()
        print("Option 3: Create symlink:")
        print("  sudo ln -s $(which docker) /usr/local/bin/docker")
        print()
        print("After applying the fix, restart your terminal and try again!")
    else:
        print("❌ Docker/OrbStack not found in common locations")
        print()
        print("Please install one of:")
        print("  • OrbStack (recommended for Mac): https://orbstack.dev/")
        print("  • Docker Desktop: https://www.docker.com/products/docker-desktop")
        print()
        print("After installation:")
        print("  1. Open the application (OrbStack or Docker Desktop)")
        print("  2. Wait for it to fully start")
        print("  3. Open a NEW terminal window")
        print("  4. Run: docker --version")
        print("  5. Try the test again")

    print()


def main():
    """Main diagnostic function."""
    print()
    print("🔍 Docker/OrbStack Diagnostic Tool for macOS")
    print()

    check_orbstack_app()
    check_shell_path()
    check_python_path()
    found = check_common_locations()
    suggest_fix(found)

    print("=" * 60)
    print("Next Steps")
    print("=" * 60)
    print()
    print("1. If docker was found, apply the PATH fix above")
    print("2. Restart your terminal")
    print("3. Run: python3 quick_test_mcp.py")
    print()


if __name__ == "__main__":
    main()
