# Istio Integration for Tenant Management Application

## Overview
This directory contains Istio service mesh resources for exposing the tenant management application through AWS ALB.

## Resources

### 1. Gateway (`01-gateway.yaml`)
- Defines ingress gateway entry point
- Configures HTTP (port 80) and HTTPS (port 443) listeners
- Uses Istio's default ingress gateway selector

### 2. VirtualService (`02-virtualservice.yaml`)
- Routes traffic to backend and frontend services
- **Backend routes:**
  - `/api/v1/*` → backend:8000
  - `/health` → backend:8000
  - `/metrics` → backend:9090
- **Frontend routes:**
  - `/` → frontend:80 (SPA routing)

### 3. DestinationRules (`03-destinationrules.yaml`)
- **Backend:** LEAST_REQUEST load balancing with connection pooling and outlier detection
- **Frontend:** ROUND_ROBIN load balancing with connection pooling

### 4. Ingress Service (`04-ingress-service.yaml`)
- AWS Network Load Balancer configuration
- External-facing internet scheme
- IP target type for pod direct routing
- Cross-zone load balancing enabled

### 5. PeerAuthentication (`05-peer-authentication.yaml`)
- Configures mTLS mode as PERMISSIVE
- Allows gradual migration from plain text to mTLS

## Deployment

### Prerequisites
1. Istio must be installed in the cluster
2. Istio sidecar injection enabled for tenant-management namespace:
   ```bash
   kubectl label namespace tenant-management istio-injection=enabled
   ```

### Apply Resources
```bash
# Apply all Istio resources
kubectl apply -f k8s/istio/

# Verify gateway
kubectl get gateway -n tenant-management

# Verify virtual service
kubectl get virtualservice -n tenant-management

# Verify destination rules
kubectl get destinationrule -n tenant-management

# Check ingress gateway service
kubectl get svc istio-ingressgateway -n istio-system
```

### Restart Pods (for sidecar injection)
```bash
kubectl rollout restart deployment/backend -n tenant-management
kubectl rollout restart deployment/frontend -n tenant-management
kubectl rollout restart deployment/postgres -n tenant-management
```

## Verification

### Check Istio Sidecars
```bash
# Verify pods have 2/2 containers (app + sidecar)
kubectl get pods -n tenant-management

# Check sidecar injection status
kubectl get pod <pod-name> -n tenant-management -o jsonpath='{.spec.containers[*].name}'
```

### Get ALB Endpoint
```bash
# Get Load Balancer DNS
kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

### Test Application
```bash
# Get ALB URL
ALB_URL=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Test backend API
curl http://$ALB_URL/api/v1/health

# Test frontend
curl http://$ALB_URL/

# Access in browser
open http://$ALB_URL
```

## Traffic Management

### Gradual Rollout
The DestinationRule includes outlier detection to automatically remove unhealthy pods from the load balancer pool:
- **consecutiveErrors:** 5 errors trigger ejection
- **interval:** Check every 30s
- **baseEjectionTime:** Eject for 30s minimum
- **maxEjectionPercent:** Maximum 50% of pods can be ejected

### Connection Pooling
- **TCP max connections:** 100
- **HTTP/1.1 max pending requests:** 50
- **HTTP/2 max requests:** 100
- **Max requests per connection:** 2 (backend only)

## AWS ALB Configuration

The ingress gateway service uses AWS Load Balancer Controller annotations:
- **Type:** Network Load Balancer (NLB)
- **Target Type:** IP (direct pod routing)
- **Scheme:** internet-facing
- **Cross-zone:** Enabled for high availability

## Security

### mTLS Configuration
Current mode: **PERMISSIVE**
- Allows both mTLS and plain text traffic
- Recommended for initial deployment
- Switch to STRICT mode after validation:
  ```yaml
  spec:
    mtls:
      mode: STRICT
  ```

### TLS Termination
- Configure AWS Certificate Manager (ACM) certificate
- Update Gateway credentialName with certificate secret
- Enable HTTPS-only access

## Monitoring

### Istio Observability
```bash
# View traffic in Kiali (if installed)
kubectl port-forward svc/kiali -n istio-system 20001:20001

# View metrics in Grafana (if installed)
kubectl port-forward svc/grafana -n istio-system 3000:3000

# View traces in Jaeger (if installed)
kubectl port-forward svc/jaeger-query -n istio-system 16686:16686
```

### Application Metrics
Backend exposes Prometheus metrics on `/metrics` endpoint (port 9090)

## Troubleshooting

### Pods not getting sidecars
```bash
# Check namespace label
kubectl get namespace tenant-management --show-labels

# Enable injection
kubectl label namespace tenant-management istio-injection=enabled --overwrite

# Restart deployments
kubectl rollout restart deployment -n tenant-management
```

### Gateway not routing
```bash
# Check gateway status
kubectl describe gateway tenant-management-gateway -n tenant-management

# Check virtual service
kubectl describe virtualservice tenant-management-vs -n tenant-management

# Check ingress gateway logs
kubectl logs -n istio-system -l istio=ingressgateway
```

### ALB not provisioned
```bash
# Check AWS Load Balancer Controller logs
kubectl logs -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller

# Verify service annotations
kubectl describe svc istio-ingressgateway -n istio-system
```

## Next Steps

1. ✅ Enable Istio sidecar injection for namespace
2. ✅ Apply Istio resources
3. ✅ Restart pods for sidecar injection
4. ⏳ Verify ALB provisioning
5. ⏳ Test application through ALB
6. ⏳ Configure custom domain with Route53
7. ⏳ Add ACM certificate for HTTPS
8. ⏳ Switch to STRICT mTLS mode
