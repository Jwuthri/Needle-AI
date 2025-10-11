#!/bin/bash
set -e

echo "🔧 Setting up pre-commit hooks for NeedleAi..."

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "📦 Installing pre-commit..."
    pip install pre-commit
fi

# Install the git hooks
echo "⚙️  Installing pre-commit git hooks..."
pre-commit install

# Install commit-msg hook for conventional commits
pre-commit install --hook-type commit-msg

# Run hooks against all files to ensure everything works
echo "🧪 Running pre-commit against all files..."
pre-commit run --all-files || {
    echo "⚠️  Some pre-commit checks failed. Please fix the issues and run 'pre-commit run --all-files' again."
    echo "    Common fixes:"
    echo "    - Format Python code: cd backend && poetry run black ."
    echo "    - Sort imports: cd backend && poetry run isort ."
    echo "    - Format frontend: cd frontend && npm run format"
    exit 1
}

echo "✅ Pre-commit hooks are installed and working!"
echo "   Hooks will now run automatically on every commit."
echo ""
echo "💡 Useful commands:"
echo "   - Skip hooks: git commit --no-verify"
echo "   - Run manually: pre-commit run --all-files"
echo "   - Update hooks: pre-commit autoupdate"
