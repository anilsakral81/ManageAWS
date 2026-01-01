#!/bin/bash

# Alternative: Build Frontend Locally with Docker Buildx
# This uses QEMU emulation with optimized settings

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_header() {
    echo ""
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}  Build Frontend Locally (AMD64)${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo ""
}

print_header

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AWS_REGION="ap-south-1"
AWS_ACCOUNT_ID="122610483530"
ECR_REPO="tenant-management-frontend"
IMAGE_TAG="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:latest"

log_step "Setting up Docker Buildx for cross-platform builds..."

# Create buildx builder if it doesn't exist
if ! docker buildx inspect multiplatform &> /dev/null; then
    log_info "Creating new buildx builder..."
    docker buildx create --name multiplatform --use --driver docker-container --driver-opt network=host
else
    log_info "Using existing buildx builder..."
    docker buildx use multiplatform
fi

# Bootstrap the builder
docker buildx inspect --bootstrap

log_step "Logging into ECR..."
export AWS_PAGER=""
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

log_step "Building frontend image for AMD64..."
log_warn "This may take 5-10 minutes due to emulation..."

cd "$PROJECT_ROOT/frontend"

# Build with buildx for AMD64 only, with optimizations
docker buildx build \
    --platform linux/amd64 \
    --build-arg NODE_OPTIONS="--max-old-space-size=4096" \
    -t $IMAGE_TAG \
    --push \
    --progress=plain \
    .

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Build Complete! 🎉${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    log_info "Frontend image pushed to ECR:"
    echo "  $IMAGE_TAG"
    echo ""
    log_info "Deploy to EKS:"
    echo "  kubectl rollout restart deployment/frontend -n tenant-management"
    echo ""
else
    log_error "Build failed"
    exit 1
fi
