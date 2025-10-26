#!/bin/bash

# Pre-commit hook for GambleGlee
# This hook runs formatting and linting checks before allowing commits

set -e

echo "🔍 Running pre-commit checks..."

# Check if we're in the right directory
if [ ! -f "backend/pyproject.toml" ] || [ ! -f "frontend/package.json" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Backend checks
echo "🐍 Checking backend formatting..."
cd backend

# Check Black formatting
if ! python -m black --check app/ > /dev/null 2>&1; then
    echo "❌ Black formatting check failed. Running Black..."
    python -m black app/
    echo "✅ Black formatting applied"
fi

# Check isort import sorting
if ! python -m isort --check-only app/ > /dev/null 2>&1; then
    echo "❌ isort import sorting check failed. Running isort..."
    python -m isort app/
    echo "✅ isort import sorting applied"
fi

# Check flake8 linting
echo "🔍 Running flake8 linting..."
if ! python -m flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics > /dev/null 2>&1; then
    echo "❌ flake8 linting failed. Please fix the issues above."
    python -m flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics
    exit 1
fi

cd ..

# Frontend checks
echo "⚛️  Checking frontend formatting..."
cd frontend

# Check ESLint
if ! npm run lint > /dev/null 2>&1; then
    echo "❌ ESLint check failed. Running ESLint fix..."
    npm run lint -- --fix
    echo "✅ ESLint fixes applied"
fi

cd ..

echo "✅ All pre-commit checks passed!"
echo "🚀 Ready to commit!"
