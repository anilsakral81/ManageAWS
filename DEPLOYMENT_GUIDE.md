# Safe Deployment Guide - Uptime Tracking Feature

## Overview

This guide explains how to safely deploy the new uptime tracking feature with full rollback capability.

## 🎯 What Gets Deployed

### Backend Changes
- New database table: `tenant_state_history`
- New model: `TenantStateHistory`
- New service: `MetricsService`
- New API endpoints: `/api/tenants/{namespace}/metrics/*`
- Database migration: `004_tenant_state_history.py`
- Updated tenant scaling to record state changes

### Frontend Changes
- New "Uptime Metrics" tab in Tenant Info dialog
- New metrics display components
- API integration for metrics endpoints
- Auto-refresh metrics every 30 seconds

## 📋 Pre-Deployment Checklist

- [ ] Kubernetes cluster is running
- [ ] kubectl is configured and working
- [ ] Docker is running
- [ ] Current system is stable
- [ ] You have tested locally (optional but recommended)

## 🚀 Deployment Steps

### Option 1: Automated Safe Deployment (Recommended)

```bash
cd /Users/comviva/Documents/Code/ManageAWS

# Run the safe deployment script
./deploy-uptime-tracking.sh
```

**What this script does:**
1. ✅ Creates git commit with all new changes
2. ✅ Creates backup git tag (e.g., `backup-20260114_120000`)
3. ✅ Creates version git tag (e.g., `v2-uptime-tracking-20260114_120000`)
4. ✅ Exports current Kubernetes deployments to `k8s/backups/<timestamp>/`
5. ✅ Backs up database to `k8s/backups/<timestamp>/database-backup.sql`
6. ✅ Builds new Docker images with version tags
7. ✅ Runs database migration (adds tenant_state_history table)
8. ✅ Deploys new backend and frontend
9. ✅ Verifies deployment
10. ✅ Shows rollback instructions

### Option 2: Manual Deployment

If you prefer manual control:

#### Step 1: Create Backup
```bash
# Create git backup
git add .
git commit -m "feat: Add uptime tracking"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
git tag -a "backup-${TIMESTAMP}" -m "Backup before deployment"

# Backup Kubernetes state
mkdir -p k8s/backups/${TIMESTAMP}
kubectl get deployment backend -n tenant-management -o yaml > k8s/backups/${TIMESTAMP}/backend-deployment.yaml
kubectl get deployment frontend -n tenant-management -o yaml > k8s/backups/${TIMESTAMP}/frontend-deployment.yaml

# Backup database
POSTGRES_POD=$(kubectl get pods -n tenant-management -l app=postgres -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n tenant-management ${POSTGRES_POD} -- pg_dump -U postgres tenant_management > k8s/backups/${TIMESTAMP}/database-backup.sql
```

#### Step 2: Build New Images
```bash
# Build with version tags
docker build -t tenant-management-backend:v2-uptime -t tenant-management-backend:latest backend/
docker build -t tenant-management-frontend:v2-uptime -t tenant-management-frontend:latest frontend/

# Load into cluster (if using minikube/kind)
minikube image load tenant-management-backend:latest
minikube image load tenant-management-frontend:latest
```

#### Step 3: Run Database Migration
```bash
# Find backend pod
BACKEND_POD=$(kubectl get pods -n tenant-management -l app=backend -o jsonpath='{.items[0].metadata.name}')

# Run migration
kubectl exec -n tenant-management ${BACKEND_POD} -- alembic upgrade head
```

#### Step 4: Deploy
```bash
# Restart deployments to use new images
kubectl rollout restart deployment/backend -n tenant-management
kubectl rollout restart deployment/frontend -n tenant-management

# Wait for completion
kubectl rollout status deployment/backend -n tenant-management
kubectl rollout status deployment/frontend -n tenant-management
```

## 🔄 Rollback Procedure

### Option 1: Automated Rollback

```bash
# List available backups
ls -la k8s/backups/

# Rollback to specific timestamp
./rollback-deployment.sh 20260114_120000
```

### Option 2: Manual Rollback

```bash
# 1. Restore git state
git checkout backup-<TIMESTAMP>

# 2. Rollback database (remove new table)
POSTGRES_POD=$(kubectl get pods -n tenant-management -l app=postgres -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n tenant-management ${POSTGRES_POD} -- psql -U postgres tenant_management -c "DROP TABLE IF EXISTS tenant_state_history CASCADE;"

# 3. Restore Kubernetes deployments
kubectl apply -f k8s/backups/<TIMESTAMP>/backend-deployment.yaml
kubectl apply -f k8s/backups/<TIMESTAMP>/frontend-deployment.yaml

# 4. Wait for rollout
kubectl rollout status deployment/backend -n tenant-management
kubectl rollout status deployment/frontend -n tenant-management
```

## ✅ Post-Deployment Verification

### 1. Check Pod Status
```bash
kubectl get pods -n tenant-management
```

Expected: All pods should be Running

### 2. Check Backend Logs
```bash
kubectl logs -n tenant-management -l app=backend --tail=50
```

Look for:
- No errors
- Migration success message
- Server started successfully

### 3. Check Database Migration
```bash
BACKEND_POD=$(kubectl get pods -n tenant-management -l app=backend -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n tenant-management ${BACKEND_POD} -- alembic current
```

Expected: Should show revision `004` (tenant_state_history)

### 4. Test the Feature

1. **Open the UI** in your browser
2. **Navigate to Tenants page**
3. **Click Info (ℹ️)** on any tenant
4. **Click "Uptime Metrics" tab**
5. **Verify you see:**
   - Current State card
   - Monthly Uptime card (may show 0% if no history yet)
   - Recent State Changes table (may be empty initially)

### 5. Generate Test Data

```bash
# Start a tenant to generate state history
# Via UI: Click Start button on a stopped tenant
# OR via API:
kubectl exec -n tenant-management ${BACKEND_POD} -- curl -X POST http://localhost:8000/api/tenants/<namespace>/start
```

Wait a moment, then check the Uptime Metrics tab again - you should see a state change recorded.

## 🐛 Troubleshooting

### Issue: Migration Failed

**Symptoms:** Backend pod crashes or migration errors

**Solution:**
```bash
# Check migration status
BACKEND_POD=$(kubectl get pods -n tenant-management -l app=backend -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n tenant-management ${BACKEND_POD} -- alembic current

# If stuck, rollback and try again
./rollback-deployment.sh <TIMESTAMP>
```

### Issue: Frontend Not Loading Metrics

**Symptoms:** Uptime Metrics tab shows error or spinner indefinitely

**Solution:**
```bash
# Check backend logs for API errors
kubectl logs -n tenant-management -l app=backend --tail=100 | grep metrics

# Verify endpoints are accessible
BACKEND_POD=$(kubectl get pods -n tenant-management -l app=backend -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n tenant-management ${BACKEND_POD} -- curl http://localhost:8000/api/tenants
```

### Issue: Database Connection Errors

**Symptoms:** Backend can't connect to database

**Solution:**
```bash
# Check postgres pod
kubectl get pods -n tenant-management -l app=postgres

# Check backend can reach postgres
kubectl exec -n tenant-management ${BACKEND_POD} -- nc -zv postgres-service 5432
```

## 📊 Backup Retention

Backups are stored in `k8s/backups/<timestamp>/` and include:

- `backend-deployment.yaml` - Backend Kubernetes deployment
- `frontend-deployment.yaml` - Frontend Kubernetes deployment
- `postgres-deployment.yaml` - Database deployment
- `database-backup.sql` - Full database dump

**Recommendation:** Keep backups for at least 30 days before cleanup.

## 🔒 Rollback Decision Matrix

| Issue | Severity | Action |
|-------|----------|--------|
| Backend pod crashes | High | Rollback immediately |
| Migration fails | High | Rollback immediately |
| Frontend shows errors | Medium | Investigate first, rollback if critical |
| Metrics not loading | Medium | Check backend logs, rollback if needed |
| UI looks broken | Medium | Check browser console, may be cache issue |
| Performance degradation | High | Rollback if >20% slowdown |
| No issues found | Low | Continue monitoring for 24h |

## 📝 Deployment Checklist

After deployment, verify:

- [ ] All pods are running
- [ ] No errors in backend logs
- [ ] No errors in frontend logs
- [ ] Database migration completed (revision 004)
- [ ] UI loads without errors
- [ ] Uptime Metrics tab appears in tenant info dialog
- [ ] Starting/stopping a tenant creates state history
- [ ] Metrics display correctly after state change
- [ ] No performance degradation
- [ ] Backup created and accessible

## 🎉 Success Criteria

Deployment is successful when:

1. ✅ All pods are healthy and running
2. ✅ Database migration to version 004 completed
3. ✅ Uptime Metrics tab appears in UI
4. ✅ State changes are recorded when starting/stopping tenants
5. ✅ Metrics calculate and display correctly
6. ✅ No errors in logs for 15 minutes
7. ✅ Rollback plan is ready and tested (optional)

## 📞 Support

If you encounter issues:

1. Check logs: `kubectl logs -n tenant-management -l app=backend --tail=100`
2. Check pod status: `kubectl get pods -n tenant-management`
3. Review [UPTIME_TRACKING.md](UPTIME_TRACKING.md) for feature documentation
4. Use rollback if critical issues found

---

**Remember:** You can always rollback safely using the backup created during deployment!
