#!/bin/bash

# Test script for the RAG chatbot project
# This script runs all tests and quality checks

set -e

echo "🧪 Running comprehensive test suite..."

echo "🔍 Running code quality checks..."
./scripts/lint.sh

echo "🧪 Running unit tests..."
cd backend && uv run pytest -v

echo "✅ All tests and quality checks passed!"