#!/bin/bash
# Database setup script for NeedleAi
# Creates the database if it doesn't exist and runs migrations

set -e

echo "🗄️  NeedleAi Database Setup"
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Load environment variables if .env exists
if [ -f .env ]; then
    echo "📋 Loading environment variables from .env..."
    export $(grep -v '^#' .env | xargs)
elif [ -f ../.env ]; then
    echo "📋 Loading environment variables from ../.env..."
    export $(grep -v '^#' ../.env | xargs)
else
    echo -e "${YELLOW}⚠️  No .env file found, using default values${NC}"
fi

# Parse DATABASE_URL or use defaults
DATABASE_URL=${DATABASE_URL:-"postgresql://postgres:postgres@localhost:5432/needleai"}

# Extract connection details from DATABASE_URL
# Format: postgresql://user:password@host:port/dbname
if [[ $DATABASE_URL =~ postgresql://([^:]+):([^@]+)@([^:]+):([^/]+)/(.+) ]]; then
    DB_USER="${BASH_REMATCH[1]}"
    DB_PASSWORD="${BASH_REMATCH[2]}"
    DB_HOST="${BASH_REMATCH[3]}"
    DB_PORT="${BASH_REMATCH[4]}"
    DB_NAME="${BASH_REMATCH[5]}"
else
    echo -e "${RED}❌ Invalid DATABASE_URL format${NC}"
    echo "Expected format: postgresql://user:password@host:port/dbname"
    exit 1
fi

echo "Database configuration:"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  User: $DB_USER"
echo "  Database: $DB_NAME"
echo ""

# Function to check if PostgreSQL is accessible
check_postgres() {
    echo "🔍 Checking PostgreSQL connection..."
    if PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c '\q' 2>/dev/null; then
        echo -e "${GREEN}✅ PostgreSQL is accessible${NC}"
        return 0
    else
        echo -e "${RED}❌ Cannot connect to PostgreSQL${NC}"
        return 1
    fi
}

# Function to check if database exists
check_database() {
    if PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -lqt | cut -d \| -f 1 | grep -qw $DB_NAME; then
        return 0
    else
        return 1
    fi
}

# Function to create database
create_database() {
    echo "🏗️  Creating database '$DB_NAME'..."
    if PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "CREATE DATABASE $DB_NAME;" 2>/dev/null; then
        echo -e "${GREEN}✅ Database created successfully${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to create database${NC}"
        return 1
    fi
}

# Function to check if alembic is available
check_alembic() {
    if command -v alembic &> /dev/null; then
        return 0
    elif python -m alembic --help &> /dev/null 2>&1; then
        return 0
    else
        echo -e "${RED}❌ Alembic not found. Please install it:${NC}"
        echo "   pip install alembic"
        return 1
    fi
}

# Function to run migrations
run_migrations() {
    echo "🔄 Running Alembic migrations..."
    
    # Change to backend directory if not already there
    if [ -f "alembic.ini" ]; then
        ALEMBIC_DIR="."
    elif [ -f "../alembic.ini" ]; then
        ALEMBIC_DIR=".."
    elif [ -f "backend/alembic.ini" ]; then
        ALEMBIC_DIR="backend"
    else
        echo -e "${RED}❌ alembic.ini not found${NC}"
        return 1
    fi
    
    cd $ALEMBIC_DIR
    
    # Check current revision
    echo "📋 Current database revision:"
    if command -v alembic &> /dev/null; then
        alembic current || echo "  (No migrations applied yet)"
    else
        python -m alembic current || echo "  (No migrations applied yet)"
    fi
    
    echo ""
    echo "🔄 Applying migrations..."
    
    # Run migrations
    if command -v alembic &> /dev/null; then
        alembic upgrade head
    else
        python -m alembic upgrade head
    fi
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Migrations completed successfully${NC}"
        echo ""
        echo "📋 Current database revision after migration:"
        if command -v alembic &> /dev/null; then
            alembic current
        else
            python -m alembic current
        fi
        return 0
    else
        echo -e "${RED}❌ Migration failed${NC}"
        return 1
    fi
}

# Main execution
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 1: Check PostgreSQL connection
if ! check_postgres; then
    echo -e "${YELLOW}💡 Make sure PostgreSQL is running:${NC}"
    echo "   • Docker: docker-compose up -d db"
    echo "   • Local: brew services start postgresql (macOS)"
    echo "   • Local: sudo systemctl start postgresql (Linux)"
    exit 1
fi

echo ""

# Step 2: Check if database exists
if check_database; then
    echo -e "${GREEN}✅ Database '$DB_NAME' already exists${NC}"
else
    echo -e "${YELLOW}⚠️  Database '$DB_NAME' does not exist${NC}"
    if create_database; then
        echo ""
    else
        exit 1
    fi
fi

echo ""

# Step 3: Check Alembic
if ! check_alembic; then
    exit 1
fi

echo ""

# Step 4: Run migrations
if run_migrations; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${GREEN}🎉 Database setup completed successfully!${NC}"
    echo ""
    echo "📊 Database is ready at:"
    echo "   $DATABASE_URL"
    echo ""
    echo "💡 Next steps:"
    echo "   • Start the backend: ./scripts/start.sh"
    echo "   • View migrations: alembic history"
    echo "   • Create new migration: alembic revision -m \"description\""
else
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${RED}❌ Database setup failed${NC}"
    echo ""
    echo "💡 Troubleshooting:"
    echo "   • Check your DATABASE_URL in .env"
    echo "   • Ensure PostgreSQL is running"
    echo "   • Check migration files in alembic/versions/"
    exit 1
fi

