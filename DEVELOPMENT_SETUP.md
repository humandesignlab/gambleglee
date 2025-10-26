# Development Setup Guide

This guide helps you set up automatic formatting and linting for GambleGlee development.

## Prerequisites

- Python 3.11+
- Node.js 20+
- VS Code (recommended)

## Automatic Formatting Setup

### 1. VS Code Configuration

The project includes `.vscode/settings.json` with automatic formatting on save:

- **Python**: Black formatting + isort import sorting
- **TypeScript/React**: ESLint formatting + import organization
- **Format on save**: Enabled for all supported file types

### 2. Pre-commit Hook

Run the pre-commit script before committing:

```bash
npm run pre-commit
```

This will:
- ✅ Check and fix Black formatting
- ✅ Check and fix isort import sorting  
- ✅ Run flake8 linting checks
- ✅ Run ESLint checks and fixes

### 3. Manual Formatting Commands

```bash
# Format all code
npm run format:all

# Format only backend
npm run format:backend

# Format only frontend  
npm run format:frontend

# Check formatting without fixing
npm run check:all
```

## Backend Formatting

### Tools Used
- **Black**: Code formatting (line length: 88)
- **isort**: Import sorting (Black-compatible profile)
- **flake8**: Linting (errors only: E9,F63,F7,F82)

### Configuration
- `backend/pyproject.toml`: Black and isort configuration
- Compatible with CI/CD pipeline expectations

### Manual Commands
```bash
cd backend

# Format code
python -m black app/
python -m isort app/

# Check formatting
python -m black --check app/
python -m isort --check-only app/

# Lint code
python -m flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics
```

## Frontend Formatting

### Tools Used
- **ESLint**: Linting and formatting
- **Prettier**: Code formatting (via ESLint)
- **TypeScript**: Type checking

### Configuration
- `frontend/.eslintrc.cjs`: ESLint configuration
- `frontend/package.json`: Scripts and dependencies

### Manual Commands
```bash
cd frontend

# Lint and fix
npm run lint -- --fix

# Check linting
npm run lint
```

## CI/CD Compatibility

The local formatting tools are configured to match the CI/CD pipeline expectations:

- ✅ Same Black version and configuration
- ✅ Same isort profile and settings
- ✅ Same flake8 error codes
- ✅ Same ESLint rules and configuration

## Troubleshooting

### Black vs isort conflicts
If you see conflicts between Black and isort:

1. Run isort first: `python -m isort app/`
2. Then run Black: `python -m black app/`
3. Or use the combined command: `npm run format:backend`

### VS Code not formatting on save
1. Ensure you have the Python and ESLint extensions installed
2. Check that `.vscode/settings.json` is in your project root
3. Reload VS Code window

### Pre-commit hook fails
1. Make sure the script is executable: `chmod +x scripts/pre-commit.sh`
2. Run manually: `./scripts/pre-commit.sh`
3. Fix any issues reported and try again

## Best Practices

1. **Always run pre-commit checks** before pushing code
2. **Use VS Code** for automatic formatting on save
3. **Fix linting issues** as you code, don't let them accumulate
4. **Keep formatting tools updated** to match CI/CD versions
5. **Test locally** before pushing to avoid CI failures

## IDE Integration

### VS Code Extensions (Recommended)
- Python
- ESLint
- Prettier
- TypeScript Importer
- GitLens

### Other IDEs
- **PyCharm**: Configure Black and isort as external tools
- **WebStorm**: Configure ESLint and Prettier
- **Vim/Neovim**: Use ALE or similar plugins

## Contributing

When contributing to GambleGlee:

1. Set up your development environment using this guide
2. Make your changes
3. Run `npm run pre-commit` before committing
4. Ensure all checks pass
5. Push your changes

This ensures consistent code quality and prevents CI/CD failures.
