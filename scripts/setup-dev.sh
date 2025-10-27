#!/bin/bash

# Developer Setup Script for GambleGlee
# This script sets up the development environment for new developers
# Ensures all formatting tools are configured correctly

set -e

echo "🚀 Setting up GambleGlee development environment..."

# Check if we're in the right directory
if [ ! -f "backend/pyproject.toml" ] || [ ! -f "frontend/package.json" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Install VS Code extensions
echo "📦 Installing recommended VS Code extensions..."
if command -v code >/dev/null 2>&1; then
    # Python extensions
    code --install-extension ms-python.python
    code --install-extension ms-python.black-formatter
    code --install-extension ms-python.isort
    code --install-extension ms-python.flake8
    code --install-extension ms-python.mypy-type-checker
    
    # TypeScript/JavaScript extensions
    code --install-extension dbaeumer.vscode-eslint
    code --install-extension esbenp.prettier-vscode
    
    # Terraform extensions
    code --install-extension hashicorp.terraform
    
    # General extensions
    code --install-extension redhat.vscode-yaml
    code --install-extension eamodio.gitlens
    
    echo "✅ VS Code extensions installed"
else
    echo "⚠️  VS Code not found. Please install extensions manually from .vscode/extensions.json"
fi

# Set up Python environment
echo "🐍 Setting up Python environment..."
cd backend
if [ ! -d ".venv" ]; then
    python -m venv .venv
    echo "✅ Python virtual environment created"
fi

source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
echo "✅ Python dependencies installed"

# Set up Node.js environment
echo "⚛️  Setting up Node.js environment..."
cd ../frontend
npm install
echo "✅ Node.js dependencies installed"

# Set up pre-commit hook
echo "🔧 Setting up pre-commit hook..."
cd ..
if [ ! -f ".git/hooks/pre-commit" ]; then
    cp scripts/pre-commit.sh .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit
    echo "✅ Pre-commit hook installed"
else
    echo "⚠️  Pre-commit hook already exists"
fi

# Test formatting tools
echo "🧪 Testing formatting tools..."
cd backend
python -m black --version
python -m isort --version
python -m flake8 --version
python -m mypy --version
echo "✅ Python formatting tools verified"

cd ../frontend
npm run lint -- --version
echo "✅ Frontend formatting tools verified"

cd ..

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "📋 What's configured:"
echo "   ✅ VS Code extensions installed"
echo "   ✅ Python virtual environment created"
echo "   ✅ All dependencies installed"
echo "   ✅ Pre-commit hook installed"
echo "   ✅ Formatting tools verified"
echo ""
echo "💡 Tips:"
echo "   • Code will be automatically formatted on save"
echo "   • Pre-commit hook will ensure CI compatibility"
echo "   • Run 'npm run local-ci' to test locally before pushing"
echo ""
echo "🚀 Happy coding!"