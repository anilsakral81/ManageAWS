#!/bin/bash
# Apply ACM certificate to Istio Ingress Gateway
# Usage: ./apply-certificate.sh <CERTIFICATE_ARN>

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <CERTIFICATE_ARN>"
    echo ""
    echo "Example:"
    echo "  $0 arn:aws:acm:ap-south-1:122610483530:certificate/xxxxx"
    exit 1
fi

CERT_ARN="$1"
NAMESPACE="istio-system"
SERVICE="istio-ingressgateway"

echo "Applying ACM certificate to $SERVICE..."
echo "Certificate ARN: $CERT_ARN"

# Update the service with SSL certificate annotations
kubectl patch svc $SERVICE -n $NAMESPACE -p "{
  \"metadata\": {
    \"annotations\": {
      \"service.beta.kubernetes.io/aws-load-balancer-ssl-cert\": \"$CERT_ARN\",
      \"service.beta.kubernetes.io/aws-load-balancer-ssl-ports\": \"443\",
      \"service.beta.kubernetes.io/aws-load-balancer-backend-protocol\": \"tcp\"
    }
  }
}"

echo "Certificate applied successfully!"
echo ""
echo "Waiting for load balancer to update (this may take 2-5 minutes)..."
sleep 10

for i in {1..30}; do
    echo -n "."
    sleep 10
done
echo ""

# Get load balancer DNS
LB_DNS=$(kubectl get svc $SERVICE -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo ""
echo "Load Balancer DNS: $LB_DNS"
echo ""
echo "Testing HTTPS endpoint..."
sleep 5

HTTPS_STATUS=$(curl -k -s -o /dev/null -w "%{http_code}" https://governance.mrtmcloud.com/tm/health || echo "000")
echo "HTTPS Status: $HTTPS_STATUS"

if [ "$HTTPS_STATUS" = "200" ]; then
    echo ""
    echo "✅ HTTPS is working!"
    echo "Access your application at: https://governance.mrtmcloud.com/tm/"
else
    echo ""
    echo "⚠️  HTTPS returned status: $HTTPS_STATUS"
    echo "This might be normal if DNS hasn't propagated yet."
    echo "Wait 5-10 minutes and try again."
fi
