#!/bin/bash

# Deploy Tenant Management Application to AWS EKS
# This script automates the complete deployment process to EKS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_header() {
    echo ""
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}  AWS EKS Deployment Script${NC}"
    echo -e "${BLUE}  Tenant Management Application${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo ""
}

# Check prerequisites
check_prerequisites() {
    log_step "Checking prerequisites..."
    
    local missing_tools=()
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        missing_tools+=("kubectl")
    fi
    
    # Check docker
    if ! command -v docker &> /dev/null; then
        missing_tools+=("docker")
    fi
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        missing_tools+=("aws-cli")
    fi
    
    # Check eksctl
    if ! command -v eksctl &> /dev/null; then
        log_warn "eksctl is not installed. It's recommended but not required."
    fi
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        echo ""
        echo "Install missing tools:"
        for tool in "${missing_tools[@]}"; do
            case $tool in
                kubectl)
                    echo "  kubectl: brew install kubectl"
                    ;;
                docker)
                    echo "  docker: brew install --cask docker"
                    ;;
                aws-cli)
                    echo "  aws-cli: brew install awscli"
                    ;;
            esac
        done
        exit 1
    fi
    
    log_info "All required tools are installed ✓"
}

# Configure AWS credentials
configure_aws() {
    log_step "Checking AWS configuration..."
    
    if ! aws sts get-caller-identity &> /dev/null; then
        log_warn "AWS credentials not configured or invalid"
        echo ""
        read -p "Do you want to configure AWS credentials now? (y/n): " configure_now
        if [[ $configure_now =~ ^[Yy]$ ]]; then
            aws configure
        else
            log_error "AWS credentials are required. Run 'aws configure' manually."
            exit 1
        fi
    fi
    
    # Get AWS account ID and region
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    AWS_REGION=$(aws configure get region)
    
    if [ -z "$AWS_REGION" ]; then
        read -p "Enter AWS region (e.g., us-east-1): " AWS_REGION
    fi
    
    log_info "AWS Account ID: $AWS_ACCOUNT_ID"
    log_info "AWS Region: $AWS_REGION"
    
    # Confirm
    read -p "Continue with these settings? (y/n): " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        log_error "Deployment cancelled"
        exit 1
    fi
}

# Connect to EKS cluster
connect_to_eks() {
    log_step "Connecting to EKS cluster..."
    
    # List available clusters
    log_info "Fetching available EKS clusters..."
    CLUSTERS=$(aws eks list-clusters --region $AWS_REGION --query 'clusters[]' --output text)
    
    if [ -z "$CLUSTERS" ]; then
        log_error "No EKS clusters found in region $AWS_REGION"
        echo ""
        read -p "Do you want to create a new EKS cluster? (y/n): " create_cluster
        if [[ $create_cluster =~ ^[Yy]$ ]]; then
            create_eks_cluster
        else
            log_error "EKS cluster is required for deployment"
            exit 1
        fi
    else
        echo ""
        echo "Available EKS clusters:"
        select CLUSTER_NAME in $CLUSTERS; do
            if [ -n "$CLUSTER_NAME" ]; then
                break
            fi
        done
    fi
    
    log_info "Selected cluster: $CLUSTER_NAME"
    
    # Update kubeconfig
    log_info "Updating kubeconfig..."
    aws eks update-kubeconfig --region $AWS_REGION --name $CLUSTER_NAME
    
    # Verify connection
    if kubectl cluster-info &> /dev/null; then
        log_info "Successfully connected to EKS cluster ✓"
        kubectl get nodes
    else
        log_error "Failed to connect to EKS cluster"
        exit 1
    fi
}

# Create EKS cluster (optional)
create_eks_cluster() {
    log_step "Creating new EKS cluster..."
    
    if ! command -v eksctl &> /dev/null; then
        log_error "eksctl is required to create a cluster"
        echo "Install with: brew install eksctl"
        exit 1
    fi
    
    read -p "Enter cluster name: " CLUSTER_NAME
    read -p "Enter node instance type (default: t3.medium): " INSTANCE_TYPE
    INSTANCE_TYPE=${INSTANCE_TYPE:-t3.medium}
    read -p "Enter number of nodes (default: 2): " NODE_COUNT
    NODE_COUNT=${NODE_COUNT:-2}
    
    log_info "Creating EKS cluster '$CLUSTER_NAME'..."
    log_warn "This will take 15-20 minutes..."
    
    eksctl create cluster \
        --name $CLUSTER_NAME \
        --region $AWS_REGION \
        --nodegroup-name standard-workers \
        --node-type $INSTANCE_TYPE \
        --nodes $NODE_COUNT \
        --nodes-min 1 \
        --nodes-max 4 \
        --managed
    
    log_info "EKS cluster created successfully ✓"
}

# Create ECR repositories
create_ecr_repositories() {
    log_step "Setting up ECR repositories..."
    
    ECR_BACKEND_REPO="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$BACKEND_IMAGE"
    ECR_FRONTEND_REPO="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$FRONTEND_IMAGE"
    
    # Create backend repository
    if aws ecr describe-repositories --repository-names $BACKEND_IMAGE --region $AWS_REGION &> /dev/null; then
        log_info "ECR repository '$BACKEND_IMAGE' already exists"
    else
        log_info "Creating ECR repository '$BACKEND_IMAGE'..."
        aws ecr create-repository \
            --repository-name $BACKEND_IMAGE \
            --region $AWS_REGION \
            --image-scanning-configuration scanOnPush=true
        log_info "Backend repository created ✓"
    fi
    
    # Create frontend repository
    if aws ecr describe-repositories --repository-names $FRONTEND_IMAGE --region $AWS_REGION &> /dev/null; then
        log_info "ECR repository '$FRONTEND_IMAGE' already exists"
    else
        log_info "Creating ECR repository '$FRONTEND_IMAGE'..."
        aws ecr create-repository \
            --repository-name $FRONTEND_IMAGE \
            --region $AWS_REGION \
            --image-scanning-configuration scanOnPush=true
        log_info "Frontend repository created ✓"
    fi
}

# Login to ECR
ecr_login() {
    log_step "Logging in to Amazon ECR..."
    
    aws ecr get-login-password --region $AWS_REGION | \
        docker login --username AWS --password-stdin \
        $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
    
    log_info "ECR login successful ✓"
}

# Build and push Docker images
build_and_push_images() {
    log_step "Building and pushing Docker images..."
    
    # Get the project root directory
    PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    
    # Build backend
    log_info "Building backend image..."
    cd "$PROJECT_ROOT/backend"
    docker build -t $BACKEND_IMAGE:$VERSION .
    docker tag $BACKEND_IMAGE:$VERSION $ECR_BACKEND_REPO:$VERSION
    docker tag $BACKEND_IMAGE:$VERSION $ECR_BACKEND_REPO:latest
    
    log_info "Pushing backend image to ECR..."
    docker push $ECR_BACKEND_REPO:$VERSION
    docker push $ECR_BACKEND_REPO:latest
    log_info "Backend image pushed ✓"
    
    # Build frontend
    log_info "Building frontend image..."
    cd "$PROJECT_ROOT/frontend"
    docker build -t $FRONTEND_IMAGE:$VERSION .
    docker tag $FRONTEND_IMAGE:$VERSION $ECR_FRONTEND_REPO:$VERSION
    docker tag $FRONTEND_IMAGE:$VERSION $ECR_FRONTEND_REPO:latest
    
    log_info "Pushing frontend image to ECR..."
    docker push $ECR_FRONTEND_REPO:$VERSION
    docker push $ECR_FRONTEND_REPO:latest
    log_info "Frontend image pushed ✓"
    
    cd "$PROJECT_ROOT/k8s"
}

# Update Kubernetes manifests with ECR image paths
update_k8s_manifests() {
    log_step "Updating Kubernetes manifests..."
    
    PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    
    # Create EKS-specific manifest directory
    EKS_MANIFEST_DIR="$PROJECT_ROOT/k8s/eks-manifests"
    mkdir -p $EKS_MANIFEST_DIR
    
    # Copy and update backend deployment
    log_info "Updating backend deployment manifest..."
    sed "s|image: tenant-management-backend:latest|image: $ECR_BACKEND_REPO:latest|g" \
        "$PROJECT_ROOT/k8s/05-backend.yaml" > "$EKS_MANIFEST_DIR/05-backend.yaml"
    
    # Update imagePullPolicy
    sed -i '' 's|imagePullPolicy: Never|imagePullPolicy: Always|g' \
        "$EKS_MANIFEST_DIR/05-backend.yaml"
    
    # Copy and update frontend deployment
    log_info "Updating frontend deployment manifest..."
    sed "s|image: tenant-management-frontend:latest|image: $ECR_FRONTEND_REPO:latest|g" \
        "$PROJECT_ROOT/k8s/06-frontend.yaml" > "$EKS_MANIFEST_DIR/06-frontend.yaml"
    
    # Update imagePullPolicy
    sed -i '' 's|imagePullPolicy: Never|imagePullPolicy: Always|g' \
        "$EKS_MANIFEST_DIR/06-frontend.yaml"
    
    # Copy other manifests
    log_info "Copying other manifests..."
    for file in 00-namespace.yaml 01-configmaps.yaml 02-secrets.yaml 03-postgres.yaml 04-rbac.yaml 07-ingress.yaml; do
        cp "$PROJECT_ROOT/k8s/$file" "$EKS_MANIFEST_DIR/"
    done
    
    log_info "Manifests updated and saved to $EKS_MANIFEST_DIR ✓"
}

# Deploy to EKS
deploy_to_eks() {
    log_step "Deploying application to EKS..."
    
    PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    EKS_MANIFEST_DIR="$PROJECT_ROOT/k8s/eks-manifests"
    
    # Create namespace
    log_info "Creating namespace..."
    kubectl apply -f "$EKS_MANIFEST_DIR/00-namespace.yaml"
    
    # Apply secrets and configmaps
    log_info "Applying secrets and configmaps..."
    kubectl apply -f "$EKS_MANIFEST_DIR/02-secrets.yaml"
    kubectl apply -f "$EKS_MANIFEST_DIR/01-configmaps.yaml"
    
    # Deploy PostgreSQL
    log_info "Deploying PostgreSQL..."
    kubectl apply -f "$EKS_MANIFEST_DIR/03-postgres.yaml"
    
    # Wait for PostgreSQL to be ready
    log_info "Waiting for PostgreSQL to be ready..."
    kubectl wait --for=condition=ready pod -l app=postgres -n $NAMESPACE --timeout=300s
    
    # Apply RBAC
    log_info "Applying RBAC..."
    kubectl apply -f "$EKS_MANIFEST_DIR/04-rbac.yaml"
    
    # Deploy backend
    log_info "Deploying backend..."
    kubectl apply -f "$EKS_MANIFEST_DIR/05-backend.yaml"
    
    # Wait for backend to be ready
    log_info "Waiting for backend to be ready..."
    kubectl wait --for=condition=ready pod -l app=backend -n $NAMESPACE --timeout=300s
    
    # Run database migrations
    log_info "Running database migrations..."
    BACKEND_POD=$(kubectl get pod -n $NAMESPACE -l app=backend -o jsonpath='{.items[0].metadata.name}')
    kubectl exec -n $NAMESPACE $BACKEND_POD -- alembic upgrade head
    
    # Deploy frontend
    log_info "Deploying frontend..."
    kubectl apply -f "$EKS_MANIFEST_DIR/06-frontend.yaml"
    
    # Wait for frontend to be ready
    log_info "Waiting for frontend to be ready..."
    kubectl wait --for=condition=ready pod -l app=frontend -n $NAMESPACE --timeout=300s
    
    log_info "Application deployed successfully ✓"
}

# Setup AWS Load Balancer Controller (for ingress)
setup_alb_controller() {
    log_step "Setting up AWS Load Balancer Controller..."
    
    read -p "Do you want to set up AWS Load Balancer Controller for ingress? (y/n): " setup_alb
    if [[ ! $setup_alb =~ ^[Yy]$ ]]; then
        log_info "Skipping ALB controller setup"
        return
    fi
    
    # Create IAM OIDC provider
    log_info "Creating IAM OIDC provider for cluster..."
    eksctl utils associate-iam-oidc-provider \
        --region=$AWS_REGION \
        --cluster=$CLUSTER_NAME \
        --approve
    
    # Download IAM policy
    log_info "Downloading ALB controller IAM policy..."
    curl -o iam_policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.7.0/docs/install/iam_policy.json
    
    # Create IAM policy
    log_info "Creating IAM policy..."
    aws iam create-policy \
        --policy-name AWSLoadBalancerControllerIAMPolicy \
        --policy-document file://iam_policy.json || true
    
    # Create service account
    log_info "Creating service account..."
    eksctl create iamserviceaccount \
        --cluster=$CLUSTER_NAME \
        --namespace=kube-system \
        --name=aws-load-balancer-controller \
        --role-name AmazonEKSLoadBalancerControllerRole \
        --attach-policy-arn=arn:aws:iam::$AWS_ACCOUNT_ID:policy/AWSLoadBalancerControllerIAMPolicy \
        --approve || true
    
    # Install AWS Load Balancer Controller using Helm
    log_info "Installing AWS Load Balancer Controller..."
    helm repo add eks https://aws.github.io/eks-charts || true
    helm repo update
    
    helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
        -n kube-system \
        --set clusterName=$CLUSTER_NAME \
        --set serviceAccount.create=false \
        --set serviceAccount.name=aws-load-balancer-controller || true
    
    # Update ingress for ALB
    log_info "Updating ingress configuration for ALB..."
    PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    EKS_MANIFEST_DIR="$PROJECT_ROOT/k8s/eks-manifests"
    
    cat > "$EKS_MANIFEST_DIR/07-ingress.yaml" <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tenant-management-ingress
  namespace: $NAMESPACE
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/healthcheck-path: /health
spec:
  rules:
    - http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: backend-service
                port:
                  number: 8000
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend-service
                port:
                  number: 80
EOF
    
    kubectl apply -f "$EKS_MANIFEST_DIR/07-ingress.yaml"
    
    rm -f iam_policy.json
    log_info "AWS Load Balancer Controller setup complete ✓"
}

# Display access information
display_access_info() {
    log_step "Deployment Summary"
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Deployment Successful! 🎉${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    
    # Get service information
    kubectl get all -n $NAMESPACE
    
    echo ""
    log_info "Access Options:"
    echo ""
    
    # Check for LoadBalancer
    LB_HOSTNAME=$(kubectl get ingress -n $NAMESPACE -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")
    
    if [ -n "$LB_HOSTNAME" ]; then
        echo "  🌐 Application URL: http://$LB_HOSTNAME"
        echo "  📝 Note: DNS propagation may take a few minutes"
    else
        echo "  📌 Port Forwarding (for immediate access):"
        echo "     Frontend:"
        echo "       kubectl port-forward -n $NAMESPACE svc/frontend-service 8080:80"
        echo "       Then visit: http://localhost:8080"
        echo ""
        echo "     Backend API:"
        echo "       kubectl port-forward -n $NAMESPACE svc/backend-service 8000:8000"
        echo "       Then visit: http://localhost:8000/docs"
    fi
    
    echo ""
    log_info "Useful Commands:"
    echo "  • View logs: kubectl logs -f -n $NAMESPACE -l app=backend"
    echo "  • View pods: kubectl get pods -n $NAMESPACE"
    echo "  • Describe pod: kubectl describe pod -n $NAMESPACE <pod-name>"
    echo "  • Delete deployment: kubectl delete namespace $NAMESPACE"
    echo ""
}

# Cleanup function
cleanup() {
    log_step "Cleaning up EKS deployment..."
    
    read -p "Are you sure you want to delete the entire deployment? (y/n): " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        log_info "Cleanup cancelled"
        exit 0
    fi
    
    log_info "Deleting Kubernetes resources..."
    kubectl delete namespace $NAMESPACE || true
    
    read -p "Do you want to delete ECR repositories? (y/n): " delete_ecr
    if [[ $delete_ecr =~ ^[Yy]$ ]]; then
        log_info "Deleting ECR repositories..."
        aws ecr delete-repository --repository-name $BACKEND_IMAGE --region $AWS_REGION --force || true
        aws ecr delete-repository --repository-name $FRONTEND_IMAGE --region $AWS_REGION --force || true
    fi
    
    log_info "Cleanup complete ✓"
}

# Main execution
main() {
    print_header
    
    # Parse command line arguments
    case "${1:-deploy}" in
        deploy)
            check_prerequisites
            configure_aws
            connect_to_eks
            create_ecr_repositories
            ecr_login
            build_and_push_images
            update_k8s_manifests
            deploy_to_eks
            setup_alb_controller
            display_access_info
            ;;
        build)
            check_prerequisites
            configure_aws
            create_ecr_repositories
            ecr_login
            build_and_push_images
            log_info "Images built and pushed to ECR ✓"
            ;;
        apply)
            check_prerequisites
            configure_aws
            connect_to_eks
            update_k8s_manifests
            deploy_to_eks
            display_access_info
            ;;
        cleanup|delete)
            check_prerequisites
            configure_aws
            connect_to_eks
            cleanup
            ;;
        *)
            echo "Usage: $0 [deploy|build|apply|cleanup]"
            echo ""
            echo "Commands:"
            echo "  deploy  - Full deployment (default): build images, push to ECR, and deploy to EKS"
            echo "  build   - Build and push images to ECR only"
            echo "  apply   - Deploy/update Kubernetes manifests only"
            echo "  cleanup - Delete all resources from EKS and optionally ECR"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
