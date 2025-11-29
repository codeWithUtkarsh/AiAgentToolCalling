#!/bin/bash
# Verification script to run on Mac where Docker is installed
# This tests the GitHub MCP integration with the stdio mode fix

set -e

echo "======================================================================"
echo "GitHub MCP Verification Script for Mac"
echo "======================================================================"
echo ""

# Check Docker
echo "🐳 Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found"
    exit 1
fi

DOCKER_VERSION=$(docker -v)
echo "✅ Docker installed: $DOCKER_VERSION"
echo ""

# Check Python
echo "🐍 Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "✅ Python installed: $PYTHON_VERSION"
echo ""

# Check if we're in the right directory
if [ ! -f "github_mcp_client.py" ]; then
    echo "❌ Error: github_mcp_client.py not found"
    echo "Please run this script from the AiAgentToolCalling directory"
    exit 1
fi

echo "✅ Found github_mcp_client.py"
echo ""

# Check GitHub token
echo "🔑 Checking GitHub token..."
if [ -z "$GITHUB_PERSONAL_ACCESS_TOKEN" ]; then
    echo "❌ GITHUB_PERSONAL_ACCESS_TOKEN not set"
    echo ""
    echo "Please set it:"
    echo "  export GITHUB_PERSONAL_ACCESS_TOKEN='your_token_here'"
    echo ""
    exit 1
fi

TOKEN_LENGTH=${#GITHUB_PERSONAL_ACCESS_TOKEN}
echo "✅ Token found ($TOKEN_LENGTH characters)"
echo ""

# Install dependencies
echo "📦 Installing Python dependencies..."
pip3 install -q -r requirements.txt 2>&1 | grep -v "already satisfied" || true
echo "✅ Dependencies installed"
echo ""

# Run quick test
echo "======================================================================"
echo "Running GitHub MCP Quick Test"
echo "======================================================================"
echo ""

python3 quick_test_mcp.py

EXIT_CODE=$?

echo ""
echo "======================================================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ SUCCESS! GitHub MCP is working correctly on your Mac!"
else
    echo "❌ Tests failed. Run diagnostics:"
    echo "   python3 diagnose_github_mcp.py"
fi
echo "======================================================================"

exit $EXIT_CODE
