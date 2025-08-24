#!/bin/bash

# Freight Platform Deployment Script
# This script automates the deployment of the freight platform

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_TYPE="${1:-local}"
ENVIRONMENT="${2:-development}"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check kubectl for Kubernetes deployment
    if [[ "$DEPLOYMENT_TYPE" == "kubernetes" ]] && ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed. Please install kubectl for Kubernetes deployment."
        exit 1
    fi
    
    # Check Helm for Kubernetes deployment
    if [[ "$DEPLOYMENT_TYPE" == "kubernetes" ]] && ! command -v helm &> /dev/null; then
        log_error "Helm is not installed. Please install Helm for Kubernetes deployment."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

deploy_local() {
    log_info "Deploying freight platform locally with Docker Compose..."
    
    cd "$PROJECT_ROOT/deployment/docker"
    
    # Create necessary directories
    mkdir -p logs data/postgres data/redis data/minio data/redpanda
    
    # Set permissions
    chmod 755 logs data
    
    # Pull latest images
    log_info "Pulling latest Docker images..."
    docker-compose pull
    
    # Build custom images
    log_info "Building custom images..."
    docker-compose build
    
    # Start infrastructure services first
    log_info "Starting infrastructure services..."
    docker-compose up -d postgres redis minio redpanda
    
    # Wait for infrastructure to be ready
    log_info "Waiting for infrastructure services to be ready..."
    sleep 30
    
    # Check infrastructure health
    check_service_health "postgres" "5432"
    check_service_health "redis" "6379"
    check_service_health "minio" "9000"
    check_service_health "redpanda" "9092"
    
    # Start application services
    log_info "Starting application services..."
    docker-compose up -d quotation-service
    
    # Wait for application services
    sleep 20
    
    # Check application health
    check_application_health "http://localhost:8101/health" "quotation-service"
    
    log_success "Local deployment completed successfully!"
    log_info "Services are available at:"
    log_info "  - Quotation API: http://localhost:8101"
    log_info "  - MinIO Console: http://localhost:9001 (admin/admin)"
    log_info "  - API Documentation: http://localhost:8101/docs"
}

deploy_kubernetes() {
    log_info "Deploying freight platform to Kubernetes..."
    
    cd "$PROJECT_ROOT/deployment/k8s"
    
    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
        exit 1
    fi
    
    # Create namespace
    log_info "Creating namespace..."
    kubectl apply -f manifests/namespace.yaml
    
    # Deploy infrastructure using Helmfile
    log_info "Deploying infrastructure with Helmfile..."
    cd helmfile
    
    if command -v helmfile &> /dev/null; then
        helmfile sync --environment "$ENVIRONMENT"
    else
        log_warning "Helmfile not found, deploying infrastructure manually..."
        helm repo add bitnami https://charts.bitnami.com/bitnami
        helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
        helm repo update
        
        # Deploy PostgreSQL HA
        helm upgrade --install postgresql-ha bitnami/postgresql-ha \
            -n freight-platform \
            -f values/postgresql-ha.yaml
        
        # Deploy Redis
        helm upgrade --install redis-ha bitnami/redis \
            -n freight-platform \
            -f values/redis.yaml
    fi
    
    # Wait for infrastructure
    log_info "Waiting for infrastructure to be ready..."
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=postgresql-ha -n freight-platform --timeout=300s
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=redis -n freight-platform --timeout=300s
    
    # Deploy application services
    log_info "Deploying application services..."
    cd ../manifests
    kubectl apply -f config-secrets.yaml
    kubectl apply -f quotation-service.yaml
    kubectl apply -f ingress.yaml
    
    # Wait for application deployment
    kubectl wait --for=condition=available deployment/quotation-service -n freight-platform --timeout=300s
    
    log_success "Kubernetes deployment completed successfully!"
    
    # Get ingress information
    INGRESS_IP=$(kubectl get ingress freight-platform-ingress -n freight-platform -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
    if [[ "$INGRESS_IP" != "pending" ]]; then
        log_info "Services are available at: http://$INGRESS_IP"
    else
        log_info "Ingress IP is pending. Check 'kubectl get ingress -n freight-platform' for updates."
    fi
}

check_service_health() {
    local service_name="$1"
    local port="$2"
    local max_attempts=30
    local attempt=1
    
    log_info "Checking health of $service_name..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if nc -z localhost "$port" 2>/dev/null; then
            log_success "$service_name is healthy"
            return 0
        fi
        
        log_info "Waiting for $service_name... (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    log_error "$service_name failed to become healthy"
    return 1
}

check_application_health() {
    local health_url="$1"
    local service_name="$2"
    local max_attempts=30
    local attempt=1
    
    log_info "Checking health of $service_name..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f "$health_url" &>/dev/null; then
            log_success "$service_name is healthy"
            return 0
        fi
        
        log_info "Waiting for $service_name... (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    log_error "$service_name failed to become healthy"
    return 1
}

show_usage() {
    echo "Usage: $0 [DEPLOYMENT_TYPE] [ENVIRONMENT]"
    echo ""
    echo "DEPLOYMENT_TYPE:"
    echo "  local       Deploy using Docker Compose (default)"
    echo "  kubernetes  Deploy to Kubernetes cluster"
    echo ""
    echo "ENVIRONMENT:"
    echo "  development Development environment (default)"
    echo "  staging     Staging environment"
    echo "  production  Production environment"
    echo ""
    echo "Examples:"
    echo "  $0                          # Deploy locally for development"
    echo "  $0 local development        # Same as above"
    echo "  $0 kubernetes production    # Deploy to Kubernetes for production"
}

cleanup() {
    log_info "Cleaning up..."
    if [[ "$DEPLOYMENT_TYPE" == "local" ]]; then
        cd "$PROJECT_ROOT/deployment/docker"
        docker-compose down
    fi
}

# Main execution
main() {
    log_info "Starting Freight Platform deployment..."
    log_info "Deployment type: $DEPLOYMENT_TYPE"
    log_info "Environment: $ENVIRONMENT"
    
    # Trap cleanup on exit
    trap cleanup EXIT
    
    # Check prerequisites
    check_prerequisites
    
    # Deploy based on type
    case "$DEPLOYMENT_TYPE" in
        "local")
            deploy_local
            ;;
        "kubernetes")
            deploy_kubernetes
            ;;
        *)
            log_error "Invalid deployment type: $DEPLOYMENT_TYPE"
            show_usage
            exit 1
            ;;
    esac
    
    log_success "Deployment completed successfully!"
}

# Handle command line arguments
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    show_usage
    exit 0
fi

# Run main function
main "$@"

