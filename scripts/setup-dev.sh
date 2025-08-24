#!/bin/bash

# Development Environment Setup Script
# This script sets up the development environment for the freight platform

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

check_python() {
    log_info "Checking Python installation..."
    
    if ! command -v python3.11 &> /dev/null; then
        if ! command -v python3 &> /dev/null; then
            log_error "Python 3 is not installed. Please install Python 3.11 or later."
            exit 1
        fi
        
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        if [[ $(echo "$PYTHON_VERSION < 3.11" | bc -l) -eq 1 ]]; then
            log_warning "Python version $PYTHON_VERSION detected. Python 3.11+ is recommended."
        fi
        PYTHON_CMD="python3"
    else
        PYTHON_CMD="python3.11"
    fi
    
    log_success "Python check passed: $($PYTHON_CMD --version)"
}

setup_virtual_environment() {
    log_info "Setting up virtual environment..."
    
    cd "$PROJECT_ROOT/services/quotation/quotation-service"
    
    if [[ ! -d "venv" ]]; then
        log_info "Creating virtual environment..."
        $PYTHON_CMD -m venv venv
    else
        log_info "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    log_info "Upgrading pip..."
    pip install --upgrade pip
    
    # Install dependencies
    log_info "Installing dependencies..."
    pip install -r requirements.txt
    pip install -r requirements-test.txt
    
    log_success "Virtual environment setup completed"
}

setup_pre_commit_hooks() {
    log_info "Setting up pre-commit hooks..."
    
    cd "$PROJECT_ROOT"
    
    # Install pre-commit if not already installed
    if ! command -v pre-commit &> /dev/null; then
        pip install pre-commit
    fi
    
    # Create pre-commit config if it doesn't exist
    if [[ ! -f ".pre-commit-config.yaml" ]]; then
        cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
  
  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
        language_version: python3
  
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]
  
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=88, --extend-ignore=E203]
EOF
    fi
    
    # Install pre-commit hooks
    pre-commit install
    
    log_success "Pre-commit hooks setup completed"
}

setup_database() {
    log_info "Setting up database..."
    
    cd "$PROJECT_ROOT/services/quotation/quotation-service"
    source venv/bin/activate
    
    # Check if PostgreSQL is running
    if ! nc -z localhost 5432 2>/dev/null; then
        log_warning "PostgreSQL is not running. Please start it with Docker Compose:"
        log_info "  cd deployment/docker && docker-compose up -d postgres"
        return 1
    fi
    
    # Initialize database
    log_info "Initializing database..."
    python src/init_db.py
    
    log_success "Database setup completed"
}

create_env_file() {
    log_info "Creating environment file..."
    
    cd "$PROJECT_ROOT/services/quotation/quotation-service"
    
    if [[ ! -f ".env" ]]; then
        cat > .env << 'EOF'
# Development Environment Configuration
FLASK_ENV=development
FLASK_DEBUG=true

# Database
DATABASE_URL=postgresql://freight:freight@localhost:5432/freight_db

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO
OBJECT_STORE_ENDPOINT=localhost:9000
OBJECT_STORE_ACCESS_KEY=minioadmin
OBJECT_STORE_SECRET_KEY=minioadmin
OBJECT_STORE_SECURE=false
OBJECT_STORE_BUCKET=freight-docs

# Kafka
KAFKA_BROKERS=localhost:9092

# Service
SERVICE_NAME=quotation-service
SERVICE_VERSION=1.0.0
LOG_LEVEL=DEBUG
AUTH_ENABLED=false

# Security (change in production)
SECRET_KEY=dev-secret-key-change-in-production
JWT_SECRET_KEY=dev-jwt-secret-key-change-in-production
EOF
        log_success "Environment file created"
    else
        log_info "Environment file already exists"
    fi
}

setup_ide_config() {
    log_info "Setting up IDE configuration..."
    
    cd "$PROJECT_ROOT"
    
    # VS Code settings
    mkdir -p .vscode
    
    if [[ ! -f ".vscode/settings.json" ]]; then
        cat > .vscode/settings.json << 'EOF'
{
    "python.defaultInterpreterPath": "./services/quotation/quotation-service/venv/bin/python",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "services/quotation/quotation-service/tests"
    ],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        "**/venv": true,
        "**/.pytest_cache": true,
        "**/htmlcov": true
    },
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
EOF
        log_success "VS Code settings created"
    fi
    
    # PyCharm settings
    if [[ ! -f ".idea/misc.xml" ]] && command -v pycharm &> /dev/null; then
        mkdir -p .idea
        cat > .idea/misc.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<project version="4">
  <component name="ProjectRootManager" version="2" project-jdk-name="Python 3.11 (freight-platform)" project-jdk-type="Python SDK" />
</project>
EOF
        log_info "PyCharm configuration created"
    fi
}

run_tests() {
    log_info "Running tests to verify setup..."
    
    cd "$PROJECT_ROOT/services/quotation/quotation-service"
    source venv/bin/activate
    
    # Run unit tests
    log_info "Running unit tests..."
    python -m pytest tests/unit/ -v --tb=short
    
    log_success "Tests passed successfully"
}

show_next_steps() {
    log_success "Development environment setup completed!"
    echo ""
    log_info "Next steps:"
    echo "1. Start infrastructure services:"
    echo "   cd deployment/docker && docker-compose up -d postgres redis minio redpanda"
    echo ""
    echo "2. Activate virtual environment:"
    echo "   cd services/quotation/quotation-service && source venv/bin/activate"
    echo ""
    echo "3. Start the quotation service:"
    echo "   python src/main.py"
    echo ""
    echo "4. Test the API:"
    echo "   curl http://localhost:8101/health"
    echo ""
    echo "5. View API documentation:"
    echo "   Open http://localhost:8101/docs in your browser"
    echo ""
    log_info "Happy coding! 🚀"
}

main() {
    log_info "Setting up Freight Platform development environment..."
    
    check_python
    setup_virtual_environment
    create_env_file
    setup_pre_commit_hooks
    setup_ide_config
    
    # Optional steps that might fail
    if setup_database; then
        run_tests
    else
        log_warning "Database setup skipped. Start infrastructure services first."
    fi
    
    show_next_steps
}

# Handle help
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    echo "Usage: $0"
    echo ""
    echo "This script sets up the development environment for the Freight Platform."
    echo "It will:"
    echo "  - Check Python installation"
    echo "  - Create virtual environment"
    echo "  - Install dependencies"
    echo "  - Set up pre-commit hooks"
    echo "  - Create environment files"
    echo "  - Configure IDE settings"
    echo "  - Initialize database (if available)"
    echo "  - Run tests"
    exit 0
fi

main "$@"

