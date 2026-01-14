# HTTPS Setup Guide for Tenant Management System

## Overview
This guide explains how to enable HTTPS for your Kubernetes deployment using AWS ACM certificates and Network Load Balancer (NLB).

## Prerequisites
- AWS ACM certificate for your domain
- kubectl access to EKS cluster
- Domain DNS configured to point to the load balancer

## Available ACM Certificates

Based on the scan, here are the available certificates:

1. **`*.comviva.demo.mrtm-comviva.com`** (ISSUED)
   - ARN: `arn:aws:acm:ap-south-1:122610483530:certificate/65112963-1df7-4356-9c34-4aa0a303adc3`
   - Valid until: 2026-06-08

2. **`*.release.comviva.mrtmcloud.com`** (ISSUED)
   - ARN: `arn:aws:acm:ap-south-1:122610483530:certificate/a23a0c58-50d9-45a7-aa03-443adabea971`
   - SANs: `*.release.comviva.mrtmcloud.com`, `*.demo.comviva.mrtmcloud.com`
   - Valid until: 2026-06-12

3. **`*.demo.pm.mrtmcloud.com`** (ISSUED, IN USE)
   - ARN: `arn:aws:acm:ap-south-1:122610483530:certificate/511ea75e-7ccd-4388-885a-9a1583f69521`
   - SANs: `*.demo.pm.mrtmcloud.com`, `*.comviva.rm.mrtmcloud.com`, `*.demo.pvg.mrtmcloud.com`, etc.
   - Valid until: 2026-06-20

## Option 1: Request a New Certificate for `governance.mrtmcloud.com`

If you need a certificate specifically for `governance.mrtmcloud.com` or `*.mrtmcloud.com`:

```bash
# Request certificate (requires ACM permissions)
aws acm request-certificate \
  --domain-name "*.mrtmcloud.com" \
  --subject-alternative-names "mrtmcloud.com" "governance.mrtmcloud.com" \
  --validation-method DNS \
  --region ap-south-1

# Validate the certificate by adding DNS records shown in ACM console
```

## Option 2: Use Existing Certificate

If `governance.mrtmcloud.com` matches one of the existing certificates, use that certificate ARN.

## Setup Steps

### Step 1: Update Istio Ingress Gateway Service

Update the Istio ingress gateway service to use ACM certificate:

```bash
# Edit the service
kubectl edit svc istio-ingressgateway -n istio-system
```

Add or update these annotations (replace with your certificate ARN):

```yaml
metadata:
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: "arn:aws:acm:ap-south-1:122610483530:certificate/YOUR_CERT_ARN"
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: "443"
    service.beta.kubernetes.io/aws-load-balancer-backend-protocol: "tcp"
```

Or apply the prepared configuration:

```bash
# First, update the certificate ARN in the file
export CERT_ARN="arn:aws:acm:ap-south-1:122610483530:certificate/YOUR_CERT_ARN"

# Create a temporary file with the ARN replaced
sed "s|YOUR_CERT_ARN|$CERT_ARN|g" k8s/enable-https.yaml > /tmp/https-service.yaml

# Apply the configuration
kubectl apply -f /tmp/https-service.yaml
```

### Step 2: Apply Updated Istio Gateway

The Gateway configuration has been updated to handle both HTTP and HTTPS:

```bash
kubectl apply -f k8s/eks-manifests/07-istio-gateway.yaml
```

### Step 3: Wait for Load Balancer Update

The NLB will be updated with the SSL certificate. This may take 2-5 minutes:

```bash
# Watch the service
kubectl get svc istio-ingressgateway -n istio-system -w

# Check load balancer status
aws elbv2 describe-load-balancers --region ap-south-1 | grep -A 10 istio
```

### Step 4: Get the Load Balancer DNS

```bash
export LB_DNS=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "Load Balancer DNS: $LB_DNS"
```

### Step 5: Update DNS Records

Update your DNS to point to the load balancer:

```bash
# For governance.mrtmcloud.com, create a CNAME record:
# Type: CNAME
# Name: governance
# Value: <LOAD_BALANCER_DNS>
# TTL: 300
```

Or use Route53:

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id YOUR_HOSTED_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "governance.mrtmcloud.com",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "'"$LB_DNS"'"}]
      }
    }]
  }'
```

### Step 6: Enable HTTPS Redirect (Optional)

To force all HTTP traffic to redirect to HTTPS, update the Gateway:

```yaml
servers:
- port:
    number: 80
    name: http
    protocol: HTTP
  hosts:
  - "*"
  tls:
    httpsRedirect: true
```

Apply:

```bash
kubectl apply -f k8s/eks-manifests/07-istio-gateway.yaml
```

## Verification

### Test HTTP Access

```bash
curl -I http://governance.mrtmcloud.com/tm/health
```

### Test HTTPS Access

```bash
curl -I https://governance.mrtmcloud.com/tm/health
```

### Check Certificate

```bash
openssl s_client -connect governance.mrtmcloud.com:443 -servername governance.mrtmcloud.com
```

### Verify in Browser

Open https://governance.mrtmcloud.com/tm/ in your browser and verify:
- Green padlock icon
- Valid certificate
- No SSL warnings

## Troubleshooting

### Certificate Not Showing

1. Verify the certificate ARN is correct
2. Ensure the domain matches the certificate
3. Check load balancer listeners:
   ```bash
   aws elbv2 describe-listeners --load-balancer-arn YOUR_LB_ARN --region ap-south-1
   ```

### 503 Errors

1. Check backend pods are running:
   ```bash
   kubectl get pods -n tenant-management
   ```

2. Check Istio gateway configuration:
   ```bash
   kubectl get gateway -n tenant-management tenant-management-gateway -o yaml
   ```

### DNS Not Resolving

1. Check DNS propagation:
   ```bash
   nslookup governance.mrtmcloud.com
   dig governance.mrtmcloud.com
   ```

2. Wait for TTL to expire (usually 5 minutes)

### Mixed Content Warnings

Update frontend configuration to use HTTPS URLs:

```bash
# Update configmap with HTTPS URLs
kubectl edit configmap frontend-config -n tenant-management
```

## Security Best Practices

1. **Enable HTTPS Redirect**: Force all HTTP traffic to HTTPS
2. **Use Strong TLS Version**: TLS 1.2 or higher
3. **Regular Certificate Renewal**: Set up auto-renewal or monitoring
4. **HSTS Headers**: Add Strict-Transport-Security headers
5. **Security Headers**: Add X-Frame-Options, X-Content-Type-Options, etc.

## Adding Security Headers

Update the VirtualService to add security headers:

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: tenant-management-vs
  namespace: tenant-management
spec:
  # ... existing config ...
  http:
  - match:
    - uri:
        prefix: /tm/
    headers:
      response:
        set:
          Strict-Transport-Security: "max-age=31536000; includeSubDomains"
          X-Frame-Options: "SAMEORIGIN"
          X-Content-Type-Options: "nosniff"
          X-XSS-Protection: "1; mode=block"
    route:
    - destination:
        host: frontend-service
```

## Cost Considerations

- ACM certificates are free
- NLB charges apply based on:
  - Number of load balancer hours
  - Number of LCUs (Load Balancer Capacity Units) used
- Estimate: ~$20-30/month for typical usage

## Next Steps

1. Set up CloudWatch monitoring for SSL/TLS metrics
2. Configure certificate expiration alerts
3. Implement automated certificate renewal
4. Set up WAF (Web Application Firewall) for additional security
5. Enable CloudFront for CDN and DDoS protection
