# HTTPS Quick Start Guide

## Quick Setup (5 minutes)

### Step 1: Run the automated setup script

```bash
cd /Users/comviva/Documents/Code/ManageAWS
./k8s/setup-https.sh
```

The script will:
1. List available ACM certificates
2. Let you choose or request a certificate
3. Update the Istio ingress gateway with SSL
4. Apply the updated Gateway configuration
5. Test HTTP and HTTPS endpoints

### Step 2: Choose a certificate

When prompted, select option 1 and use one of these certificates:

**For `*.comviva.mrtmcloud.com` domains:**
```
arn:aws:acm:ap-south-1:122610483530:certificate/a23a0c58-50d9-45a7-aa03-443adabea971
```

**For `*.demo.pm.mrtmcloud.com` domains:**
```
arn:aws:acm:ap-south-1:122610483530:certificate/511ea75e-7ccd-4388-885a-9a1583f69521
```

### Step 3: Update ConfigMaps for HTTPS (optional but recommended)

```bash
# Apply HTTPS-enabled configmaps
kubectl apply -f k8s/eks-manifests/01-configmaps-https.yaml

# Restart deployments to pick up new config
kubectl rollout restart deployment backend frontend -n tenant-management

# Wait for deployments to complete
kubectl rollout status deployment backend frontend -n tenant-management
```

### Step 4: Verify HTTPS is working

```bash
# Test HTTPS health endpoint
curl -k https://governance.mrtmcloud.com/tm/health

# Test in browser
open https://governance.mrtmcloud.com/tm/
```

## Manual Setup (if script doesn't work)

### 1. Update Istio Ingress Gateway Service

```bash
kubectl edit svc istio-ingressgateway -n istio-system
```

Add these annotations (replace `YOUR_CERT_ARN` with actual ARN):

```yaml
metadata:
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: "arn:aws:acm:ap-south-1:122610483530:certificate/YOUR_CERT_ARN"
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: "443"
```

### 2. Apply Gateway Configuration

```bash
kubectl apply -f k8s/eks-manifests/07-istio-gateway.yaml
```

### 3. Wait and test

```bash
# Wait 3-5 minutes for NLB to update
sleep 180

# Test HTTPS
curl -k https://governance.mrtmcloud.com/tm/health
```

## Enable Force HTTPS Redirect

To redirect all HTTP traffic to HTTPS:

```bash
kubectl patch gateway tenant-management-gateway -n tenant-management --type='json' -p='[
  {
    "op": "add",
    "path": "/spec/servers/0/tls",
    "value": {"httpsRedirect": true}
  }
]'
```

## Troubleshooting

### HTTPS not working?

1. **Check certificate status:**
   ```bash
   aws acm describe-certificate \
     --certificate-arn arn:aws:acm:ap-south-1:122610483530:certificate/YOUR_CERT_ARN \
     --region ap-south-1 \
     --query 'Certificate.Status'
   ```
   Should return: `"ISSUED"`

2. **Check load balancer listeners:**
   ```bash
   kubectl describe svc istio-ingressgateway -n istio-system | grep -A 10 Annotations
   ```

3. **Check Gateway:**
   ```bash
   kubectl get gateway tenant-management-gateway -n tenant-management -o yaml
   ```

4. **Check pod logs:**
   ```bash
   kubectl logs -n tenant-management -l app=backend --tail=50
   ```

### Certificate errors in browser?

- Verify domain matches certificate
- Check certificate is not expired
- Clear browser cache
- Try in incognito mode

### Mixed content warnings?

- Update all HTTP references to HTTPS
- Apply the HTTPS configmaps:
  ```bash
  kubectl apply -f k8s/eks-manifests/01-configmaps-https.yaml
  kubectl rollout restart deployment backend frontend -n tenant-management
  ```

## DNS Configuration

If DNS is not pointing to the load balancer:

```bash
# Get load balancer DNS
export LB_DNS=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo "Update your DNS:"
echo "Type: CNAME"
echo "Name: governance"
echo "Value: $LB_DNS"
```

## Security Headers

After HTTPS is working, consider adding security headers by updating the VirtualService.

See full documentation: [HTTPS_SETUP.md](HTTPS_SETUP.md)

## Next Steps

1. ✅ Enable HTTPS
2. ✅ Update ConfigMaps
3. ✅ Test endpoints
4. 🔲 Enable HTTPS redirect
5. 🔲 Add security headers
6. 🔲 Set up monitoring for certificate expiration
7. 🔲 Configure WAF (optional)
8. 🔲 Set up CloudFront CDN (optional)
