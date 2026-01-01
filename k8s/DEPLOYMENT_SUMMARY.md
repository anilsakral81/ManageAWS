# Kubernetes Deployment - Complete Setup Summary

All Kubernetes manifests and deployment scripts have been created for running the Tenant Management Portal in a local Kubernetes cluster.

## 📦 Created Files

### Kubernetes Manifests (k8s/)

1. **00-namespace.yaml** - Namespace creation
   - Creates `tenant-management` namespace with labels

2. **01-configmaps.yaml** - Configuration
   - `backend-config`: Backend environment variables (API settings, CORS, scheduler)
   - `frontend-config`: Frontend environment variables (API URL, Keycloak)

3. **02-secrets.yaml** - Sensitive data
   - `postgres-secret`: Database credentials
   - `backend-secret`: Database URL, Keycloak secrets, AWS credentials

4. **03-postgres.yaml** - PostgreSQL database
   - PersistentVolumeClaim (5Gi storage)
   - Deployment (postgres:16-alpine)
   - Service (ClusterIP on port 5432)
   - Health checks and resource limits

5. **04-rbac.yaml** - Kubernetes permissions
   - ServiceAccount: `tenant-manager`
   - ClusterRole: Permissions to manage deployments/statefulsets in tenant namespaces
   - ClusterRoleBinding: Binds role to service account

6. **05-backend.yaml** - FastAPI backend
   - Deployment (2 replicas, tenant-management-backend:latest)
   - Init container to wait for PostgreSQL
   - Environment variables from ConfigMap and Secret
   - Health/readiness probes
   - Service (ClusterIP on port 8000)

7. **06-frontend.yaml** - React frontend
   - Deployment (2 replicas, tenant-management-frontend:latest)
   - Nginx serving static files
   - Environment variables from ConfigMap
   - Health/readiness probes
   - Service (ClusterIP on port 80)

8. **07-ingress.yaml** - External access
   - Ingress resource with nginx controller
   - Routes `/` to frontend, `/api` to backend
   - Configured for localhost

### Deployment Scripts

9. **deploy.sh** - Main deployment script
   - `./deploy.sh all` - Build and deploy everything
   - `./deploy.sh build` - Build Docker images
   - `./deploy.sh apply` - Apply Kubernetes manifests
   - `./deploy.sh delete` - Delete all resources
   - `./deploy.sh restart` - Restart deployments
   - `./deploy.sh status` - Show deployment status
   - `./deploy.sh logs` - Show application logs
   - Auto-detects cluster type (minikube/kind/docker-desktop)
   - Runs database migrations automatically
   - Loads images into cluster

10. **setup-cluster.sh** - Cluster initialization
    - Interactive setup for minikube/kind/docker-desktop
    - Installs prerequisites (kubectl, docker)
    - Starts cluster with proper configuration
    - Enables ingress and metrics addons
    - Provides next steps

11. **create-demo-tenants.sh** - Demo data
    - Creates 3 tenant namespaces (tenant-acme, tenant-globex, tenant-initech)
    - Deploys nginx apps in each namespace
    - Labels namespaces for management

### Documentation

12. **README.md** (k8s/)
    - Comprehensive deployment guide
    - Prerequisites and setup instructions
    - Manual deployment steps
    - Configuration management
    - Architecture diagram
    - Troubleshooting guide
    - Production considerations

13. **QUICKSTART.md** (root)
    - Quick start guide with one-command deploy
    - Access instructions for different cluster types
    - Common tasks reference
    - Development workflow
    - Troubleshooting quick reference

### Docker Configuration

14. **frontend/Dockerfile** (previously created)
    - Multi-stage build (Node builder + Nginx)
    - Optimized for production
    - Health check endpoint

15. **frontend/nginx.conf** (previously created)
    - SPA routing with fallback to index.html
    - Reverse proxy `/api` → `backend-service:8000`
    - Gzip compression
    - Static asset caching
    - Security headers

16. **backend/Dockerfile** (existing)
    - Python 3.11-slim base
    - Non-root user (appuser)
    - Health check endpoint
    - Uvicorn server

## 🚀 Quick Start

### One-Command Deployment

```bash
# 1. Setup cluster (first time only)
cd /Users/comviva/Documents/Code/ManageAWS/k8s
./setup-cluster.sh

# 2. Deploy application
./deploy.sh all

# 3. Access application
kubectl port-forward -n tenant-management svc/frontend-service 8080:80
# Open: http://localhost:8080

# 4. Create demo tenants
./create-demo-tenants.sh
```

### Alternative: Manual Steps

```bash
# 1. Start cluster
minikube start --driver=docker --cpus=4 --memory=8192
minikube addons enable ingress

# 2. Build images
cd /Users/comviva/Documents/Code/ManageAWS
docker build -t tenant-management-backend:latest ./backend
docker build -t tenant-management-frontend:latest ./frontend

# 3. Load images
minikube image load tenant-management-backend:latest
minikube image load tenant-management-frontend:latest

# 4. Deploy
cd k8s
kubectl apply -f 00-namespace.yaml
kubectl apply -f 01-configmaps.yaml
kubectl apply -f 02-secrets.yaml
kubectl apply -f 03-postgres.yaml
kubectl wait --for=condition=ready pod -l app=postgres -n tenant-management --timeout=300s
kubectl apply -f 04-rbac.yaml
kubectl apply -f 05-backend.yaml
kubectl apply -f 06-frontend.yaml
kubectl apply -f 07-ingress.yaml

# 5. Run migrations
BACKEND_POD=$(kubectl get pods -n tenant-management -l app=backend -o jsonpath='{.items[0].metadata.name}')
kubectl exec -it $BACKEND_POD -n tenant-management -- alembic upgrade head
kubectl exec -it $BACKEND_POD -n tenant-management -- python scripts/init_db.py
```

## 🔧 Configuration

### Backend Environment Variables

Configured in `01-configmaps.yaml` (backend-config):
- `APP_NAME`, `APP_ENV`, `DEBUG`, `LOG_LEVEL`
- `API_PREFIX=/api/v1`, `API_PORT=8000`
- `CORS_ORIGINS=http://localhost:3000,http://localhost:8080`
- `SCHEDULER_ENABLED=true`, `SCHEDULER_TIMEZONE=UTC`
- `IN_CLUSTER=true` (enables in-cluster K8s client)

Configured in `02-secrets.yaml` (backend-secret):
- `DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres-service:5432/tenant_management`
- `KEYCLOAK_CLIENT_SECRET`, `KEYCLOAK_ADMIN_USERNAME`, `KEYCLOAK_ADMIN_PASSWORD`
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (empty, fill in if needed)

### Frontend Environment Variables

Configured in `01-configmaps.yaml` (frontend-config):
- `VITE_API_BASE_URL=http://localhost:8080`
- `VITE_KEYCLOAK_URL=http://localhost:8080/auth`
- `VITE_KEYCLOAK_REALM=saas-management`
- `VITE_KEYCLOAK_CLIENT_ID=tenant-management-portal`

### Database Configuration

Configured in `02-secrets.yaml` (postgres-secret):
- `POSTGRES_USER=postgres`
- `POSTGRES_PASSWORD=postgres`
- `POSTGRES_DB=tenant_management`

Storage:
- PVC size: 5Gi
- Storage class: standard
- Access mode: ReadWriteOnce

## 📊 Architecture

### Components

1. **Frontend (2 replicas)**
   - Image: tenant-management-frontend:latest
   - Nginx serving React SPA
   - Port: 80
   - Resources: 100m CPU / 128Mi RAM

2. **Backend (2 replicas)**
   - Image: tenant-management-backend:latest
   - FastAPI application
   - Port: 8000 (HTTP), 9090 (metrics)
   - Resources: 250m CPU / 512Mi RAM
   - ServiceAccount: tenant-manager (with K8s API access)

3. **PostgreSQL (1 replica)**
   - Image: postgres:16-alpine
   - Port: 5432
   - Resources: 250m CPU / 512Mi RAM
   - Storage: 5Gi PVC

4. **Ingress**
   - Controller: nginx
   - Routes: `/` → frontend, `/api` → backend

### Networking

```
External → Ingress → Frontend Service → Frontend Pods (Nginx)
                   ↓
                   Backend Service → Backend Pods (FastAPI)
                                   ↓
                                   PostgreSQL Service → PostgreSQL Pod
```

### RBAC Permissions

The backend ServiceAccount has permissions to:
- Get, List, Watch namespaces
- Get, List, Watch, Update, Patch deployments and statefulsets
- Get, List, Watch pods

This allows the portal to manage tenant deployments across namespaces.

## 📋 Access Methods

### 1. Port Forwarding (Development)

```bash
# Frontend
kubectl port-forward -n tenant-management svc/frontend-service 8080:80
# Access: http://localhost:8080

# Backend API
kubectl port-forward -n tenant-management svc/backend-service 8000:8000
# Access: http://localhost:8000/docs
```

### 2. Ingress (Production-like)

**Minikube:**
```bash
minikube ip  # Get IP (e.g., 192.168.49.2)
# Access: http://192.168.49.2
```

**Kind/Docker Desktop:**
```bash
# Access: http://localhost
```

### 3. Minikube Service

```bash
minikube service frontend-service -n tenant-management --url
```

## 🛠️ Common Operations

### View Logs

```bash
./deploy.sh logs

# Or manually:
kubectl logs -l app=backend -n tenant-management -f
kubectl logs -l app=frontend -n tenant-management -f
kubectl logs -l app=postgres -n tenant-management -f
```

### Restart Services

```bash
./deploy.sh restart

# Or manually:
kubectl rollout restart deployment/backend -n tenant-management
kubectl rollout restart deployment/frontend -n tenant-management
```

### Scale Services

```bash
kubectl scale deployment backend -n tenant-management --replicas=3
kubectl scale deployment frontend -n tenant-management --replicas=3
```

### Update After Code Changes

```bash
./deploy.sh build    # Rebuild images
./deploy.sh restart  # Restart deployments
```

### Database Access

```bash
kubectl port-forward -n tenant-management svc/postgres-service 5432:5432
psql -h localhost -U postgres -d tenant_management
# Password: postgres
```

### Check Status

```bash
./deploy.sh status

# Or manually:
kubectl get all -n tenant-management
kubectl get pvc -n tenant-management
kubectl get ingress -n tenant-management
```

### Clean Up

```bash
./deploy.sh delete

# Or manually:
kubectl delete namespace tenant-management
```

## 🔍 Verification

After deployment, verify:

```bash
# Check all pods are running
kubectl get pods -n tenant-management

# Expected:
# postgres-xxx          1/1     Running
# backend-xxx           1/1     Running
# backend-yyy           1/1     Running
# frontend-xxx          1/1     Running
# frontend-yyy          1/1     Running

# Check services
kubectl get svc -n tenant-management

# Expected:
# postgres-service      ClusterIP   10.x.x.x   5432/TCP
# backend-service       ClusterIP   10.x.x.x   8000/TCP,9090/TCP
# frontend-service      ClusterIP   10.x.x.x   80/TCP

# Test backend health
kubectl exec -n tenant-management deployment/backend -- curl -s http://localhost:8000/health

# Test frontend health
kubectl exec -n tenant-management deployment/frontend -- curl -s http://localhost:80/health
```

## 🐛 Troubleshooting

### ImagePullBackOff Error

```bash
# Rebuild and reload images
./deploy.sh build
```

### Pods Not Starting

```bash
# Check events
kubectl get events -n tenant-management --sort-by='.lastTimestamp'

# Describe pod
kubectl describe pod <pod-name> -n tenant-management

# Check logs
kubectl logs <pod-name> -n tenant-management
```

### Database Connection Issues

```bash
# Check postgres is running
kubectl get pods -n tenant-management -l app=postgres

# Check postgres logs
kubectl logs -l app=postgres -n tenant-management

# Verify service DNS
kubectl exec -n tenant-management deployment/backend -- \
  nslookup postgres-service
```

### Ingress Not Working

```bash
# Use port-forwarding instead
kubectl port-forward -n tenant-management svc/frontend-service 8080:80
```

## 🎯 Next Steps

1. **Access the application**: Use port-forwarding or ingress
2. **Create demo tenants**: Run `./create-demo-tenants.sh`
3. **Test functionality**: Start/stop tenants from the web UI
4. **Add real tenants**: Deploy your actual applications
5. **Configure authentication**: Set up Keycloak integration
6. **Enable monitoring**: Add Prometheus/Grafana
7. **Production deployment**: Deploy to cloud (EKS, GKE, AKS)

## 📝 Important Notes

1. **Image Pull Policy**: Set to `Never` for local development (images must be pre-loaded)
2. **Storage**: Using `standard` StorageClass - may vary by cluster type
3. **Secrets**: Default passwords are insecure - change for production
4. **RBAC**: Backend has ClusterRole for managing other namespaces
5. **Health Checks**: All components have liveness/readiness probes
6. **Resource Limits**: Configured for local development - adjust for production

## 🔐 Security Considerations

### For Production:

1. **Change default passwords** in `02-secrets.yaml`
2. **Use external secret management** (Vault, AWS Secrets Manager)
3. **Enable TLS** with cert-manager
4. **Add NetworkPolicies** to restrict pod communication
5. **Use private image registry** instead of `imagePullPolicy: Never`
6. **Enable pod security policies**
7. **Set up proper RBAC** with least privilege
8. **Enable audit logging**
9. **Use namespace isolation**
10. **Implement rate limiting** in ingress

## 📞 Support

All scripts are executable and include error handling. For issues:

1. Check script output for error messages
2. Review logs: `./deploy.sh logs`
3. Check pod status: `./deploy.sh status`
4. Review events: `kubectl get events -n tenant-management`
5. Consult [QUICKSTART.md](../QUICKSTART.md) or [k8s/README.md](README.md)

---

**Deployment Status**: ✅ Ready to deploy
**Last Updated**: December 2024
**Tested On**: Minikube 1.32, Kind 0.20, Docker Desktop 4.25
