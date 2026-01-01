#!/bin/bash

# Build and Deploy Tenant Management Application to Kubernetes
# Usage: ./deploy.sh [build|apply|delete|restart]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="tenant-management"
BACKEND_IMAGE="tenant-management-backend"
FRONTEND_IMAGE="tenant-management-frontend"
VERSION="latest"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    # Check if docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if cluster is running
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Kubernetes cluster is not running. Please start your cluster (minikube, kind, or Docker Desktop)."
        exit 1
    fi
    
    log_info "Prerequisites check passed ✓"
}

detect_cluster_type() {
    if kubectl config current-context | grep -q "minikube"; then
        echo "minikube"
    elif kubectl config current-context | grep -q "kind"; then
        echo "kind"
    elif kubectl config current-context | grep -q "docker-desktop"; then
        echo "docker-desktop"
    else
        echo "unknown"
    fi
}

build_images() {
    log_info "Building Docker images..."
    
    CLUSTER_TYPE=$(detect_cluster_type)
    log_info "Detected cluster type: $CLUSTER_TYPE"
    
    # Build backend image
    log_info "Building backend image..."
    docker build -t ${BACKEND_IMAGE}:${VERSION} ../backend
    
    # Build frontend image
    log_info "Building frontend image..."
    docker build -t ${FRONTEND_IMAGE}:${VERSION} ../frontend
    
    # Load images into cluster if using minikube or kind
    if [ "$CLUSTER_TYPE" = "minikube" ]; then
        log_info "Loading images into minikube..."
        minikube image load ${BACKEND_IMAGE}:${VERSION}
        minikube image load ${FRONTEND_IMAGE}:${VERSION}
    elif [ "$CLUSTER_TYPE" = "kind" ]; then
        log_info "Loading images into kind..."
        kind load docker-image ${BACKEND_IMAGE}:${VERSION}
        kind load docker-image ${FRONTEND_IMAGE}:${VERSION}
    fi
    
    log_info "Docker images built successfully ✓"
}

apply_manifests() {
    log_info "Applying Kubernetes manifests..."
    
    # Apply manifests in order
    kubectl apply -f 00-namespace.yaml
    kubectl apply -f 01-configmaps.yaml
    kubectl apply -f 02-secrets.yaml
    kubectl apply -f 03-postgres.yaml
    kubectl apply -f 04-rbac.yaml
    
    # Wait for postgres to be ready
    log_info "Waiting for PostgreSQL to be ready..."
    kubectl wait --for=condition=ready pod -l app=postgres -n ${NAMESPACE} --timeout=300s
    
    # Run database migrations
    log_info "Running database migrations..."
    run_migrations
    
    # Apply backend and frontend
    kubectl apply -f 05-backend.yaml
    kubectl apply -f 06-frontend.yaml
    kubectl apply -f 07-ingress.yaml
    
    log_info "Kubernetes manifests applied successfully ✓"
}

run_migrations() {
    log_info "Running Alembic migrations..."
    
    # Create a job to run migrations
    cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration-$(date +%s)
  namespace: ${NAMESPACE}
spec:
  ttlSecondsAfterFinished: 100
  template:
    spec:
      restartPolicy: Never
      initContainers:
      - name: wait-for-postgres
        image: busybox:1.36
        command: ['sh', '-c', 'until nc -z postgres-service 5432; do echo waiting for postgres; sleep 2; done;']
      containers:
      - name: migration
        image: ${BACKEND_IMAGE}:${VERSION}
        imagePullPolicy: Never
        command: ["/bin/sh", "-c"]
        args:
          - |
            echo "Running database migrations..."
            alembic upgrade head
            echo "Running seed script..."
            python scripts/init_db.py
            echo "Migrations completed successfully!"
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: backend-secret
              key: DATABASE_URL
EOF

    # Wait for migration job to complete
    log_info "Waiting for migration job to complete..."
    sleep 5
    JOB_NAME=$(kubectl get jobs -n ${NAMESPACE} --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')
    kubectl wait --for=condition=complete job/${JOB_NAME} -n ${NAMESPACE} --timeout=300s
    
    log_info "Database migrations completed ✓"
}

delete_resources() {
    log_warn "Deleting all resources in namespace ${NAMESPACE}..."
    kubectl delete namespace ${NAMESPACE} --ignore-not-found=true
    log_info "Resources deleted successfully ✓"
}

restart_services() {
    log_info "Restarting backend and frontend deployments..."
    kubectl rollout restart deployment/backend -n ${NAMESPACE}
    kubectl rollout restart deployment/frontend -n ${NAMESPACE}
    log_info "Services restarted successfully ✓"
}

get_status() {
    log_info "Getting deployment status..."
    echo ""
    kubectl get all -n ${NAMESPACE}
    echo ""
    log_info "ConfigMaps:"
    kubectl get configmaps -n ${NAMESPACE}
    echo ""
    log_info "Secrets:"
    kubectl get secrets -n ${NAMESPACE}
    echo ""
    log_info "PVCs:"
    kubectl get pvc -n ${NAMESPACE}
}

get_access_info() {
    CLUSTER_TYPE=$(detect_cluster_type)
    
    echo ""
    log_info "==================================="
    log_info "Application Access Information"
    log_info "==================================="
    
    if [ "$CLUSTER_TYPE" = "minikube" ]; then
        log_info "Getting minikube service URL..."
        echo ""
        log_info "Enable ingress addon if not already enabled:"
        echo "  minikube addons enable ingress"
        echo ""
        log_info "Get the minikube IP:"
        MINIKUBE_IP=$(minikube ip)
        echo "  Minikube IP: $MINIKUBE_IP"
        echo ""
        log_info "Access the application at:"
        echo "  http://$MINIKUBE_IP"
        echo ""
        log_info "Or use port-forwarding:"
        echo "  kubectl port-forward -n ${NAMESPACE} svc/frontend-service 8080:80"
        echo "  Then access: http://localhost:8080"
        
    elif [ "$CLUSTER_TYPE" = "kind" ]; then
        log_info "For kind cluster, install ingress-nginx:"
        echo "  kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml"
        echo ""
        log_info "Then access the application at:"
        echo "  http://localhost"
        echo ""
        log_info "Or use port-forwarding:"
        echo "  kubectl port-forward -n ${NAMESPACE} svc/frontend-service 8080:80"
        echo "  Then access: http://localhost:8080"
        
    elif [ "$CLUSTER_TYPE" = "docker-desktop" ]; then
        log_info "For Docker Desktop, enable ingress controller:"
        echo "  kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.4/deploy/static/provider/cloud/deploy.yaml"
        echo ""
        log_info "Access the application at:"
        echo "  http://localhost"
        echo ""
        log_info "Or use port-forwarding:"
        echo "  kubectl port-forward -n ${NAMESPACE} svc/frontend-service 8080:80"
        echo "  Then access: http://localhost:8080"
    else
        log_info "Use port-forwarding to access the application:"
        echo "  kubectl port-forward -n ${NAMESPACE} svc/frontend-service 8080:80"
        echo "  Then access: http://localhost:8080"
    fi
    
    echo ""
    log_info "Backend API:"
    echo "  kubectl port-forward -n ${NAMESPACE} svc/backend-service 8000:8000"
    echo "  Then access: http://localhost:8000/docs"
    echo ""
    log_info "==================================="
}

show_logs() {
    log_info "Showing logs for backend and frontend..."
    echo ""
    log_info "Backend logs:"
    kubectl logs -l app=backend -n ${NAMESPACE} --tail=50
    echo ""
    log_info "Frontend logs:"
    kubectl logs -l app=frontend -n ${NAMESPACE} --tail=50
}

# Main script
case "$1" in
    build)
        check_prerequisites
        build_images
        ;;
    apply)
        check_prerequisites
        apply_manifests
        get_status
        get_access_info
        ;;
    delete)
        delete_resources
        ;;
    restart)
        restart_services
        ;;
    status)
        get_status
        ;;
    logs)
        show_logs
        ;;
    all)
        check_prerequisites
        build_images
        apply_manifests
        get_status
        get_access_info
        ;;
    *)
        echo "Usage: $0 {build|apply|delete|restart|status|logs|all}"
        echo ""
        echo "Commands:"
        echo "  build    - Build Docker images"
        echo "  apply    - Apply Kubernetes manifests"
        echo "  delete   - Delete all resources"
        echo "  restart  - Restart backend and frontend deployments"
        echo "  status   - Show deployment status"
        echo "  logs     - Show application logs"
        echo "  all      - Build images and deploy everything"
        echo ""
        echo "Example:"
        echo "  $0 all          # Build and deploy everything"
        echo "  $0 build        # Only build images"
        echo "  $0 apply        # Only apply manifests"
        exit 1
        ;;
esac
