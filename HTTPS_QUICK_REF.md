# 🔒 HTTPS - Quick Reference Card

## ✅ Status: ENABLED AND WORKING

**URL**: https://governance.mrtmcloud.com/tm/

## Quick Test
```bash
curl -I https://governance.mrtmcloud.com/tm/health
# Expected: HTTP/2 200
```

## Files & Documentation

| File | Description |
|------|-------------|
| **[HTTPS_ENABLED.md](HTTPS_ENABLED.md)** | 📋 Main summary & overview |
| **[k8s/HTTPS_STATUS.md](k8s/HTTPS_STATUS.md)** | 📊 Current status & what's done |
| **[k8s/HTTPS_QUICKSTART.md](k8s/HTTPS_QUICKSTART.md)** | ⚡ 5-minute setup guide |
| **[k8s/HTTPS_SETUP.md](k8s/HTTPS_SETUP.md)** | 📚 Comprehensive documentation |

## Scripts

| Script | Purpose |
|--------|---------|
| `k8s/verify-https.sh` | 🔍 Check HTTPS status |
| `k8s/setup-https.sh` | 🚀 Configure ACM certificate |

## Common Commands

```bash
# Verify HTTPS
./k8s/verify-https.sh

# Test endpoint
curl https://governance.mrtmcloud.com/tm/health

# Open in browser
open https://governance.mrtmcloud.com/tm/

# Check pods
kubectl get pods -n tenant-management

# Check gateway
kubectl get gateway -n tenant-management

# Check load balancer
kubectl get svc -n istio-system istio-ingressgateway
```

## Deployment Backups

All current Kubernetes resources saved in [k8s/](k8s/) directory:
- `current-deployment-state.yaml` (309KB) - Complete state
- `deployed-configmaps.yaml` (48KB)
- `deployed-deployments.yaml` (23KB)
- `deployed-services.yaml` (5.2KB)
- `deployed-istio-resources.yaml` (9.7KB)
- `deployed-secrets.yaml` (3.1KB)
- `deployed-istio-ingress.yaml` (4.5KB)

## Optional Next Steps

1. **Add ACM Certificate**: `./k8s/setup-https.sh`
2. **Update ConfigMaps**: `kubectl apply -f k8s/eks-manifests/01-configmaps-https.yaml`
3. **Enable HTTPS Redirect**: See [HTTPS_SETUP.md](k8s/HTTPS_SETUP.md)
4. **Add Security Headers**: See [HTTPS_SETUP.md](k8s/HTTPS_SETUP.md)

## Need Help?

1. Run verification: `./k8s/verify-https.sh`
2. Check documentation: [HTTPS_ENABLED.md](HTTPS_ENABLED.md)
3. View logs: `kubectl logs -n tenant-management -l app=backend --tail=50`

---
**Last Updated**: January 5, 2026
