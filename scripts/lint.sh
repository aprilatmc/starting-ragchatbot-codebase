#!/bin/bash

# Code linting script for the RAG chatbot project
# This script runs all quality checks: flake8, mypy, and formatting checks

set -e

echo "🔍 Running code quality checks..."

echo "📋 Checking code style with flake8..."
uv run flake8 backend/ main.py --max-line-length=88 --extend-ignore=E203,W503

echo "🔬 Running type checking with mypy..."
uv run mypy backend/ main.py

echo "📦 Checking import formatting with isort..."
uv run isort --check-only --diff backend/ main.py

echo "⚫ Checking code formatting with black..."
uv run black --check --diff backend/ main.py

echo "✅ All quality checks passed!"