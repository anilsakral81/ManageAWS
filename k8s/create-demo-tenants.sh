#!/bin/bash

# Create demo tenant namespaces for testing
# This script creates sample tenant deployments that can be managed by the portal

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# Create namespaces for demo tenants
TENANTS=("tenant-acme" "tenant-globex" "tenant-initech")

log_step "Creating demo tenant namespaces..."

for tenant in "${TENANTS[@]}"; do
    log_info "Creating namespace: $tenant"
    
    # Create namespace
    kubectl create namespace $tenant --dry-run=client -o yaml | kubectl apply -f -
    
    # Label namespace
    kubectl label namespace $tenant managed-by=tenant-management --overwrite
    
    # Create a simple nginx deployment in each namespace
    cat <<EOF | kubectl apply -f -
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${tenant}-app
  namespace: $tenant
  labels:
    app: ${tenant}-app
    tenant: $tenant
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ${tenant}-app
  template:
    metadata:
      labels:
        app: ${tenant}-app
        tenant: $tenant
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "64Mi"
            cpu: "100m"
          limits:
            memory: "128Mi"
            cpu: "200m"
        livenessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 10
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: ${tenant}-service
  namespace: $tenant
spec:
  selector:
    app: ${tenant}-app
  ports:
  - protocol: TCP
    port: 80
    targetPort: 80
  type: ClusterIP
EOF

    log_info "Created deployment and service for $tenant ✓"
done

echo ""
log_info "=========================================="
log_info "Demo tenants created successfully! 🎉"
log_info "=========================================="
echo ""
log_info "Created namespaces:"
for tenant in "${TENANTS[@]}"; do
    echo "  - $tenant"
done
echo ""
log_info "Verify with:"
echo "  kubectl get namespaces | grep tenant-"
echo "  kubectl get deployments -n tenant-acme"
echo ""
log_info "You can now manage these tenants from the web portal:"
echo "  - Start/Stop deployments"
echo "  - Scale replicas"
echo "  - View status"
echo "  - Schedule automated actions"
echo ""
log_info "=========================================="
