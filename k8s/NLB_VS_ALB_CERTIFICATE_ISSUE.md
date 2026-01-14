# NLB vs ALB Certificate Issue - Solution Guide

## Problem

You added multiple certificates to the HTTPS listener, but the browser shows the default certificate instead of the correct one for `governance.mrtmcloud.com`.

## Root Cause

Your Istio ingress gateway is using a **Network Load Balancer (NLB)**, not an Application Load Balancer (ALB).

### Key Differences:

| Feature | NLB | ALB |
|---------|-----|-----|
| **Multiple Certificates** | ❌ No SNI support | ✅ Full SNI support |
| **Certificate per Listener** | Only 1 default | Multiple with SNI |
| **Layer** | Layer 4 (TCP) | Layer 7 (HTTP/HTTPS) |
| **Use Case** | High performance, TCP | HTTP/HTTPS with features |

**NLB limitation**: You can only have ONE certificate per listener. Any additional certificates you added in the console won't work because NLB doesn't support SNI (Server Name Indication) the same way ALB does.

## Solutions

### ⭐ Option 1: Switch to ALB (RECOMMENDED)

ALB supports multiple certificates with SNI, so it will automatically serve the correct certificate based on the domain name.

#### Steps:

```bash
cd /Users/comviva/Documents/Code/ManageAWS

# Run the switch script
./k8s/switch-to-alb.sh
```

The script will:
1. Convert the Istio ingress service to use ALB
2. Configure your certificate on the ALB
3. Set up proper health checks
4. Update DNS automatically

#### After switching to ALB:

To add more certificates for different domains:
1. Go to **AWS Console → EC2 → Load Balancers**
2. Find your ALB (starts with `k8s-istiosys-istioing-`)
3. Click **Listeners** tab
4. Edit **HTTPS:443** listener
5. Click **Add certificates**
6. Select your certificates
7. **SNI will automatically route** to the correct cert based on domain

### Option 2: Configure Certificate ARN on NLB (Single Domain Only)

If you only need ONE domain (governance.mrtmcloud.com), you can configure the certificate directly on the NLB:

```bash
# Get your certificate ARN
aws acm list-certificates --region ap-south-1

# Apply it using the existing script
./k8s/apply-certificate.sh arn:aws:acm:ap-south-1:122610483530:certificate/YOUR_CERT_ARN
```

**Limitation**: This only works for ONE certificate. If you need multiple domains with different certificates, use Option 1 (ALB).

### Option 3: TLS Termination in Istio (Advanced)

Let Istio Gateway handle TLS instead of the load balancer. This requires exporting your certificate from ACM (not possible for AWS-issued certs) or using your own certificate.

```bash
# If you have certificate files (tls.crt and tls.key)
./k8s/configure-istio-tls.sh
```

## Why You See the Default Certificate

When you added certificates to the AWS Console:

1. **If you used NLB**: The certificates were added but NLB can't use them properly. It will always serve the first/default certificate regardless of the domain name requested.

2. **If you manually added to ALB**: The Istio ingress is still using NLB, so those certificates aren't being used at all.

## Recommended Approach

**Use ALB** (Option 1) because:
- ✅ Supports multiple certificates with SNI
- ✅ Automatically serves the right certificate for each domain
- ✅ Better for HTTP/HTTPS workloads
- ✅ More features (path-based routing, host-based routing, etc.)

The only downside is slightly higher latency (~1-2ms) compared to NLB, but you get much better HTTP/HTTPS features.

## Quick Commands

### Check current load balancer type:
```bash
kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.metadata.annotations}' | grep load-balancer-type
```

### Switch to ALB:
```bash
./k8s/switch-to-alb.sh
```

### Add certificate to NLB (single cert only):
```bash
./k8s/apply-certificate.sh <CERT_ARN>
```

### Check which certificate is being served:
```bash
openssl s_client -connect governance.mrtmcloud.com:443 -servername governance.mrtmcloud.com < /dev/null 2>&1 | grep subject
```

## After Switching to ALB

1. Update DNS if the load balancer DNS changed
2. Test: `curl -I https://governance.mrtmcloud.com/tm/health`
3. Verify certificate in browser - should see correct cert for your domain
4. Add additional certificates via AWS Console if needed

## Files Created

- **[switch-to-alb.sh](switch-to-alb.sh)** - Automated script to switch from NLB to ALB
- **[configure-istio-tls.sh](configure-istio-tls.sh)** - Alternative: Configure TLS in Istio
- **[apply-certificate.sh](apply-certificate.sh)** - Apply certificate to NLB (single cert only)

---

**Recommendation**: Use `./k8s/switch-to-alb.sh` to switch to ALB for proper multi-certificate support with SNI.
