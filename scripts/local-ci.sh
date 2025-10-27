#!/bin/bash

# Local CI script for GambleGlee
# This script runs the same checks as CI locally
# Run this before pushing to catch issues early

set -e

echo "🚀 Running local CI checks (same as GitHub Actions)..."

# Check if we're in the right directory
if [ ! -f "backend/pyproject.toml" ] || [ ! -f "frontend/package.json" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

# Backend checks
print_status "Backend Tests"
cd backend

# Python formatting
print_status "Checking Python formatting..."
if ! python -m black --check app/ > /dev/null 2>&1; then
    print_warning "Black formatting issues found. Fixing..."
    python -m black app/
    print_success "Black formatting applied"
else
    print_success "Black formatting OK"
fi

# Import sorting
print_status "Checking import sorting..."
if ! python -m isort --check-only app/ > /dev/null 2>&1; then
    print_warning "Import sorting issues found. Fixing..."
    python -m isort app/
    print_success "Import sorting applied"
else
    print_success "Import sorting OK"
fi

# Linting
print_status "Running flake8 linting..."
if ! python -m flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics > /dev/null 2>&1; then
    print_error "flake8 linting failed"
    python -m flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics
    exit 1
else
    print_success "flake8 linting OK"
fi

# Type checking
print_status "Running mypy type checking..."
if ! python -m mypy app/ --ignore-missing-imports > /dev/null 2>&1; then
    print_error "mypy type checking failed"
    python -m mypy app/ --ignore-missing-imports
    exit 1
else
    print_success "mypy type checking OK"
fi

cd ..

# Frontend checks
print_status "Frontend Tests"
cd frontend

# ESLint
print_status "Running ESLint..."
if ! npm run lint > /dev/null 2>&1; then
    print_warning "ESLint issues found. Fixing..."
    npm run lint -- --fix
    print_success "ESLint fixes applied"
else
    print_success "ESLint OK"
fi

# TypeScript type checking
print_status "Running TypeScript type checking..."
if ! npm run type-check > /dev/null 2>&1; then
    print_error "TypeScript type checking failed"
    npm run type-check
    exit 1
else
    print_success "TypeScript type checking OK"
fi

# Unit tests
print_status "Running unit tests..."
if ! npm run test:unit > /dev/null 2>&1; then
    print_error "Unit tests failed"
    npm run test:unit
    exit 1
else
    print_success "Unit tests OK"
fi

cd ..

# Infrastructure checks (if terraform is available)
print_status "Infrastructure Tests"
if command -v terraform >/dev/null 2>&1; then
    print_status "Checking Terraform formatting..."
    if [ -d "infrastructure/terraform" ]; then
        cd infrastructure/terraform
        if ! terraform fmt -check > /dev/null 2>&1; then
            print_warning "Terraform formatting issues found. Fixing..."
            terraform fmt
            print_success "Terraform formatting applied"
        else
            print_success "Terraform formatting OK"
        fi
        cd ../..
    else
        print_warning "Terraform directory not found, skipping..."
    fi
else
    print_warning "Terraform not installed, skipping infrastructure checks"
fi

# Summary
echo ""
print_success "🎉 All local CI checks passed!"
print_status "You're ready to push to GitHub!"
echo ""
echo "Next steps:"
echo "1. git add -A"
echo "2. git commit -m 'Your commit message'"
echo "3. git push origin develop"
echo ""
