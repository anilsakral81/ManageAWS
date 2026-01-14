#!/bin/bash
# Switch from NLB to ALB for better certificate support
# ALB supports multiple certificates with SNI

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Switch Istio Ingress from NLB to ALB ===${NC}\n"

echo "This will:"
echo "1. Update Istio ingress gateway service to use ALB"
echo "2. Configure ALB annotations for HTTPS"
echo "3. Support multiple certificates with SNI"
echo ""
read -p "Continue? (y/n): " confirm

if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "Cancelled"
    exit 0
fi

# Get certificate ARNs
echo -e "\n${YELLOW}Available ACM Certificates:${NC}"
aws acm list-certificates --region ap-south-1 --output table

echo ""
read -p "Enter primary certificate ARN for governance.mrtmcloud.com: " CERT_ARN

if [ -z "$CERT_ARN" ]; then
    echo "Certificate ARN required"
    exit 1
fi

# Create ALB ingress service configuration
cat << EOF > /tmp/istio-alb-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: istio-ingressgateway
  namespace: istio-system
  annotations:
    # ALB annotations
    service.beta.kubernetes.io/aws-load-balancer-type: "external"
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: "ip"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"
    service.beta.kubernetes.io/aws-load-balancer-attributes: "load_balancing.cross_zone.enabled=true"
    
    # SSL Certificate
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: "$CERT_ARN"
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: "443"
    
    # Backend protocol - Istio listens on 8080/8443
    service.beta.kubernetes.io/aws-load-balancer-backend-protocol: "http"
    
    # Health check
    service.beta.kubernetes.io/aws-load-balancer-healthcheck-path: "/healthz/ready"
    service.beta.kubernetes.io/aws-load-balancer-healthcheck-port: "15021"
spec:
  type: LoadBalancer
  selector:
    istio: ingressgateway
  ports:
  - name: http
    port: 80
    protocol: TCP
    targetPort: 8080
  - name: https
    port: 443
    protocol: TCP
    targetPort: 8080  # ALB terminates TLS, forwards HTTP to Istio
EOF

echo -e "\n${YELLOW}Applying ALB configuration...${NC}"
kubectl apply -f /tmp/istio-alb-service.yaml

echo -e "${GREEN}✓${NC} Service updated to use ALB"

echo -e "\n${YELLOW}Waiting for ALB to provision (this may take 3-5 minutes)...${NC}"
sleep 30

for i in {1..30}; do
    echo -n "."
    sleep 10
done
echo ""

# Get new load balancer DNS
NEW_LB_DNS=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo -e "\n${GREEN}New ALB DNS: $NEW_LB_DNS${NC}"
echo ""
echo "Update your DNS to point to: $NEW_LB_DNS"
echo ""
echo "Testing endpoints..."
sleep 10

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://governance.mrtmcloud.com/tm/health || echo "000")
echo "HTTP Status: $HTTP_STATUS"

HTTPS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://governance.mrtmcloud.com/tm/health || echo "000")
echo "HTTPS Status: $HTTPS_STATUS"

echo ""
if [ "$HTTPS_STATUS" = "200" ]; then
    echo -e "${GREEN}✅ ALB is working with HTTPS!${NC}"
else
    echo -e "${YELLOW}⚠️  DNS may need time to propagate${NC}"
    echo "Wait 5-10 minutes and test again"
fi

echo ""
echo "To add more certificates (for different domains):"
echo "1. Go to EC2 > Load Balancers in AWS Console"
echo "2. Find your ALB"
echo "3. Go to Listeners tab"
echo "4. Edit HTTPS:443 listener"
echo "5. Add certificates with SNI"
