#!/bin/bash

# Setup Local Kubernetes Cluster for Development
# This script helps set up a local K8s cluster using minikube or kind

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# Detect OS
OS=$(uname -s)
log_info "Detected OS: $OS"

# Check if running on macOS
if [ "$OS" != "Darwin" ]; then
    log_warn "This script is optimized for macOS. Proceed with caution on other systems."
fi

# Ask user which cluster type to use
echo ""
log_step "Choose Kubernetes cluster type:"
echo "1) Minikube (Recommended - Full-featured)"
echo "2) Kind (Lightweight)"
echo "3) Docker Desktop (If already installed)"
echo "4) Skip cluster setup"
read -p "Enter choice [1-4]: " CHOICE

case $CHOICE in
    1)
        CLUSTER_TYPE="minikube"
        ;;
    2)
        CLUSTER_TYPE="kind"
        ;;
    3)
        CLUSTER_TYPE="docker-desktop"
        ;;
    4)
        log_info "Skipping cluster setup"
        exit 0
        ;;
    *)
        log_error "Invalid choice"
        exit 1
        ;;
esac

install_prerequisites() {
    log_step "Checking and installing prerequisites..."
    
    # Check Homebrew
    if ! command -v brew &> /dev/null; then
        log_error "Homebrew not found. Please install from https://brew.sh"
        exit 1
    fi
    
    # Install kubectl
    if ! command -v kubectl &> /dev/null; then
        log_info "Installing kubectl..."
        brew install kubectl
    else
        log_info "kubectl already installed ✓"
    fi
    
    # Install Docker
    if ! command -v docker &> /dev/null; then
        log_info "Installing Docker..."
        brew install --cask docker
        log_warn "Please start Docker Desktop manually and come back"
        read -p "Press enter when Docker is running..."
    else
        log_info "Docker already installed ✓"
    fi
}

setup_minikube() {
    log_step "Setting up Minikube..."
    
    # Install minikube
    if ! command -v minikube &> /dev/null; then
        log_info "Installing minikube..."
        brew install minikube
    else
        log_info "Minikube already installed ✓"
    fi
    
    # Start minikube
    log_info "Starting minikube cluster..."
    minikube start --driver=docker --cpus=4 --memory=8192 --disk-size=20g
    
    # Enable addons
    log_info "Enabling minikube addons..."
    minikube addons enable ingress
    minikube addons enable metrics-server
    minikube addons enable dashboard
    
    log_info "Minikube setup complete ✓"
    log_info "Minikube IP: $(minikube ip)"
}

setup_kind() {
    log_step "Setting up Kind..."
    
    # Install kind
    if ! command -v kind &> /dev/null; then
        log_info "Installing kind..."
        brew install kind
    else
        log_info "Kind already installed ✓"
    fi
    
    # Create kind cluster with config
    log_info "Creating kind cluster..."
    cat <<EOF | kind create cluster --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: tenant-management
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
- role: worker
- role: worker
EOF
    
    # Install ingress-nginx
    log_info "Installing ingress-nginx..."
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
    
    # Wait for ingress to be ready
    log_info "Waiting for ingress controller..."
    kubectl wait --namespace ingress-nginx \
      --for=condition=ready pod \
      --selector=app.kubernetes.io/component=controller \
      --timeout=90s
    
    log_info "Kind setup complete ✓"
}

setup_docker_desktop() {
    log_step "Setting up Docker Desktop Kubernetes..."
    
    # Check if Docker Desktop is running
    if ! docker info &> /dev/null; then
        log_error "Docker Desktop is not running. Please start it and enable Kubernetes."
        exit 1
    fi
    
    # Check if Kubernetes is enabled
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Kubernetes is not enabled in Docker Desktop."
        log_info "Please enable it: Docker Desktop → Preferences → Kubernetes → Enable Kubernetes"
        exit 1
    fi
    
    # Install ingress-nginx
    log_info "Installing ingress-nginx..."
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.4/deploy/static/provider/cloud/deploy.yaml
    
    log_info "Docker Desktop Kubernetes setup complete ✓"
}

verify_cluster() {
    log_step "Verifying cluster..."
    
    # Check cluster info
    kubectl cluster-info
    
    # Check nodes
    kubectl get nodes
    
    # Check if cluster is ready
    if kubectl get nodes | grep -q "Ready"; then
        log_info "Cluster is ready ✓"
    else
        log_error "Cluster is not ready"
        exit 1
    fi
}

show_next_steps() {
    echo ""
    log_info "=========================================="
    log_info "Cluster Setup Complete! 🎉"
    log_info "=========================================="
    echo ""
    log_info "Next steps:"
    echo "1. Deploy the application:"
    echo "   cd k8s"
    echo "   ./deploy.sh all"
    echo ""
    echo "2. Access the application:"
    if [ "$CLUSTER_TYPE" = "minikube" ]; then
        echo "   minikube ip  # Get the IP"
        echo "   Access at: http://<minikube-ip>"
    else
        echo "   Access at: http://localhost"
    fi
    echo ""
    echo "3. Or use port-forwarding:"
    echo "   kubectl port-forward -n tenant-management svc/frontend-service 8080:80"
    echo "   Access at: http://localhost:8080"
    echo ""
    log_info "Useful commands:"
    if [ "$CLUSTER_TYPE" = "minikube" ]; then
        echo "   minikube dashboard    # Open Kubernetes dashboard"
        echo "   minikube stop         # Stop cluster"
        echo "   minikube start        # Start cluster"
        echo "   minikube delete       # Delete cluster"
    elif [ "$CLUSTER_TYPE" = "kind" ]; then
        echo "   kind get clusters     # List clusters"
        echo "   kind delete cluster --name tenant-management  # Delete cluster"
    fi
    echo "   kubectl get all -A    # View all resources"
    echo ""
    log_info "=========================================="
}

# Main execution
main() {
    log_info "Starting Kubernetes cluster setup..."
    echo ""
    
    install_prerequisites
    
    case $CLUSTER_TYPE in
        minikube)
            setup_minikube
            ;;
        kind)
            setup_kind
            ;;
        docker-desktop)
            setup_docker_desktop
            ;;
    esac
    
    verify_cluster
    show_next_steps
}

main
