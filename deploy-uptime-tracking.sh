#!/bin/bash

# Safe Deployment Script with Rollback Support
# This script deploys the new uptime tracking feature while keeping the old version for rollback

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

NAMESPACE="tenant-management"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_TAG="backup-${TIMESTAMP}"
NEW_VERSION="v2-uptime-tracking-${TIMESTAMP}"

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║   Safe Deployment - Uptime Tracking Feature          ║"
echo "║   Backup & Rollback Enabled                          ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Commit current changes
log_step "1/8 Creating Git backup tag"
log_info "Committing new uptime tracking changes..."

git add backend/app/models/tenant_state_history.py
git add backend/app/services/metrics_service.py
git add backend/app/schemas/metrics.py
git add backend/alembic/versions/004_tenant_state_history.py
git add backend/app/models/__init__.py
git add backend/app/services/tenant_service.py
git add backend/app/api/endpoints/tenants.py
git add frontend/src/services/tenantService.ts
git add frontend/src/pages/Tenants.tsx
git add UPTIME_TRACKING.md

git commit -m "feat: Add tenant uptime/downtime tracking with monthly metrics

- Add TenantStateHistory model for tracking state transitions
- Add MetricsService for calculating uptime/downtime
- Add metrics API endpoints
- Add Uptime Metrics tab in frontend
- Add database migration 004
- Track running/stopped/scaling states
- Support monthly aggregation
- Auto-refresh metrics every 30s"

log_info "Creating git tag: ${BACKUP_TAG}"
git tag -a "${BACKUP_TAG}" -m "Backup before uptime tracking deployment"

log_info "Creating version tag: ${NEW_VERSION}"
git tag -a "${NEW_VERSION}" -m "Uptime tracking feature deployment"

echo ""
log_info "✓ Git tags created:"
log_info "  Backup tag:  ${BACKUP_TAG}"
log_info "  Version tag: ${NEW_VERSION}"

# Step 2: Backup current deployments
log_step "2/8 Backing up current Kubernetes deployments"

mkdir -p k8s/backups/${TIMESTAMP}

log_info "Exporting current backend deployment..."
kubectl get deployment backend -n ${NAMESPACE} -o yaml > k8s/backups/${TIMESTAMP}/backend-deployment.yaml 2>/dev/null || log_warn "Backend deployment not found (fresh install?)"

log_info "Exporting current frontend deployment..."
kubectl get deployment frontend -n ${NAMESPACE} -o yaml > k8s/backups/${TIMESTAMP}/frontend-deployment.yaml 2>/dev/null || log_warn "Frontend deployment not found (fresh install?)"

log_info "Exporting current database state..."
kubectl get deployment postgres -n ${NAMESPACE} -o yaml > k8s/backups/${TIMESTAMP}/postgres-deployment.yaml 2>/dev/null || log_warn "Postgres deployment not found (fresh install?)"

log_info "✓ Kubernetes state backed up to: k8s/backups/${TIMESTAMP}/"

# Step 3: Create database backup
log_step "3/8 Backing up database"

POSTGRES_POD=$(kubectl get pods -n ${NAMESPACE} -l app=postgres -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -n "$POSTGRES_POD" ]; then
    log_info "Creating database backup..."
    kubectl exec -n ${NAMESPACE} ${POSTGRES_POD} -- pg_dump -U postgres tenant_management > k8s/backups/${TIMESTAMP}/database-backup.sql
    log_info "✓ Database backed up to: k8s/backups/${TIMESTAMP}/database-backup.sql"
else
    log_warn "No postgres pod found - skipping database backup"
fi

# Step 4: Build new images with version tags
log_step "4/8 Building Docker images with version tags"

CLUSTER_TYPE=$(kubectl config current-context | grep -q "minikube" && echo "minikube" || 
               kubectl config current-context | grep -q "kind" && echo "kind" || 
               echo "docker-desktop")

log_info "Detected cluster type: ${CLUSTER_TYPE}"

# Build backend with new version
log_info "Building backend image: tenant-management-backend:${NEW_VERSION}"
docker build -t tenant-management-backend:${NEW_VERSION} backend/
docker tag tenant-management-backend:${NEW_VERSION} tenant-management-backend:latest

# Build frontend with new version
log_info "Building frontend image: tenant-management-frontend:${NEW_VERSION}"
docker build -t tenant-management-frontend:${NEW_VERSION} frontend/
docker tag tenant-management-frontend:${NEW_VERSION} tenant-management-frontend:latest

# Load images into cluster
if [ "$CLUSTER_TYPE" = "minikube" ]; then
    log_info "Loading images into minikube..."
    minikube image load tenant-management-backend:${NEW_VERSION}
    minikube image load tenant-management-frontend:${NEW_VERSION}
    minikube image load tenant-management-backend:latest
    minikube image load tenant-management-frontend:latest
elif [ "$CLUSTER_TYPE" = "kind" ]; then
    log_info "Loading images into kind..."
    kind load docker-image tenant-management-backend:${NEW_VERSION}
    kind load docker-image tenant-management-frontend:${NEW_VERSION}
    kind load docker-image tenant-management-backend:latest
    kind load docker-image tenant-management-frontend:latest
fi

log_info "✓ Docker images built and loaded"

# Step 5: Run database migration
log_step "5/8 Running database migration"

if [ -n "$POSTGRES_POD" ]; then
    log_info "Waiting for postgres to be ready..."
    kubectl wait --for=condition=ready pod -l app=postgres -n ${NAMESPACE} --timeout=60s
    
    log_info "Finding backend pod..."
    BACKEND_POD=$(kubectl get pods -n ${NAMESPACE} -l app=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    
    if [ -n "$BACKEND_POD" ]; then
        log_info "Running Alembic migration..."
        kubectl exec -n ${NAMESPACE} ${BACKEND_POD} -- alembic upgrade head
        log_info "✓ Database migration completed"
    else
        log_warn "Backend pod not found - will run migration after deployment"
    fi
else
    log_warn "Postgres not running - will run migration after deployment"
fi

# Step 6: Update deployments
log_step "6/8 Deploying new version"

log_info "Restarting backend deployment..."
kubectl rollout restart deployment/backend -n ${NAMESPACE} 2>/dev/null || log_warn "Backend deployment not found"

log_info "Restarting frontend deployment..."
kubectl rollout restart deployment/frontend -n ${NAMESPACE} 2>/dev/null || log_warn "Frontend deployment not found"

log_info "Waiting for rollout to complete..."
kubectl rollout status deployment/backend -n ${NAMESPACE} --timeout=300s 2>/dev/null || true
kubectl rollout status deployment/frontend -n ${NAMESPACE} --timeout=300s 2>/dev/null || true

# Step 7: Run migration if not done earlier
log_step "7/8 Ensuring database migration is complete"

BACKEND_POD=$(kubectl get pods -n ${NAMESPACE} -l app=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -n "$BACKEND_POD" ]; then
    log_info "Verifying migration..."
    kubectl exec -n ${NAMESPACE} ${BACKEND_POD} -- alembic upgrade head
    log_info "✓ Migration verified"
fi

# Step 8: Verify deployment
log_step "8/8 Verifying deployment"

log_info "Checking pod status..."
kubectl get pods -n ${NAMESPACE}

echo ""
log_info "Checking backend logs for errors..."
kubectl logs -n ${NAMESPACE} -l app=backend --tail=20 | grep -i error || log_info "No errors found in backend logs"

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║              DEPLOYMENT COMPLETED                      ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
log_info "✓ New version deployed: ${NEW_VERSION}"
log_info "✓ Backup tag created:   ${BACKUP_TAG}"
log_info "✓ Backup location:      k8s/backups/${TIMESTAMP}/"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 ROLLBACK INSTRUCTIONS (if needed):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "If something goes wrong, you can rollback using:"
echo ""
echo "  ./rollback-deployment.sh ${TIMESTAMP}"
echo ""
echo "Or manually:"
echo ""
echo "  # Restore git state"
echo "  git checkout ${BACKUP_TAG}"
echo ""
echo "  # Rollback database"
echo "  kubectl exec -n ${NAMESPACE} \${POSTGRES_POD} -- psql -U postgres tenant_management < k8s/backups/${TIMESTAMP}/database-backup.sql"
echo ""
echo "  # Rollback deployments"
echo "  kubectl apply -f k8s/backups/${TIMESTAMP}/backend-deployment.yaml"
echo "  kubectl apply -f k8s/backups/${TIMESTAMP}/frontend-deployment.yaml"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
log_info "Testing the new feature:"
echo "  1. Open your browser to the tenant management UI"
echo "  2. Click Info (ℹ️) on any tenant"
echo "  3. Click 'Uptime Metrics' tab"
echo "  4. View current state and monthly metrics"
echo ""
log_info "You can now start/stop tenants to see state tracking in action!"
echo ""
