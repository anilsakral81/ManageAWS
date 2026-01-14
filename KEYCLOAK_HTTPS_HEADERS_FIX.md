# Keycloak HTTPS Fix - X-Forwarded Headers

## Problem

Even after configuring Keycloak with `KC_PROXY=edge`, the login form was still showing HTTP URLs and triggering browser security warnings:
- "The information you're about to submit is not secure"
- Keycloak OpenID configuration showed HTTP endpoints instead of HTTPS

## Root Cause

Keycloak was configured to work behind a proxy (`KC_PROXY=edge`), but the Istio VirtualService wasn't passing the necessary `X-Forwarded-Proto` header to tell Keycloak the original request came over HTTPS.

Without this header, Keycloak assumed the connection was HTTP and generated HTTP URLs for all endpoints, redirects, and form submissions.

## Solution

Updated the Keycloak VirtualService to inject `X-Forwarded-Proto: https` and `X-Forwarded-Port: 443` headers on all Keycloak routes.

### File: k8s/keycloak-vs-https.yaml

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: keycloak-vs
  namespace: tenant-management
spec:
  gateways:
  - tenant-management-gateway
  hosts:
  - '*'
  http:
  - match:
    - uri:
        prefix: /realms/
    headers:
      request:
        set:
          X-Forwarded-Proto: https
          X-Forwarded-Port: "443"
    route:
    - destination:
        host: keycloak
        port:
          number: 8080
    timeout: 60s
  # ... (same headers for /admin/, /js/, /resources/, /robots.txt)
```

## Applied Changes

```bash
kubectl apply -f k8s/keycloak-vs-https.yaml
```

## Verification

### Before Fix:
```bash
curl -sL https://governance.mrtmcloud.com/realms/tenant-management/.well-known/openid-configuration | jq '.issuer'
# Output: "http://governance.mrtmcloud.com/realms/tenant-management"
```

### After Fix:
```bash
curl -sL https://governance.mrtmcloud.com/realms/tenant-management/.well-known/openid-configuration | jq '.issuer'
# Output: "https://governance.mrtmcloud.com/realms/tenant-management"
```

All Keycloak endpoints now correctly show HTTPS:
- ✅ issuer: `https://governance.mrtmcloud.com/realms/tenant-management`
- ✅ authorization_endpoint: `https://governance.mrtmcloud.com/.../auth`
- ✅ token_endpoint: `https://governance.mrtmcloud.com/.../token`
- ✅ end_session_endpoint: `https://governance.mrtmcloud.com/.../logout`

## Testing

1. **Clear browser cache**: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)

2. **Visit the application**:
   ```
   https://governance.mrtmcloud.com/tm/
   ```

3. **Click Login** and verify:
   - ✅ No "not secure" warning
   - ✅ URL bar shows `https://` throughout the login flow
   - ✅ Form submission happens over HTTPS

4. **Check browser console**:
   - No mixed content errors
   - No security warnings

## How It Works

1. **Browser** sends request to `https://governance.mrtmcloud.com/realms/...`
2. **NLB** terminates HTTPS and forwards to Istio Gateway
3. **Istio Gateway** receives HTTP request (TLS already terminated)
4. **Istio VirtualService** adds headers:
   - `X-Forwarded-Proto: https`
   - `X-Forwarded-Port: 443`
5. **Keycloak** sees these headers and knows:
   - Original request was HTTPS
   - Should generate HTTPS URLs in responses
6. **Keycloak** returns login page with HTTPS form action
7. **Browser** submits form over HTTPS ✅

## Key Points

- **KC_PROXY=edge**: Tells Keycloak to trust X-Forwarded headers
- **X-Forwarded-Proto**: Tells Keycloak the protocol (https)
- **X-Forwarded-Port**: Tells Keycloak the port (443)
- **Both are needed**: Environment variables AND forwarded headers

## Related Files

- `k8s/keycloak-vs-https.yaml` - Updated VirtualService
- `k8s/current-keycloak-vs.yaml` - Previous configuration backup
- `KEYCLOAK_HTTPS_FIXED.md` - Initial proxy configuration fix

## Status

✅ **FULLY RESOLVED** - Login now works over HTTPS with no security warnings

Date: January 5, 2026
