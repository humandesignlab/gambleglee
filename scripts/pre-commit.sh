#!/bin/bash

# Pre-commit hook for GambleGlee
# This hook runs formatting and linting checks before allowing commits
# Auto-fixes formatting issues to match CI expectations

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

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    echo "🔧 Activating virtual environment..."
    source .venv/bin/activate
else
    echo "⚠️  No virtual environment found, using system Python"
fi

# Ensure we're using the exact same versions as CI
echo "🔧 Ensuring CI-compatible tool versions..."
pip install -q black==23.11.0 isort==5.12.0 flake8==6.1.0 mypy==1.7.1

# Auto-fix Black formatting (always run to ensure CI compatibility)
echo "🎨 Applying Black formatting..."
python -m black app/

# Auto-fix isort import sorting (always run to ensure CI compatibility)
echo "📦 Applying isort import sorting..."
python -m isort app/

# Check flake8 linting (critical errors only)
echo "🔍 Running flake8 linting..."
if ! python -m flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics > /dev/null 2>&1; then
    echo "❌ flake8 linting failed. Please fix the critical issues above."
    python -m flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics
    exit 1
fi

# Check mypy type checking (optional - can be skipped for now)
echo "🔍 Running mypy type checking..."
if ! python -m mypy app/ --ignore-missing-imports > /dev/null 2>&1; then
    echo "⚠️  mypy type checking found issues. Consider fixing them."
    echo "   (This won't block the commit, but should be addressed)"
    python -m mypy app/ --ignore-missing-imports | head -20
    echo "   ... (showing first 20 errors)"
fi

cd ..

# Frontend checks
echo "⚛️  Checking frontend formatting..."
cd frontend

# Auto-fix ESLint issues (always run to ensure CI compatibility)
echo "🎨 Applying ESLint fixes..."
npm run lint -- --fix

# Check if there are any remaining linting issues
if ! npm run lint > /dev/null 2>&1; then
    echo "❌ ESLint still has unfixable issues. Please fix them manually."
    npm run lint
    exit 1
fi

cd ..

# Infrastructure checks (if terraform is available)
echo "🏗️  Checking infrastructure formatting..."
if command -v terraform >/dev/null 2>&1; then
    if [ -d "infrastructure/terraform" ]; then
        cd infrastructure/terraform
        echo "🎨 Applying Terraform formatting..."
        terraform fmt -recursive
        cd ../..
    else
        echo "⚠️  Terraform directory not found, skipping..."
    fi
else
    echo "⚠️  Terraform not installed, skipping infrastructure checks"
fi

echo "✅ All pre-commit checks passed!"
echo "🚀 Ready to commit!"
echo ""
echo "💡 Tip: Your code has been automatically formatted to match CI expectations!"
