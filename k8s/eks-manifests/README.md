# EKS Deployment with Istio

## Architecture

```
Internet → AWS ALB → Istio Ingress Gateway (NodePort) → Istio Gateway → VirtualService → Services → Pods
```

Your EKS cluster already has:
- ✅ Istio installed
- ✅ Istio Ingress Gateway deployed
- ✅ AWS ALB configured to route to Istio Ingress Gateway

## Deployment Files

### Core Application (Deploy these)
1. `00-namespace.yaml` - Creates tenant-management namespace
2. `01-configmaps.yaml` - Application configuration
3. `02-secrets.yaml` - Sensitive data (database, Keycloak)
4. `03-postgres.yaml` - PostgreSQL database
5. `04-rbac.yaml` - Service account and permissions
6. `05-backend.yaml` - Backend API deployment & service
7. `06-frontend.yaml` - Frontend deployment & service

### Istio Routing (Deploy these)
8. `07-istio-gateway.yaml` - Istio Gateway (connects to existing ingress gateway)
9. `08-istio-virtualservice.yaml` - Routes traffic to backend/frontend
10. `09-istio-destinationrules.yaml` - Load balancing and circuit breaking

### ⚠️ Do NOT Deploy
- ~~`07-ingress.yaml`~~ - Not needed (using Istio instead)
- ~~`k8s/istio/04-ingress-service.yaml`~~ - Already exists in your cluster

## Prerequisites

1. **Enable Istio sidecar injection** for the namespace:
   ```bash
   kubectl label namespace tenant-management istio-injection=enabled
   ```

2. **Verify existing Istio Ingress Gateway**:
   ```bash
   kubectl get svc -n istio-system istio-ingressgateway
   ```

## Deployment Steps

### 1. Label namespace for Istio injection
```bash
kubectl label namespace tenant-management istio-injection=enabled --overwrite
```

### 2. Deploy application resources
```bash
cd /Users/comviva/Documents/Code/ManageAWS/k8s/eks-manifests

# Deploy in order
kubectl apply -f 00-namespace.yaml
kubectl apply -f 01-configmaps.yaml
kubectl apply -f 02-secrets.yaml
kubectl apply -f 03-postgres.yaml
kubectl apply -f 04-rbac.yaml
kubectl apply -f 05-backend.yaml
kubectl apply -f 06-frontend.yaml
```

### 3. Deploy Istio routing
```bash
kubectl apply -f 07-istio-gateway.yaml
kubectl apply -f 08-istio-virtualservice.yaml
kubectl apply -f 09-istio-destinationrules.yaml
```

### 4. Verify deployment
```bash
# Check pods (should show 2/2 containers - app + istio-proxy)
kubectl get pods -n tenant-management

# Check Istio resources
kubectl get gateway,virtualservice,destinationrule -n tenant-management

# Check services
kubectl get svc -n tenant-management
```

## Accessing the Application

### Get ALB URL
Your existing ALB should route traffic to the Istio Ingress Gateway. 

If you need to find the ALB endpoint:
```bash
# Get Istio Ingress Gateway service
kubectl get svc istio-ingressgateway -n istio-system

# Or check your ALB configuration
aws elbv2 describe-load-balancers --query 'LoadBalancers[*].[LoadBalancerName,DNSName]' --output table
```

### Test the Application
```bash
# Replace <ALB_DNS> with your ALB DNS name
ALB_DNS="your-alb-name.region.elb.amazonaws.com"

# Test backend API (note the /tm prefix)
curl http://$ALB_DNS/tm/api/v1/health

# Test health endpoint
curl http://$ALB_DNS/tm/health

# Access frontend in browser
open http://$ALB_DNS/tm
```

## Traffic Flow

1. **HTTP Request** → AWS ALB
2. **ALB** → Istio Ingress Gateway (via NodePort/TargetGroup)
3. **Istio Gateway** → Matches `tenant-management-gateway`
4. **VirtualService** → Routes based on path (all prefixed with `/tm`):
   - `/tm/api/v1/*` → backend-service:8000
   - `/tm/health` → backend-service:8000
   - `/tm/metrics` → backend-service:9090
   - `/tm/docs`, `/tm/redoc` → backend-service:8000
   - `/tm/` → frontend-service:80
5. **Service** → Backend/Frontend Pods
6. **Istio Sidecar** → Handles mTLS, metrics, tracing

## Verification Commands

```bash
# Check if sidecar injection is enabled
kubectl get namespace tenant-management -o jsonpath='{.metadata.labels.istio-injection}'

# Verify pods have sidecars (2/2 containers)
kubectl get pods -n tenant-management

# Check Istio configuration
kubectl get gateway,virtualservice,destinationrule -n tenant-management

# View Istio proxy logs
kubectl logs -n tenant-management <pod-name> -c istio-proxy

# Check backend logs
kubectl logs -n tenant-management -l app=backend -c backend

# Check frontend logs
kubectl logs -n tenant-management -l app=frontend -c frontend
```

## Troubleshooting

### Pods stuck in Init or not 2/2
```bash
# Check if namespace has istio-injection label
kubectl get ns tenant-management --show-labels

# Enable injection if missing
kubectl label namespace tenant-management istio-injection=enabled --overwrite

# Restart deployments to inject sidecars
kubectl rollout restart deployment -n tenant-management
```

### 404 or routing issues
```bash
# Check VirtualService routes
kubectl get virtualservice tenant-management-vs -n tenant-management -o yaml

# Check Gateway
kubectl get gateway tenant-management-gateway -n tenant-management -o yaml

# Verify services exist
kubectl get svc -n tenant-management
```

### Can't reach application
```bash
# Verify Istio Ingress Gateway is running
kubectl get pods -n istio-system -l istio=ingressgateway

# Check if ALB targets are healthy
aws elbv2 describe-target-health --target-group-arn <your-target-group-arn>

# Port-forward directly to test (bypass Istio)
kubectl port-forward -n tenant-management svc/backend-service 8000:8000
kubectl port-forward -n tenant-management svc/frontend-service 8080:80
```

## Path Routing Summary

**All routes are prefixed with `/tm` to segregate this application from others.**

| Path | Service | Port | Purpose |
|------|---------|------|---------|
| `/tm/api/v1/*` | backend-service | 8000 | API endpoints |
| `/tm/health` | backend-service | 8000 | Health check |
| `/tm/metrics` | backend-service | 9090 | Prometheus metrics |
| `/tm/docs` | backend-service | 8000 | API documentation |
| `/tm/redoc` | backend-service | 8000 | API documentation (alt) |
| `/tm/openapi.json` | backend-service | 8000 | OpenAPI spec |
| `/tm/` | frontend-service | 80 | Frontend SPA |
| `/tm` | redirect | - | Redirects to `/tm/` |

## Update CORS if Needed

If your ALB has a specific domain, update CORS in ConfigMap:

```yaml
# In 01-configmaps.yaml
CORS_ORIGINS: "https://your-domain.com,http://your-alb.elb.amazonaws.com"
```

Then apply:
```bash
kubectl apply -f 01-configmaps.yaml
kubectl rollout restart deployment/backend -n tenant-management
```
