#!/usr/bin/env python3
"""
Quick GitHub MCP Connection Test

A lightweight script to quickly verify GitHub MCP connectivity.
For comprehensive diagnostics, use diagnose_github_mcp.py instead.
"""

import os
import sys
import asyncio


async def quick_test():
    """Quick connection test."""
    print("🚀 Quick GitHub MCP Connection Test")
    print("=" * 50)

    # Check token
    token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not token:
        print("❌ GITHUB_PERSONAL_ACCESS_TOKEN not set")
        print("\nSet it with:")
        print("  export GITHUB_PERSONAL_ACCESS_TOKEN='your_token'")
        return False

    print(f"✅ Token found ({len(token)} chars)")

    # Try to import and connect
    try:
        from github_mcp_client import GitHubMCPClient

        print("✅ MCP client module loaded")
        print("\n🔌 Connecting to GitHub MCP server...")

        async with GitHubMCPClient(token) as client:
            print("✅ Connected to GitHub MCP server!")

            # List tools
            tools = await client.list_available_tools()
            print(f"✅ {len(tools)} tools available")

            # Show some tools
            print("\n📋 Available tools (first 5):")
            for tool in tools[:5]:
                print(f"   • {tool}")

            print("\n" + "=" * 50)
            print("✅ GitHub MCP is working correctly!")
            print("=" * 50)
            return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("\nInstall dependencies:")
        print("  pip install -r requirements.txt")
        return False

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nCommon issues:")
        print("  • Docker not running (start Docker Desktop)")
        print("  • Invalid GitHub token")
        print("  • Network connectivity issues")
        print("\nRun full diagnostics:")
        print("  python diagnose_github_mcp.py")
        return False


def main():
    """Main entry point."""
    try:
        success = asyncio.run(quick_test())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test cancelled")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
