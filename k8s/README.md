# Kubernetes Deployment Guide

## Prerequisites

1. **Kubernetes Cluster**: You need a running Kubernetes cluster. Choose one:
   - **Minikube**: `brew install minikube && minikube start`
   - **Kind**: `brew install kind && kind create cluster`
   - **Docker Desktop**: Enable Kubernetes in Docker Desktop preferences

2. **kubectl**: Kubernetes CLI tool
   ```bash
   brew install kubectl
   ```

3. **Docker**: For building images
   ```bash
   brew install --cask docker
   ```

## Quick Start

### 1. Build and Deploy Everything

```bash
cd k8s
chmod +x deploy.sh
./deploy.sh all
```

This will:
- Check prerequisites
- Build Docker images for backend and frontend
- Apply all Kubernetes manifests
- Run database migrations
- Seed initial data
- Display access information

### 2. Access the Application

#### Option 1: Port Forwarding (Recommended for local dev)

```bash
# Frontend
kubectl port-forward -n tenant-management svc/frontend-service 8080:80

# Backend API (in another terminal)
kubectl port-forward -n tenant-management svc/backend-service 8000:8000
```

Then access:
- Frontend: http://localhost:8080
- Backend API Docs: http://localhost:8000/docs

#### Option 2: Ingress (Requires ingress controller)

**For Minikube:**
```bash
minikube addons enable ingress
minikube ip  # Note the IP address
```
Access at: http://<minikube-ip>

**For Kind:**
```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
```
Access at: http://localhost

**For Docker Desktop:**
```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.4/deploy/static/provider/cloud/deploy.yaml
```
Access at: http://localhost

## Manual Deployment Steps

### 1. Build Docker Images

```bash
# Backend
cd backend
docker build -t tenant-management-backend:latest .

# Frontend
cd ../frontend
docker build -t tenant-management-frontend:latest .
```

### 2. Load Images into Cluster

**For Minikube:**
```bash
minikube image load tenant-management-backend:latest
minikube image load tenant-management-frontend:latest
```

**For Kind:**
```bash
kind load docker-image tenant-management-backend:latest
kind load docker-image tenant-management-frontend:latest
```

**For Docker Desktop:** No need to load images

### 3. Apply Kubernetes Manifests

```bash
cd k8s

# Apply in order
kubectl apply -f 00-namespace.yaml
kubectl apply -f 01-configmaps.yaml
kubectl apply -f 02-secrets.yaml
kubectl apply -f 03-postgres.yaml
kubectl apply -f 04-rbac.yaml

# Wait for postgres to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n tenant-management --timeout=300s

# Apply backend and frontend
kubectl apply -f 05-backend.yaml
kubectl apply -f 06-frontend.yaml
kubectl apply -f 07-ingress.yaml
```

### 4. Run Database Migrations

```bash
# Get backend pod name
BACKEND_POD=$(kubectl get pods -n tenant-management -l app=backend -o jsonpath='{.items[0].metadata.name}')

# Run migrations
kubectl exec -it $BACKEND_POD -n tenant-management -- alembic upgrade head

# Seed initial data
kubectl exec -it $BACKEND_POD -n tenant-management -- python scripts/init_db.py
```

## Useful Commands

### Check Deployment Status

```bash
./deploy.sh status

# Or manually
kubectl get all -n tenant-management
kubectl get pods -n tenant-management -w  # Watch pods
```

### View Logs

```bash
./deploy.sh logs

# Or manually
kubectl logs -l app=backend -n tenant-management --tail=100 -f
kubectl logs -l app=frontend -n tenant-management --tail=100 -f
kubectl logs -l app=postgres -n tenant-management --tail=100 -f
```

### Restart Services

```bash
./deploy.sh restart

# Or manually
kubectl rollout restart deployment/backend -n tenant-management
kubectl rollout restart deployment/frontend -n tenant-management
```

### Scale Deployments

```bash
# Scale backend
kubectl scale deployment backend -n tenant-management --replicas=3

# Scale frontend
kubectl scale deployment frontend -n tenant-management --replicas=3
```

### Delete Everything

```bash
./deploy.sh delete

# Or manually
kubectl delete namespace tenant-management
```

### Access PostgreSQL Database

```bash
# Port forward to postgres
kubectl port-forward -n tenant-management svc/postgres-service 5432:5432

# Connect with psql
psql -h localhost -U postgres -d tenant_management
# Password: postgres
```

### Execute Commands in Pods

```bash
# Backend pod
kubectl exec -it deployment/backend -n tenant-management -- /bin/bash

# Postgres pod
kubectl exec -it deployment/postgres -n tenant-management -- /bin/bash
```

## Configuration

### Environment Variables

Edit ConfigMaps and Secrets:

```bash
# Edit backend config
kubectl edit configmap backend-config -n tenant-management

# Edit secrets (base64 encoded)
kubectl edit secret backend-secret -n tenant-management

# Apply changes (restart required)
kubectl rollout restart deployment/backend -n tenant-management
```

### Update Images

After making code changes:

```bash
# Rebuild images
./deploy.sh build

# Restart deployments to use new images
./deploy.sh restart
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Ingress Controller                    │
│                    (localhost:80)                        │
└────────────┬────────────────────────────┬────────────────┘
             │                            │
         ┌───▼────┐                  ┌────▼────┐
         │Frontend│                  │ Backend │
         │Service │                  │ Service │
         │ :80    │                  │  :8000  │
         └───┬────┘                  └────┬────┘
             │                            │
      ┌──────▼──────┐              ┌──────▼──────┐
      │  Frontend   │              │   Backend   │
      │ Deployment  │              │ Deployment  │
      │ (2 replicas)│              │ (2 replicas)│
      │   Nginx     │              │   FastAPI   │
      └─────────────┘              └──────┬──────┘
                                          │
                                    ┌─────▼─────┐
                                    │PostgreSQL │
                                    │ Service   │
                                    │   :5432   │
                                    └─────┬─────┘
                                          │
                                    ┌─────▼─────┐
                                    │PostgreSQL │
                                    │Deployment │
                                    │    +      │
                                    │    PVC    │
                                    │   (5Gi)   │
                                    └───────────┘
```

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl get pods -n tenant-management

# Describe problematic pod
kubectl describe pod <pod-name> -n tenant-management

# Check events
kubectl get events -n tenant-management --sort-by='.lastTimestamp'
```

### Image Pull Errors

For local development, ensure `imagePullPolicy: Never` is set in deployments.

```bash
# Verify images are loaded (minikube)
minikube image ls | grep tenant-management

# Reload images
./deploy.sh build
```

### Database Connection Issues

```bash
# Check postgres pod
kubectl get pods -n tenant-management -l app=postgres

# Check postgres logs
kubectl logs -l app=postgres -n tenant-management

# Test connection from backend
kubectl exec -it deployment/backend -n tenant-management -- \
  python -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('postgresql://postgres:postgres@postgres-service:5432/tenant_management'))"
```

### Ingress Not Working

```bash
# Check ingress controller is running
kubectl get pods -n ingress-nginx

# Check ingress resource
kubectl describe ingress tenant-management-ingress -n tenant-management

# Use port-forwarding as alternative
kubectl port-forward -n tenant-management svc/frontend-service 8080:80
```

### Permission Issues (RBAC)

The backend needs permissions to manage deployments in other namespaces:

```bash
# Verify ServiceAccount
kubectl get serviceaccount tenant-manager -n tenant-management

# Verify ClusterRole
kubectl describe clusterrole tenant-manager-role

# Verify ClusterRoleBinding
kubectl describe clusterrolebinding tenant-manager-binding
```

## Monitoring

### Resource Usage

```bash
# Check resource usage
kubectl top pods -n tenant-management
kubectl top nodes
```

### Health Checks

```bash
# Backend health
kubectl exec -it deployment/backend -n tenant-management -- curl http://localhost:8000/health

# Frontend health
kubectl exec -it deployment/frontend -n tenant-management -- curl http://localhost:80/health
```

## Production Considerations

1. **Secrets Management**: Use external secret managers (Vault, AWS Secrets Manager)
2. **Persistent Storage**: Use StorageClass with proper backup policies
3. **High Availability**: Increase replicas and use pod anti-affinity
4. **Resource Limits**: Adjust CPU/memory based on load testing
5. **Monitoring**: Add Prometheus + Grafana
6. **Logging**: Centralize logs with EFK stack
7. **TLS**: Enable HTTPS with cert-manager
8. **Network Policies**: Restrict pod-to-pod communication
9. **Image Registry**: Push images to private registry
10. **CI/CD**: Automate deployments with GitOps (ArgoCD, Flux)

## Next Steps

1. **Create Test Tenants**: Deploy sample applications in different namespaces
2. **Configure Keycloak**: Set up authentication and authorization
3. **Enable Metrics**: Add Prometheus metrics endpoint
4. **Set Up Alerts**: Configure alerting for critical issues
5. **Load Testing**: Test with multiple concurrent users
