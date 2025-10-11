#!/bin/bash
# Deploy script for NeedleAi Backend

set -e

echo "🚀 NeedleAi Backend Deployment"
echo "==================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-production}
BACKUP=${2:-true}

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Pre-deployment checks
perform_checks() {
    log_info "Performing pre-deployment checks..."

    # Check Docker
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running!"
    fi

    # Check environment variables for production
    if [ "$ENVIRONMENT" = "production" ]; then
        log_info "Checking production environment variables..."

        if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "your-secret-key-change-in-production" ]; then
            log_error "SECRET_KEY must be set for production!"
        fi

        

        if [ -z "$POSTGRES_PASSWORD" ]; then
            log_warning "POSTGRES_PASSWORD is not set, using default!"
        fi
    fi

    log_success "Pre-deployment checks completed!"
}

# Backup current deployment
backup_deployment() {
    if [ "$BACKUP" = "true" ]; then
        log_info "Creating backup..."

        BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"

        # Backup database
        
        if docker ps | grep -q "needleai_postgres"; then
            log_info "Backing up PostgreSQL database..."
            docker exec needleai_postgres pg_dump -U postgres needleai > "$BACKUP_DIR/database.sql"
        fi
        

        # Backup volumes
        log_info "Backing up Docker volumes..."
        docker run --rm -v needleai_redis_data:/data -v $(pwd)/$BACKUP_DIR:/backup alpine tar czf /backup/redis_data.tar.gz -C /data .

        log_success "Backup completed at $BACKUP_DIR"
    fi
}

# Deploy application
deploy_application() {
    log_info "Deploying NeedleAi Backend..."

    case $ENVIRONMENT in
        "production" | "prod")
            log_info "Deploying to production..."

            # Pull latest images
            log_info "Pulling latest Docker images..."
            docker-compose -f docker/docker-compose.yml pull

            # Build and deploy
            log_info "Building and starting services..."
            docker-compose -f docker/docker-compose.yml up --build -d --remove-orphans

            # Wait for services to be ready
            log_info "Waiting for services to be ready..."
            sleep 30

            # Health check
            max_attempts=30
            attempt=1

            while [ $attempt -le $max_attempts ]; do
                if curl -f -s http://localhost:8000/health > /dev/null; then
                    log_success "Application is healthy!"
                    break
                fi

                if [ $attempt -eq $max_attempts ]; then
                    log_error "Application failed to become healthy after $max_attempts attempts!"
                fi

                log_info "Attempt $attempt/$max_attempts - waiting for application to be ready..."
                sleep 10
                ((attempt++))
            done
            ;;

        "staging")
            log_info "Deploying to staging..."

            # Use development compose with production-like settings
            export ENVIRONMENT=staging
            export DEBUG=false
            export LOG_LEVEL=INFO

            docker-compose -f docker/docker-compose.dev.yml up --build -d --remove-orphans

            log_success "Staging deployment completed!"
            ;;

        *)
            log_error "Invalid environment: $ENVIRONMENT. Use 'production' or 'staging'."
            ;;
    esac
}

# Post-deployment tasks
post_deployment() {
    log_info "Running post-deployment tasks..."

    # Run database migrations (if applicable)
    
    log_info "Running database migrations..."
    # docker-compose exec backend alembic upgrade head
    

    # Clear caches
    log_info "Clearing application caches..."
    # Add cache clearing logic here if needed

    # Send deployment notification (webhook, Slack, etc.)
    if [ -n "$DEPLOYMENT_WEBHOOK_URL" ]; then
        log_info "Sending deployment notification..."
        curl -X POST "$DEPLOYMENT_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"text\":\"NeedleAi Backend deployed successfully to $ENVIRONMENT!\"}" \
            || log_warning "Failed to send deployment notification"
    fi

    log_success "Post-deployment tasks completed!"
}

# Rollback function
rollback() {
    log_warning "Rolling back deployment..."

    if [ -d "./backups" ]; then
        LATEST_BACKUP=$(ls -1t ./backups/ | head -n 1)
        if [ -n "$LATEST_BACKUP" ]; then
            log_info "Found backup: $LATEST_BACKUP"

            # Stop current services
            docker-compose -f docker/docker-compose.yml down

            # Restore database
            
            if [ -f "./backups/$LATEST_BACKUP/database.sql" ]; then
                log_info "Restoring database..."
                docker-compose -f docker/docker-compose.yml up -d postgres
                sleep 10
                docker exec -i needleai_postgres psql -U postgres needleai < "./backups/$LATEST_BACKUP/database.sql"
            fi
            

            # Restore volumes
            if [ -f "./backups/$LATEST_BACKUP/redis_data.tar.gz" ]; then
                log_info "Restoring Redis data..."
                docker run --rm -v needleai_redis_data:/data -v $(pwd)/backups/$LATEST_BACKUP:/backup alpine tar xzf /backup/redis_data.tar.gz -C /data
            fi

            log_success "Rollback completed!"
        else
            log_error "No backup found for rollback!"
        fi
    else
        log_error "Backup directory not found!"
    fi
}

# Main execution
case "${3:-deploy}" in
    "deploy")
        perform_checks
        backup_deployment
        deploy_application
        post_deployment

        log_success "🎉 Deployment completed successfully!"
        echo ""
        echo "📍 Application URLs:"
        echo "   🔗 Backend API: http://localhost:8000"
        echo "   📚 API Docs: http://localhost:8000/docs"
        echo "   🩺 Health Check: http://localhost:8000/health"
        echo ""
        echo "💡 Next steps:"
        echo "   • Run './scripts/status.sh' to check service status"
        echo "   • Monitor logs with 'docker-compose logs -f'"
        echo "   • Set up monitoring and alerting"
        ;;

    "rollback")
        rollback
        ;;

    *)
        echo "Usage: $0 [environment] [backup] [action]"
        echo ""
        echo "Arguments:"
        echo "  environment: production|staging (default: production)"
        echo "  backup:      true|false (default: true)"
        echo "  action:      deploy|rollback (default: deploy)"
        echo ""
        echo "Examples:"
        echo "  $0 production true deploy"
        echo "  $0 staging false deploy"
        echo "  $0 production true rollback"
        exit 1
        ;;
esac
