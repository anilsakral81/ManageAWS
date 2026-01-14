# Deployment Process

## Backend Deployment

### Building the Backend Image

Since the EKS cluster uses AMD64 architecture, always build for the correct platform:

```bash
# Login to ECR
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin 122610483530.dkr.ecr.ap-south-1.amazonaws.com

# Build and push (from project root)
docker buildx build --platform linux/amd64 \
  -t 122610483530.dkr.ecr.ap-south-1.amazonaws.com/tenant-management-backend:latest \
  --push backend/
```

### Deploying to Kubernetes

```bash
# Restart deployment to pull new image
kubectl rollout restart deployment/backend -n tenant-management

# Monitor rollout status
kubectl rollout status deployment/backend -n tenant-management

# Verify deployment
kubectl get pods -n tenant-management -l app=backend
```

## Frontend Deployment

```bash
# Build frontend (from project root)
docker buildx build --platform linux/amd64 \
  -t 122610483530.dkr.ecr.ap-south-1.amazonaws.com/tenant-management-frontend:latest \
  --push frontend/

# Restart deployment
kubectl rollout restart deployment/frontend -n tenant-management
```

## Database Migrations

```bash
# Run migrations
kubectl exec -n tenant-management deployment/backend -- alembic upgrade head

# Check migration status
kubectl exec -n tenant-management deployment/backend -- alembic current

# Create new migration
kubectl exec -n tenant-management deployment/backend -- alembic revision --autogenerate -m "description"
```

## Important Notes

- **Platform**: Always use `--platform linux/amd64` for EKS compatibility
- **ECR Login**: ECR tokens expire after 12 hours, re-login if needed
- **Image Tags**: Use `latest` for production deployments
- **Rollback**: Previous image versions are available in ECR history
- **Health Checks**: Pods have built-in health checks at `/health` endpoint

## Current Deployment

- **Backend Image**: `122610483530.dkr.ecr.ap-south-1.amazonaws.com/tenant-management-backend:latest`
- **Frontend Image**: `122610483530.dkr.ecr.ap-south-1.amazonaws.com/tenant-management-frontend:latest`
- **Namespace**: `tenant-management`
- **Cluster**: `arn:aws:eks:ap-south-1:122610483530:cluster/wonderful-blues-rainbow`

## Features Deployed

### Tenant Uptime Tracking
- **Backend**: TenantStateHistory model, MetricsService, 4 API endpoints
- **Frontend**: Uptime Metrics tab in tenant details
- **Database**: tenant_state_history table with automatic state tracking
- **Endpoints**:
  - `GET /api/v1/tenants/{namespace}/metrics` - Full metrics
  - `GET /api/v1/tenants/{namespace}/metrics/current-state` - Current state
  - `GET /api/v1/tenants/{namespace}/metrics/monthly` - Monthly stats
  - `GET /api/v1/tenants/{namespace}/metrics/history` - State history
