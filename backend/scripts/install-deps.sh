#!/bin/bash
# Install all dependencies for NeedleAI backend

set -e

echo "🚀 Installing NeedleAI Backend Dependencies..."

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then 
    echo "❌ Python 3.11+ is required. Found: $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python version: $PYTHON_VERSION"

# Check if uv is installed (faster package manager)
if command -v uv &> /dev/null; then
    echo "📦 Using uv for faster installation..."
    INSTALLER="uv pip"
else
    echo "📦 Using pip..."
    INSTALLER="pip"
fi

# Install main dependencies
echo "📥 Installing main dependencies..."
$INSTALLER install -e .

# Install development dependencies
if [ "$1" == "--dev" ] || [ "$1" == "-d" ]; then
    echo "📥 Installing development dependencies..."
    $INSTALLER install -e ".[dev]"
fi

# Check if all critical packages are installed
echo ""
echo "🔍 Verifying critical packages..."

CRITICAL_PACKAGES=(
    "fastapi"
    "sqlalchemy"
    "stripe"
    "apify_client"
    "pinecone"
    "agno"
    "pandas"
    "celery"
    "redis"
)

MISSING=()
for package in "${CRITICAL_PACKAGES[@]}"; do
    if ! python3 -c "import $package" 2>/dev/null; then
        MISSING+=("$package")
    fi
done

if [ ${#MISSING[@]} -eq 0 ]; then
    echo "✅ All critical packages installed successfully!"
else
    echo "⚠️  Missing packages: ${MISSING[*]}"
    echo "Try running: pip install ${MISSING[*]}"
    exit 1
fi

echo ""
echo "✨ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Copy .env.template to .env and fill in your API keys"
echo "2. Run database migrations: alembic upgrade head"
echo "3. Start the server: uvicorn app.main:app --reload"
echo ""

