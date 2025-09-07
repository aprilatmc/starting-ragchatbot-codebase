#!/bin/bash

# Code formatting script for the RAG chatbot project
# This script formats all Python code using black and isort

set -e

echo "🎨 Formatting Python code..."

echo "📦 Running isort to organize imports..."
uv run isort backend/ main.py

echo "⚫ Running black to format code..."
uv run black backend/ main.py

echo "✅ Code formatting complete!"