# Kubernetes Tenant Management Portal - Quick Start Guide

Complete guide to deploy and run the application in a local Kubernetes cluster.

## 📋 Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Deploy (Automated)](#quick-deploy-automated)
- [Step-by-Step Deploy (Manual)](#step-by-step-deploy-manual)
- [Accessing the Application](#accessing-the-application)
- [Creating Demo Tenants](#creating-demo-tenants)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### 1. Install Required Tools

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install kubectl
brew install kubectl

# Install Docker Desktop
brew install --cask docker
# Then start Docker Desktop from Applications

# Choose ONE Kubernetes distribution:

# Option A: Minikube (Recommended)
brew install minikube

# Option B: Kind
brew install kind

# Option C: Docker Desktop Kubernetes
# Enable in Docker Desktop: Preferences → Kubernetes → Enable Kubernetes
```

### 2. Start Kubernetes Cluster

```bash
cd /Users/comviva/Documents/Code/ManageAWS/k8s

# Automated setup (recommended)
./setup-cluster.sh

# Or manual setup:

# For Minikube:
minikube start --driver=docker --cpus=4 --memory=8192 --disk-size=20g
minikube addons enable ingress
minikube addons enable metrics-server

# For Kind:
kind create cluster --name tenant-management

# For Docker Desktop:
# Just enable Kubernetes in preferences
```

---

## Quick Deploy (Automated)

### One-Command Deploy

```bash
cd /Users/comviva/Documents/Code/ManageAWS/k8s
./deploy.sh all
```

This will:
1. ✅ Check prerequisites
2. ✅ Build Docker images (backend + frontend)
3. ✅ Load images into cluster
4. ✅ Apply all Kubernetes manifests
5. ✅ Run database migrations
6. ✅ Seed initial data
7. ✅ Display access information

### Expected Output

```
[INFO] Checking prerequisites...
[INFO] Prerequisites check passed ✓
[INFO] Building Docker images...
[INFO] Building backend image...
[INFO] Building frontend image...
[INFO] Loading images into minikube...
[INFO] Docker images built successfully ✓
[INFO] Applying Kubernetes manifests...
[INFO] Waiting for PostgreSQL to be ready...
[INFO] Running database migrations...
[INFO] Migrations completed successfully ✓
[INFO] Kubernetes manifests applied successfully ✓
```

---

## Step-by-Step Deploy (Manual)

### Step 1: Build Docker Images

```bash
cd /Users/comviva/Documents/Code/ManageAWS

# Backend
docker build -t tenant-management-backend:latest ./backend

# Frontend
docker build -t tenant-management-frontend:latest ./frontend
```

### Step 2: Load Images into Cluster

```bash
# For Minikube
minikube image load tenant-management-backend:latest
minikube image load tenant-management-frontend:latest

# For Kind
kind load docker-image tenant-management-backend:latest
kind load docker-image tenant-management-frontend:latest

# For Docker Desktop
# Images are automatically available
```

### Step 3: Apply Kubernetes Manifests

```bash
cd k8s

# 1. Create namespace
kubectl apply -f 00-namespace.yaml

# 2. Create ConfigMaps and Secrets
kubectl apply -f 01-configmaps.yaml
kubectl apply -f 02-secrets.yaml

# 3. Deploy PostgreSQL
kubectl apply -f 03-postgres.yaml

# Wait for PostgreSQL to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n tenant-management --timeout=300s

# 4. Apply RBAC permissions
kubectl apply -f 04-rbac.yaml

# 5. Deploy Backend
kubectl apply -f 05-backend.yaml

# 6. Deploy Frontend
kubectl apply -f 06-frontend.yaml

# 7. Create Ingress
kubectl apply -f 07-ingress.yaml
```

### Step 4: Run Database Migrations

```bash
# Get backend pod name
BACKEND_POD=$(kubectl get pods -n tenant-management -l app=backend -o jsonpath='{.items[0].metadata.name}')

# Run migrations
kubectl exec -it $BACKEND_POD -n tenant-management -- alembic upgrade head

# Seed initial data
kubectl exec -it $BACKEND_POD -n tenant-management -- python scripts/init_db.py
```

### Step 5: Verify Deployment

```bash
# Check all resources
kubectl get all -n tenant-management

# Expected output:
# - 1 PostgreSQL pod (Running)
# - 2 Backend pods (Running)
# - 2 Frontend pods (Running)
# - 3 Services
# - 1 Ingress
```

---

## Accessing the Application

### Option 1: Port Forwarding (Easiest)

```bash
# Terminal 1: Frontend
kubectl port-forward -n tenant-management svc/frontend-service 8080:80

# Terminal 2: Backend API (optional)
kubectl port-forward -n tenant-management svc/backend-service 8000:8000
```

**Access:**
- Frontend: http://localhost:8080
- Backend API Docs: http://localhost:8000/docs
- Backend Health: http://localhost:8000/health

### Option 2: Ingress (Production-like)

#### For Minikube:

```bash
# Get Minikube IP
minikube ip
# Example: 192.168.49.2

# Access application
open http://$(minikube ip)
```

#### For Kind:

```bash
# Install ingress-nginx (if not already installed)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

# Access application
open http://localhost
```

#### For Docker Desktop:

```bash
# Install ingress-nginx
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.4/deploy/static/provider/cloud/deploy.yaml

# Wait for ingress controller
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s

# Access application
open http://localhost
```

### Option 3: Minikube Service (Minikube Only)

```bash
minikube service frontend-service -n tenant-management
```

---

## Creating Demo Tenants

Create sample tenant namespaces for testing:

```bash
cd k8s
./create-demo-tenants.sh
```

This creates:
- `tenant-acme` namespace with nginx deployment
- `tenant-globex` namespace with nginx deployment
- `tenant-initech` namespace with nginx deployment

**Verify:**

```bash
kubectl get namespaces | grep tenant-
kubectl get deployments -n tenant-acme
```

---

## Common Tasks

### View Application Logs

```bash
# Backend logs
kubectl logs -l app=backend -n tenant-management --tail=100 -f

# Frontend logs
kubectl logs -l app=frontend -n tenant-management --tail=100 -f

# PostgreSQL logs
kubectl logs -l app=postgres -n tenant-management --tail=100 -f

# All logs with script
cd k8s
./deploy.sh logs
```

### Restart Services

```bash
# Restart all
cd k8s
./deploy.sh restart

# Or manually
kubectl rollout restart deployment/backend -n tenant-management
kubectl rollout restart deployment/frontend -n tenant-management
```

### Scale Deployments

```bash
# Scale backend to 3 replicas
kubectl scale deployment backend -n tenant-management --replicas=3

# Scale frontend to 3 replicas
kubectl scale deployment frontend -n tenant-management --replicas=3
```

### Update Application After Code Changes

```bash
cd k8s

# Rebuild images
./deploy.sh build

# Restart to use new images
./deploy.sh restart
```

### Access PostgreSQL Database

```bash
# Port forward
kubectl port-forward -n tenant-management svc/postgres-service 5432:5432

# Connect with psql (in another terminal)
psql -h localhost -U postgres -d tenant_management
# Password: postgres
```

### Execute Commands in Pods

```bash
# Backend shell
kubectl exec -it deployment/backend -n tenant-management -- /bin/bash

# Run Python in backend
kubectl exec -it deployment/backend -n tenant-management -- python

# PostgreSQL shell
kubectl exec -it deployment/postgres -n tenant-management -- psql -U postgres -d tenant_management
```

### View Resource Usage

```bash
# Pod resource usage
kubectl top pods -n tenant-management

# Node resource usage
kubectl top nodes
```

### Check Deployment Status

```bash
# Detailed status
cd k8s
./deploy.sh status

# Watch pods
kubectl get pods -n tenant-management -w

# Describe problematic pod
kubectl describe pod <pod-name> -n tenant-management
```

### Delete Everything

```bash
# Delete all resources
cd k8s
./deploy.sh delete

# Or manually
kubectl delete namespace tenant-management
```

---

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl get pods -n tenant-management

# Describe pod
kubectl describe pod <pod-name> -n tenant-management

# Check logs
kubectl logs <pod-name> -n tenant-management

# Check events
kubectl get events -n tenant-management --sort-by='.lastTimestamp'
```

**Common issues:**
- **ImagePullBackOff**: Images not loaded into cluster
  ```bash
  ./deploy.sh build  # Rebuild and reload images
  ```
- **CrashLoopBackOff**: Check logs for application errors
  ```bash
  kubectl logs <pod-name> -n tenant-management --previous
  ```

### Database Connection Issues

```bash
# Check PostgreSQL pod
kubectl get pods -n tenant-management -l app=postgres

# Check PostgreSQL logs
kubectl logs -l app=postgres -n tenant-management

# Test connection from backend
kubectl exec -it deployment/backend -n tenant-management -- \
  python -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('postgresql://postgres:postgres@postgres-service:5432/tenant_management'))"
```

### Backend API Not Responding

```bash
# Check backend pods
kubectl get pods -n tenant-management -l app=backend

# Check backend logs
kubectl logs -l app=backend -n tenant-management --tail=100

# Test health endpoint
kubectl exec -it deployment/backend -n tenant-management -- \
  curl http://localhost:8000/health
```

### Frontend Not Loading

```bash
# Check frontend pods
kubectl get pods -n tenant-management -l app=frontend

# Check frontend logs
kubectl logs -l app=frontend -n tenant-management --tail=100

# Test nginx health
kubectl exec -it deployment/frontend -n tenant-management -- \
  curl http://localhost:80/health
```

### Ingress Not Working

```bash
# Check ingress controller
kubectl get pods -n ingress-nginx

# Check ingress resource
kubectl describe ingress tenant-management-ingress -n tenant-management

# Alternative: Use port-forwarding
kubectl port-forward -n tenant-management svc/frontend-service 8080:80
```

### Cluster Issues

```bash
# Minikube
minikube status
minikube logs

# Kind
kind get clusters
docker ps  # Check if kind containers are running

# Docker Desktop
# Check Docker Desktop → Preferences → Kubernetes
```

---

## Development Workflow

### 1. Make Code Changes

Edit files in `backend/` or `frontend/`

### 2. Rebuild Images

```bash
cd k8s
./deploy.sh build
```

### 3. Restart Deployments

```bash
./deploy.sh restart
```

### 4. Watch Logs

```bash
# In another terminal
kubectl logs -l app=backend -n tenant-management -f
```

### 5. Test Changes

Access http://localhost:8080 or your ingress URL

---

## Next Steps

1. **Configure Authentication**: Set up Keycloak integration
2. **Add Real Tenants**: Deploy actual applications to manage
3. **Enable Monitoring**: Add Prometheus + Grafana
4. **Set Up CI/CD**: Automate deployments with GitHub Actions
5. **Production Deployment**: Deploy to EKS, GKE, or AKS

---

## Useful Commands Reference

```bash
# Deploy everything
./deploy.sh all

# Build images only
./deploy.sh build

# Apply manifests only
./deploy.sh apply

# Check status
./deploy.sh status

# View logs
./deploy.sh logs

# Restart services
./deploy.sh restart

# Delete everything
./deploy.sh delete

# Create demo tenants
./create-demo-tenants.sh

# Setup cluster
./setup-cluster.sh
```

---

## Architecture Overview

```
┌───────────────────────────────────────┐
│        Ingress Controller             │
│         (localhost:80)                │
└────────────┬──────────────────────────┘
             │
     ┌───────┴────────┐
     │                │
┌────▼─────┐    ┌────▼─────┐
│ Frontend │    │ Backend  │
│ Service  │    │ Service  │
│   :80    │    │  :8000   │
└────┬─────┘    └────┬─────┘
     │               │
┌────▼─────┐    ┌────▼─────┐
│ Frontend │    │ Backend  │
│   Pod    │    │   Pod    │
│  Nginx   │    │ FastAPI  │
└──────────┘    └────┬─────┘
                     │
               ┌─────▼──────┐
               │ PostgreSQL │
               │  Service   │
               │   :5432    │
               └─────┬──────┘
                     │
               ┌─────▼──────┐
               │ PostgreSQL │
               │    Pod     │
               │    +PVC    │
               └────────────┘
```

---

## Support

For issues or questions:
1. Check logs: `./deploy.sh logs`
2. Check status: `./deploy.sh status`
3. Review events: `kubectl get events -n tenant-management`
4. Check this guide's troubleshooting section
