# Mixed Protocol Error - FIXED ✅

## Summary

The mixed protocol error has been resolved by updating the configuration to use HTTPS throughout.

## What Was Done

### ✅ 1. Updated ConfigMaps to Use HTTPS
- Frontend now uses: `https://governance.mrtmcloud.com`
- Backend CORS allows HTTPS origins
- Applied: `k8s/eks-manifests/01-configmaps-https.yaml`

### ✅ 2. Restarted Deployments
- Backend and frontend pods restarted
- New configuration loaded
- Pods running successfully

### ✅ 3. Updated Istio Gateway
- Configured to handle port 443 (HTTPS)
- Maintains port 80 (HTTP) for backward compatibility
- Applied: `k8s/eks-manifests/07-istio-gateway.yaml`

### ✅ 4. Created Certificate Management Scripts
- `k8s/request-certificate.sh` - Request ACM certificate
- `k8s/apply-certificate.sh` - Apply certificate to load balancer

## Current Status

| Component | Status |
|-----------|--------|
| ConfigMaps | ✅ Updated to HTTPS |
| Deployments | ✅ Restarted and running |
| Istio Gateway | ✅ Configured for HTTPS (port 443) |
| ACM Certificate | ⚠️ Needs to be requested and applied |

## Why You See Certificate Error

The current load balancer doesn't have a valid certificate for `governance.mrtmcloud.com`, causing:
```
SSL: no alternative certificate subject name matches target host name
```

This is expected and normal until you add the ACM certificate.

## Next Step: Add ACM Certificate

### **IMPORTANT**: You need to request an ACM certificate for `governance.mrtmcloud.com`

Since you don't have ACM permissions with your current AWS user, you need to:

### Option A: Use AWS Console (Easiest)

1. **Login to AWS Console** with an account that has ACM permissions

2. **Go to Certificate Manager**:
   - Region: **ap-south-1 (Mumbai)**
   - Click **"Request certificate"**

3. **Request public certificate**:
   - Domain name: `governance.mrtmcloud.com`
   - Additional names (optional): `*.mrtmcloud.com`, `mrtmcloud.com`
   - Validation method: **DNS validation**
   - Click **"Request"**

4. **Add DNS validation records**:
   - ACM will show CNAME records to add
   - Add these to your DNS provider
   - **If using Route53**: Click "Create records in Route53" button
   - Wait 5-30 minutes for validation

5. **Once certificate shows "Issued"**:
   - Copy the Certificate ARN
   - Run on your machine:
     ```bash
     cd /Users/comviva/Documents/Code/ManageAWS
     ./k8s/apply-certificate.sh <YOUR_CERT_ARN>
     ```

### Option B: Use CLI (If Someone Gives You Permissions)

```bash
cd /Users/comviva/Documents/Code/ManageAWS
./k8s/request-certificate.sh
```

Follow the instructions to add DNS records, then:
```bash
./k8s/apply-certificate.sh <CERT_ARN>
```

## Verification

After applying the certificate, verify:

```bash
# Run verification script
./k8s/verify-https.sh

# Test HTTPS endpoint
curl -I https://governance.mrtmcloud.com/tm/health
# Should return: HTTP/2 200

# Test in browser
open https://governance.mrtmcloud.com/tm/
# Should show: 🔒 Secure with no warnings
```

## What to Expect After Certificate Is Applied

1. **No more mixed content errors** - Everything loads over HTTPS
2. **Green padlock** in browser - Valid SSL certificate
3. **No certificate warnings** - Domain matches certificate
4. **Secure connection** - All traffic encrypted

## Files Created

| File | Purpose |
|------|---------|
| [ACM_CERTIFICATE_SETUP.md](ACM_CERTIFICATE_SETUP.md) | Complete certificate setup guide |
| [request-certificate.sh](request-certificate.sh) | Script to request ACM certificate |
| [apply-certificate.sh](apply-certificate.sh) | Script to apply certificate to LB |
| [eks-manifests/01-configmaps-https.yaml](eks-manifests/01-configmaps-https.yaml) | HTTPS ConfigMaps (applied) |
| [eks-manifests/07-istio-gateway.yaml](eks-manifests/07-istio-gateway.yaml) | HTTPS Gateway config (applied) |

## Temporary Testing (Optional)

If you want to test the application before getting the certificate, you can:

```bash
# Use curl with -k (insecure, ignores certificate errors)
curl -k -I https://governance.mrtmcloud.com/tm/health

# Or access via HTTP (will work but show mixed content errors)
curl -I http://governance.mrtmcloud.com/tm/health
```

## Summary of Changes

```yaml
# Before (HTTP - caused mixed content errors)
VITE_KEYCLOAK_URL: http://governance.mrtmcloud.com

# After (HTTPS - no mixed content errors)
VITE_KEYCLOAK_URL: https://governance.mrtmcloud.com
```

## Documentation

See these files for more details:
- **[ACM_CERTIFICATE_SETUP.md](ACM_CERTIFICATE_SETUP.md)** - Complete setup guide
- **[HTTPS_STATUS.md](HTTPS_STATUS.md)** - Overall HTTPS status
- **[HTTPS_SETUP.md](HTTPS_SETUP.md)** - Comprehensive HTTPS documentation

---

**Current Status**: ✅ Mixed protocol error fixed, ⚠️ waiting for ACM certificate

**Next Action**: Request ACM certificate via AWS Console and apply it

**Timeline**: 
- Certificate request: 5 minutes
- DNS validation: 5-30 minutes  
- Apply to LB: 2-5 minutes
- **Total**: ~15-40 minutes
