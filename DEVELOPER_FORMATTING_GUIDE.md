# 🚀 Developer Setup Guide

This guide ensures all developers have consistent formatting that matches CI expectations.

## 📋 Quick Setup

### For New Developers
```bash
# Run the setup script
npm run setup-dev
```

### For Existing Developers
```bash
# Update your environment
npm run setup-dev
```

## 🎨 Auto-Formatting Features

### ✅ **Format on Save** (VS Code)
- **Python**: Black + isort automatically applied
- **TypeScript/JavaScript**: ESLint fixes automatically applied
- **Terraform**: Terraform fmt automatically applied
- **JSON/YAML**: Prettier automatically applied

### ✅ **Pre-commit Hook**
- **Always runs** before every commit
- **Auto-fixes** formatting issues
- **Ensures CI compatibility**
- **Blocks commits** only for critical errors

### ✅ **Manual Formatting**
```bash
# Format all code to match CI
npm run format:ci

# Format specific components
npm run format:backend
npm run format:frontend

# Check formatting without fixing
npm run check:all
```

## 🔧 Configuration Details

### Python (Backend)
- **Black**: 88 character line length, Python 3.11 target
- **isort**: Black-compatible profile, parentheses style
- **flake8**: Critical errors only (E9,F63,F7,F82)
- **mypy**: Lenient with missing imports

### TypeScript/JavaScript (Frontend)
- **ESLint**: Recommended rules + custom overrides
- **Prettier**: Standard formatting
- **TypeScript**: Strict type checking

### Terraform (Infrastructure)
- **terraform fmt**: Standard formatting
- **Auto-applied** on save and pre-commit

## 🚨 Troubleshooting

### VS Code Not Formatting
1. Install recommended extensions: `code --install-extension ms-python.black-formatter`
2. Check Python interpreter: `Ctrl+Shift+P` → "Python: Select Interpreter"
3. Reload VS Code window

### Pre-commit Hook Not Working
```bash
# Reinstall the hook
cp scripts/pre-commit.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

### Formatting Conflicts
```bash
# Reset to CI-compatible formatting
npm run format:ci
git add -A
git commit -m "Fix formatting to match CI"
```

## 💡 Best Practices

### ✅ **Do This**
- Let VS Code format on save
- Run `npm run local-ci` before pushing
- Use `npm run format:ci` if unsure
- Commit frequently to catch issues early

### ❌ **Avoid This**
- Manual formatting that conflicts with tools
- Disabling format-on-save
- Skipping pre-commit hooks
- Pushing without local testing

## 🎯 **CI Compatibility**

Our setup ensures **100% compatibility** with CI:
- **Same tools**: Black, isort, flake8, ESLint, Terraform
- **Same versions**: Pinned in requirements
- **Same configuration**: pyproject.toml, .eslintrc.cjs
- **Same commands**: Exact same CLI arguments

## 🆘 **Need Help?**

- **Formatting issues**: Run `npm run format:ci`
- **CI failures**: Run `npm run local-ci`
- **Setup problems**: Run `npm run setup-dev`
- **Still stuck**: Check `.vscode/settings.json` configuration

---

**🎉 Happy coding with consistent formatting!**
