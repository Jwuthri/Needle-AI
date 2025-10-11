#!/bin/bash

# Start NeedleAi backend with Celery workers
# This script starts the FastAPI server and all Celery workers in background

set -e

echo "🚀 Starting NeedleAi backend with Celery workers..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Stopping all services...${NC}"

    # Kill all background jobs
    jobs -p | xargs -r kill 2>/dev/null || true

    # Wait a bit for graceful shutdown
    sleep 2

    # Force kill any remaining processes
    pkill -f "uvicorn app.main" 2>/dev/null || true
    pkill -f "celery.*worker" 2>/dev/null || true
    pkill -f "celery.*flower" 2>/dev/null || true

    echo -e "${GREEN}All services stopped.${NC}"
    exit 0
}

# Set up trap to cleanup on script exit
trap cleanup INT TERM EXIT

# Create logs directory
mkdir -p logs

# Check if Redis is running
echo -e "${BLUE}Checking Redis connection...${NC}"
if ! redis-cli ping > /dev/null 2>&1; then
    echo -e "${RED}Error: Redis is not running. Please start Redis first.${NC}"
    echo -e "${YELLOW}You can start Redis with: redis-server${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Redis is running${NC}"

# Start services in background with logs
echo -e "${BLUE}Starting services...${NC}"

# Start FastAPI server
echo -e "${YELLOW}Starting FastAPI server...${NC}"
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info > logs/fastapi.log 2>&1 &
API_PID=$!

# Wait a moment for API to start
sleep 3

# Check if API started successfully
if ! kill -0 $API_PID 2>/dev/null; then
    echo -e "${RED}Failed to start FastAPI server. Check logs/fastapi.log${NC}"
    exit 1
fi
echo -e "${GREEN}✓ FastAPI server started (PID: $API_PID)${NC}"

# Start Celery workers
echo -e "${YELLOW}Starting Celery workers...${NC}"

# General tasks worker
celery -A app.core.celery_app:celery_app worker \
    --queues=general \
    --concurrency=2 \
    --loglevel=info \
    --hostname=general@%h > logs/celery-general.log 2>&1 &
GENERAL_PID=$!

# Chat tasks worker
celery -A app.core.celery_app:celery_app worker \
    --queues=chat \
    --concurrency=3 \
    --loglevel=info \
    --hostname=chat@%h > logs/celery-chat.log 2>&1 &
CHAT_PID=$!

# LLM tasks worker (CPU intensive)
celery -A app.core.celery_app:celery_app worker \
    --queues=llm \
    --concurrency=2 \
    --loglevel=info \
    --pool=prefork \
    --hostname=llm@%h > logs/celery-llm.log 2>&1 &
LLM_PID=$!

# Wait for workers to start
sleep 5

# Check if workers started successfully
failed_workers=()

if ! kill -0 $GENERAL_PID 2>/dev/null; then
    failed_workers+=("general")
fi

if ! kill -0 $CHAT_PID 2>/dev/null; then
    failed_workers+=("chat")
fi

if ! kill -0 $LLM_PID 2>/dev/null; then
    failed_workers+=("llm")
fi

if [ ${#failed_workers[@]} -gt 0 ]; then
    echo -e "${RED}Failed to start workers: ${failed_workers[*]}${NC}"
    echo -e "${YELLOW}Check log files in logs/ directory${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All Celery workers started successfully${NC}"
echo -e "  • General worker (PID: $GENERAL_PID)"
echo -e "  • Chat worker (PID: $CHAT_PID)"
echo -e "  • LLM worker (PID: $LLM_PID)"

# Optional: Start Celery Flower for monitoring
if [ "$1" = "--with-flower" ] || [ "$1" = "-f" ]; then
    echo -e "${YELLOW}Starting Celery Flower monitoring...${NC}"
    celery -A app.core.celery_app:celery_app flower \
        --port=5555 > logs/flower.log 2>&1 &
    FLOWER_PID=$!

    sleep 3

    if kill -0 $FLOWER_PID 2>/dev/null; then
        echo -e "${GREEN}✓ Celery Flower started (PID: $FLOWER_PID)${NC}"
        echo -e "${BLUE}  Monitor at: http://localhost:5555${NC}"
    else
        echo -e "${YELLOW}⚠ Flower failed to start, continuing without monitoring${NC}"
    fi
fi

# Show status
echo -e "\n${GREEN}🎉 All services are running!${NC}"
echo -e "${BLUE}Services:${NC}"
echo -e "  • FastAPI API: http://localhost:8000"
echo -e "  • API Docs: http://localhost:8000/docs"
echo -e "  • Celery Workers: 3 workers (general, chat, llm)"
if [ "$1" = "--with-flower" ] || [ "$1" = "-f" ]; then
    echo -e "  • Flower Monitor: http://localhost:5555"
fi

echo -e "\n${YELLOW}Log files:${NC}"
echo -e "  • FastAPI: logs/fastapi.log"
echo -e "  • General Worker: logs/celery-general.log"
echo -e "  • Chat Worker: logs/celery-chat.log"
echo -e "  • LLM Worker: logs/celery-llm.log"
if [ "$1" = "--with-flower" ] || [ "$1" = "-f" ]; then
    echo -e "  • Flower: logs/flower.log"
fi

echo -e "\n${BLUE}Press Ctrl+C to stop all services${NC}"

# Wait for user to stop
while true; do
    sleep 1
done
