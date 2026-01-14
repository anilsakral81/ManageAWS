# ACM Certificate Setup Guide for governance.mrtmcloud.com

## Current Status

✅ **ConfigMaps updated to use HTTPS**
✅ **Deployments restarted with HTTPS configuration**
✅ **Istio Gateway configured for HTTPS (port 443)**
⚠️ **ACM Certificate needed for production-grade SSL**

## Problem: Mixed Protocol Error

The mixed protocol error occurs when:
- Frontend tries to load resources over HTTP
- But the page is served over HTTPS
- Browser blocks mixed content for security

**Solution**: Use HTTPS throughout (now configured!)

## What's Been Done

1. ✅ Updated ConfigMaps to use HTTPS URLs:
   - Frontend: `VITE_KEYCLOAK_URL: https://governance.mrtmcloud.com`
   - Backend: CORS origins include HTTPS

2. ✅ Restarted backend and frontend deployments

3. ✅ Updated Istio Gateway to handle both HTTP (port 80) and HTTPS (port 443)

4. ✅ Created certificate request script

## Next Steps: Add ACM Certificate

### Option 1: Request Certificate via AWS Console (Recommended)

1. **Go to AWS Certificate Manager Console**:
   - Region: ap-south-1 (Mumbai)
   - Click "Request certificate"

2. **Request public certificate**:
   - Domain names:
     - `governance.mrtmcloud.com`
     - `*.mrtmcloud.com` (optional, for wildcard)
     - `mrtmcloud.com` (optional, for root domain)
   - Validation method: DNS validation

3. **Add DNS records**:
   - ACM will show CNAME records
   - Add these to your DNS provider (Route53, GoDaddy, etc.)
   - Wait 5-30 minutes for validation

4. **Get the Certificate ARN**:
   - Once status shows "Issued"
   - Copy the ARN (looks like: `arn:aws:acm:ap-south-1:...`)

5. **Apply the certificate**:
   ```bash
   cd /Users/comviva/Documents/Code/ManageAWS
   ./k8s/apply-certificate.sh <YOUR_CERT_ARN>
   ```

### Option 2: Request via CLI (If You Have Permissions)

```bash
cd /Users/comviva/Documents/Code/ManageAWS

# Run with an AWS account that has ACM permissions
./k8s/request-certificate.sh
```

This will:
- Request the certificate
- Show DNS validation records
- Provide the certificate ARN

Then apply it:
```bash
./k8s/apply-certificate.sh <CERT_ARN>
```

### Option 3: Use Existing Certificate (Temporary)

If you can't request a new certificate right now, you can use one of the existing certificates temporarily:

```bash
# Use the demo certificate (will show certificate warning)
./k8s/apply-certificate.sh arn:aws:acm:ap-south-1:122610483530:certificate/511ea75e-7ccd-4388-885a-9a1583f69521
```

**Note**: This will cause browser warnings since the domain doesn't match.

## DNS Validation Records

When you request the certificate, ACM will provide DNS records like:

```
Name: _xxxxxxxxxxxxx.governance.mrtmcloud.com
Type: CNAME
Value: _yyyyyyyyyyyy.acm-validations.aws.
```

Add this record to your DNS provider.

### If using Route53:

```bash
# Get your hosted zone ID first
aws route53 list-hosted-zones --output table

# Then ACM console will let you auto-create the record
# Or use the button "Create records in Route53"
```

## Verify the Setup

After applying the certificate, run:

```bash
./k8s/verify-https.sh
```

You should see:
- ✅ SSL Certificate configured
- ✅ SSL port 443 configured
- ✅ HTTPS endpoint working

## Testing

### Test HTTPS endpoint:
```bash
curl -I https://governance.mrtmcloud.com/tm/health
```

### Test in browser:
```bash
open https://governance.mrtmcloud.com/tm/
```

Check for:
- 🔒 Green padlock in address bar
- No mixed content warnings
- Valid certificate

## Troubleshooting

### Certificate not validating?

Check validation status:
```bash
aws acm describe-certificate \
  --certificate-arn <YOUR_CERT_ARN> \
  --region ap-south-1 \
  --query 'Certificate.{Status:Status,DomainValidation:DomainValidationOptions}'
```

### DNS records not showing up?

Wait longer (can take up to 48 hours, usually 5-30 minutes) or check:
```bash
dig _xxxxxxxxxxxxx.governance.mrtmcloud.com CNAME
```

### Mixed content errors still showing?

1. Hard refresh browser (Cmd+Shift+R)
2. Clear browser cache
3. Check browser console for specific URLs causing issues
4. Verify ConfigMaps:
   ```bash
   kubectl get configmap frontend-config -n tenant-management -o yaml | grep KEYCLOAK_URL
   ```

### Certificate error in browser?

- Verify domain matches certificate
- Check certificate is "Issued" in ACM
- Try different browser/incognito mode

## Current Configuration

### Frontend ConfigMap (HTTPS):
```yaml
VITE_KEYCLOAK_URL: "https://governance.mrtmcloud.com"
VITE_KEYCLOAK_REALM: "tenant-management"
VITE_KEYCLOAK_CLIENT_ID: "tenant-manager-frontend"
VITE_API_BASE_URL: "/tm"
VITE_BASE_PATH: "/tm"
```

### Backend ConfigMap:
```yaml
CORS_ORIGINS: "http://localhost:3000,http://localhost:8080,http://governance.mrtmcloud.com,https://governance.mrtmcloud.com,https://*"
```

### Istio Gateway:
- Port 80 (HTTP) - accessible
- Port 443 (HTTPS) - accessible

## Summary

1. **Now**: ConfigMaps use HTTPS, deployments restarted
2. **Next**: Request ACM certificate via AWS Console
3. **Then**: Apply certificate using `./k8s/apply-certificate.sh`
4. **Finally**: Verify with `./k8s/verify-https.sh`

## Quick Commands

```bash
# Verify current status
./k8s/verify-https.sh

# Apply certificate (once you have the ARN)
./k8s/apply-certificate.sh arn:aws:acm:ap-south-1:122610483530:certificate/xxxxx

# Check pods
kubectl get pods -n tenant-management

# View ConfigMaps
kubectl get configmap -n tenant-management frontend-config -o yaml
kubectl get configmap -n tenant-management backend-config -o yaml

# Check logs if issues
kubectl logs -n tenant-management -l app=frontend --tail=50
kubectl logs -n tenant-management -l app=backend --tail=50
```

---

**Status**: ConfigMaps updated, waiting for ACM certificate
**Next Step**: Request certificate via AWS Console or CLI
