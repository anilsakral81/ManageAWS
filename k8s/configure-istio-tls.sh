#!/bin/bash
# Configure TLS certificate in Istio Gateway (for NLB setup)
# This lets Istio handle SSL instead of the load balancer

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Configure TLS in Istio Gateway ===${NC}\n"

# Check if certificate files exist
if [ ! -f "tls.crt" ] || [ ! -f "tls.key" ]; then
    echo -e "${YELLOW}You need the certificate and private key files:${NC}"
    echo "1. Download your certificate from ACM or your certificate provider"
    echo "2. Save as: tls.crt (certificate + intermediate certs)"
    echo "3. Save as: tls.key (private key)"
    echo ""
    echo "For ACM certificates, you'll need to export them first"
    echo "(ACM doesn't allow export of AWS-issued certs, you'd need to use a different method)"
    echo ""
    exit 1
fi

# Create TLS secret
echo "Creating Kubernetes TLS secret..."
kubectl create secret tls governance-tls \
  --cert=tls.crt \
  --key=tls.key \
  -n tenant-management \
  --dry-run=client -o yaml | kubectl apply -f -

echo -e "${GREEN}✓${NC} TLS secret created"

# Update Gateway to use the secret
cat << 'EOF' > /tmp/gateway-tls.yaml
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: tenant-management-gateway
  namespace: tenant-management
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "governance.mrtmcloud.com"
    - "*"
    tls:
      httpsRedirect: true
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: governance-tls
    hosts:
    - "governance.mrtmcloud.com"
    - "*"
EOF

kubectl apply -f /tmp/gateway-tls.yaml

echo -e "${GREEN}✓${NC} Gateway updated to use TLS certificate"
echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo "HTTPS is now handled by Istio Gateway"
echo ""
echo "Test: curl -I https://governance.mrtmcloud.com/tm/health"
