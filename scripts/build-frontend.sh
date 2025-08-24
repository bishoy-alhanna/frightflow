#!/bin/bash

# Frontend Build Script for FreightFlow Platform
# This script builds both customer portal and admin dashboard

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BUILD_ENV="${BUILD_ENV:-production}"

echo -e "${BLUE}🚀 FreightFlow Frontend Build Script${NC}"
echo -e "${BLUE}====================================${NC}"
echo "Project Root: $PROJECT_ROOT"
echo "Frontend Directory: $FRONTEND_DIR"
echo "Build Environment: $BUILD_ENV"
echo ""

# Function to print status
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

if ! command_exists node; then
    print_error "Node.js is not installed"
    exit 1
fi

if ! command_exists pnpm; then
    print_warning "pnpm not found, installing..."
    npm install -g pnpm
fi

NODE_VERSION=$(node --version)
PNPM_VERSION=$(pnpm --version)
print_status "Node.js version: $NODE_VERSION"
print_status "pnpm version: $PNPM_VERSION"
echo ""

# Build Customer Portal
echo -e "${BLUE}Building Customer Portal...${NC}"
cd "$FRONTEND_DIR/customer-portal"

if [ ! -f "package.json" ]; then
    print_error "package.json not found in customer-portal directory"
    exit 1
fi

print_status "Installing dependencies..."
pnpm install --frozen-lockfile

print_status "Building application..."
NODE_ENV=$BUILD_ENV pnpm run build

if [ -d "dist" ]; then
    print_status "Customer Portal build completed successfully"
    BUILD_SIZE=$(du -sh dist | cut -f1)
    print_status "Build size: $BUILD_SIZE"
else
    print_error "Customer Portal build failed - dist directory not found"
    exit 1
fi

echo ""

# Build Admin Dashboard
echo -e "${BLUE}Building Admin Dashboard...${NC}"
cd "$FRONTEND_DIR/admin-dashboard"

if [ ! -f "package.json" ]; then
    print_error "package.json not found in admin-dashboard directory"
    exit 1
fi

print_status "Installing dependencies..."
pnpm install --frozen-lockfile

print_status "Building application..."
NODE_ENV=$BUILD_ENV pnpm run build

if [ -d "dist" ]; then
    print_status "Admin Dashboard build completed successfully"
    BUILD_SIZE=$(du -sh dist | cut -f1)
    print_status "Build size: $BUILD_SIZE"
else
    print_error "Admin Dashboard build failed - dist directory not found"
    exit 1
fi

echo ""

# Build Docker images (optional)
if [ "$1" = "--docker" ]; then
    echo -e "${BLUE}Building Docker images...${NC}"
    
    cd "$FRONTEND_DIR/customer-portal"
    print_status "Building customer-portal Docker image..."
    docker build -t freight-platform/customer-portal:latest .
    
    cd "$FRONTEND_DIR/admin-dashboard"
    print_status "Building admin-dashboard Docker image..."
    docker build -t freight-platform/admin-dashboard:latest .
    
    print_status "Docker images built successfully"
    echo ""
fi

# Summary
echo -e "${GREEN}🎉 Frontend Build Complete!${NC}"
echo -e "${GREEN}=========================${NC}"
echo "✓ Customer Portal: Built and ready"
echo "✓ Admin Dashboard: Built and ready"

if [ "$1" = "--docker" ]; then
    echo "✓ Docker images: Built and tagged"
fi

echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Test the applications locally"
echo "2. Deploy using Docker Compose: cd deployment/docker && docker-compose up"
echo "3. Or deploy to Kubernetes: kubectl apply -f deployment/k8s/manifests/"
echo ""

print_status "All frontend applications built successfully!"

