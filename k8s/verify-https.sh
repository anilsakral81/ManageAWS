#!/bin/bash
# Quick HTTPS verification script

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

DOMAIN="governance.mrtmcloud.com"
NAMESPACE="tenant-management"

echo -e "${GREEN}=== HTTPS Configuration Check ===${NC}\n"

# 1. Check Istio Ingress Gateway Service
echo -e "${YELLOW}1. Checking Istio Ingress Gateway Service...${NC}"
SSL_CERT=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.metadata.annotations.service\.beta\.kubernetes\.io/aws-load-balancer-ssl-cert}' 2>/dev/null || echo "")

if [ -n "$SSL_CERT" ]; then
    echo -e "${GREEN}✓${NC} SSL Certificate configured: ${SSL_CERT}"
else
    echo -e "${RED}✗${NC} No SSL certificate configured on load balancer"
fi

SSL_PORTS=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.metadata.annotations.service\.beta\.kubernetes\.io/aws-load-balancer-ssl-ports}' 2>/dev/null || echo "")
if [ "$SSL_PORTS" = "443" ]; then
    echo -e "${GREEN}✓${NC} SSL port 443 configured"
else
    echo -e "${RED}✗${NC} SSL port not configured (current: $SSL_PORTS)"
fi

# 2. Check Gateway configuration
echo -e "\n${YELLOW}2. Checking Istio Gateway...${NC}"
HTTPS_PORT=$(kubectl get gateway tenant-management-gateway -n $NAMESPACE -o jsonpath='{.spec.servers[?(@.port.number==443)].port.number}' 2>/dev/null || echo "")

if [ "$HTTPS_PORT" = "443" ]; then
    echo -e "${GREEN}✓${NC} HTTPS port (443) configured in Gateway"
else
    echo -e "${RED}✗${NC} HTTPS port not configured in Gateway"
fi

HTTP_REDIRECT=$(kubectl get gateway tenant-management-gateway -n $NAMESPACE -o jsonpath='{.spec.servers[?(@.port.number==80)].tls.httpsRedirect}' 2>/dev/null || echo "")
if [ "$HTTP_REDIRECT" = "true" ]; then
    echo -e "${GREEN}✓${NC} HTTPS redirect enabled"
else
    echo -e "${YELLOW}⚠${NC} HTTPS redirect not enabled (HTTP will work alongside HTTPS)"
fi

# 3. Check Load Balancer
echo -e "\n${YELLOW}3. Checking Load Balancer...${NC}"
LB_DNS=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")

if [ -n "$LB_DNS" ]; then
    echo -e "${GREEN}✓${NC} Load Balancer DNS: ${LB_DNS}"
else
    echo -e "${RED}✗${NC} Load Balancer not provisioned"
fi

# 4. Check DNS
echo -e "\n${YELLOW}4. Checking DNS...${NC}"
RESOLVED_IP=$(dig +short $DOMAIN | head -n 1)

if [ -n "$RESOLVED_IP" ]; then
    echo -e "${GREEN}✓${NC} Domain resolves to: ${RESOLVED_IP}"
else
    echo -e "${RED}✗${NC} Domain does not resolve"
fi

# 5. Check backend and frontend pods
echo -e "\n${YELLOW}5. Checking Pods...${NC}"
BACKEND_READY=$(kubectl get pods -n $NAMESPACE -l app=backend -o jsonpath='{.items[0].status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "")
FRONTEND_READY=$(kubectl get pods -n $NAMESPACE -l app=frontend -o jsonpath='{.items[0].status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "")

if [ "$BACKEND_READY" = "True" ]; then
    echo -e "${GREEN}✓${NC} Backend pod is ready"
else
    echo -e "${RED}✗${NC} Backend pod is not ready"
fi

if [ "$FRONTEND_READY" = "True" ]; then
    echo -e "${GREEN}✓${NC} Frontend pod is ready"
else
    echo -e "${RED}✗${NC} Frontend pod is not ready"
fi

# 6. Test HTTP endpoint
echo -e "\n${YELLOW}6. Testing HTTP endpoint...${NC}"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://$DOMAIN/tm/health 2>/dev/null || echo "000")

if [ "$HTTP_STATUS" = "200" ]; then
    echo -e "${GREEN}✓${NC} HTTP endpoint working (Status: $HTTP_STATUS)"
elif [ "$HTTP_STATUS" = "301" ] || [ "$HTTP_STATUS" = "302" ]; then
    echo -e "${GREEN}✓${NC} HTTP redirects to HTTPS (Status: $HTTP_STATUS)"
else
    echo -e "${RED}✗${NC} HTTP endpoint failed (Status: $HTTP_STATUS)"
fi

# 7. Test HTTPS endpoint
echo -e "\n${YELLOW}7. Testing HTTPS endpoint...${NC}"
HTTPS_STATUS=$(curl -k -s -o /dev/null -w "%{http_code}" --connect-timeout 5 https://$DOMAIN/tm/health 2>/dev/null || echo "000")

if [ "$HTTPS_STATUS" = "200" ]; then
    echo -e "${GREEN}✓${NC} HTTPS endpoint working (Status: $HTTPS_STATUS)"
else
    echo -e "${RED}✗${NC} HTTPS endpoint failed (Status: $HTTPS_STATUS)"
fi

# 8. Check ConfigMaps
echo -e "\n${YELLOW}8. Checking ConfigMaps...${NC}"
KEYCLOAK_URL=$(kubectl get configmap frontend-config -n $NAMESPACE -o jsonpath='{.data.VITE_KEYCLOAK_URL}' 2>/dev/null || echo "")

if [[ "$KEYCLOAK_URL" == https://* ]]; then
    echo -e "${GREEN}✓${NC} Frontend ConfigMap uses HTTPS: $KEYCLOAK_URL"
elif [[ "$KEYCLOAK_URL" == http://* ]]; then
    echo -e "${YELLOW}⚠${NC} Frontend ConfigMap uses HTTP: $KEYCLOAK_URL (consider updating to HTTPS)"
else
    echo -e "${RED}✗${NC} Keycloak URL not configured"
fi

# Summary
echo -e "\n${GREEN}=== Summary ===${NC}"
echo "Domain: $DOMAIN"
echo "Load Balancer: $LB_DNS"
echo "HTTP Status: $HTTP_STATUS"
echo "HTTPS Status: $HTTPS_STATUS"

if [ "$HTTPS_STATUS" = "200" ]; then
    echo -e "\n${GREEN}🎉 HTTPS is fully configured and working!${NC}"
    echo -e "Access your app at: ${GREEN}https://$DOMAIN/tm/${NC}"
elif [ -n "$SSL_CERT" ]; then
    echo -e "\n${YELLOW}⚠ HTTPS is partially configured${NC}"
    echo "Possible issues:"
    echo "  - DNS not updated or propagated yet"
    echo "  - Certificate still validating"
    echo "  - Load balancer still updating"
    echo ""
    echo "Wait 5-10 minutes and run this script again"
else
    echo -e "\n${RED}✗ HTTPS is not configured${NC}"
    echo "Run: ./k8s/setup-https.sh"
fi

echo ""
