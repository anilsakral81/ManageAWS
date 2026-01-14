#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

NAMESPACE="tenant-management"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Keycloak Deployment (tenant-management)${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}ERROR: kubectl not found. Please install kubectl first.${NC}"
    exit 1
fi

# Check if connected to cluster
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}ERROR: Not connected to a Kubernetes cluster.${NC}"
    exit 1
fi

echo -e "${YELLOW}Current Kubernetes context:${NC}"
kubectl config current-context
echo ""

# Check if namespace exists
if ! kubectl get namespace $NAMESPACE &> /dev/null; then
    echo -e "${RED}ERROR: Namespace $NAMESPACE does not exist.${NC}"
    echo -e "${YELLOW}Please create it first or deploy the full application.${NC}"
    exit 1
fi

read -p "Deploy Keycloak in $NAMESPACE namespace? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 1
fi

echo ""
echo -e "${GREEN}Step 1: Creating ConfigMaps and Secrets...${NC}"
kubectl apply -f k8s/keycloak/01-configmaps.yaml

echo -e "${GREEN}Step 2: Deploying PostgreSQL for Keycloak...${NC}"
kubectl apply -f k8s/keycloak/02-postgres.yaml

echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
kubectl wait --for=condition=ready pod -l app=keycloak-postgres -n $NAMESPACE --timeout=300s || true

echo -e "${GREEN}Step 3: Deploying Keycloak...${NC}"
kubectl apply -f k8s/keycloak/03-keycloak.yaml

echo -e "${YELLOW}Waiting for Keycloak to be ready...${NC}"
kubectl wait --for=condition=ready pod -l app=keycloak -n $NAMESPACE --timeout=600s || true

echo -e "${GREEN}Step 4: Configuring Istio routing...${NC}"
kubectl apply -f k8s/keycloak/04-istio.yaml

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Get ALB URL
echo -e "${YELLOW}Fetching ALB URL...${NC}"
ALB_URL=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "not-found")

if [ "$ALB_URL" != "not-found" ]; then
    echo -e "${GREEN}Keycloak Admin Console:${NC} http://$ALB_URL/auth"
    echo -e "${GREEN}Admin Username:${NC} admin"
    echo -e "${GREEN}Admin Password:${NC} Run: kubectl get secret keycloak-admin -n $NAMESPACE -o jsonpath='{.data.password}' | base64 -d"
    echo ""
    echo -e "${YELLOW}To access Keycloak:${NC}"
    echo "1. Open: http://$ALB_URL/auth"
    echo "2. Login with admin credentials"
    echo "3. Create realm: tenant-management"
    echo "4. Configure clients as per documentation"
else
    echo -e "${YELLOW}Could not retrieve ALB URL. Check Istio ingress gateway status:${NC}"
    echo "kubectl get svc -n istio-system istio-ingressgateway"
fi

echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo "1. Access Keycloak admin console"
echo "2. Create realm: tenant-management"
echo "3. Configure clients (see k8s/keycloak/README.md)"
echo "4. Update frontend ConfigMap with ALB URL"
echo "5. Restart deployments: kubectl rollout restart deployment backend frontend -n $NAMESPACE"
echo ""

echo -e "${YELLOW}Useful Commands:${NC}"
echo "View Keycloak logs:   kubectl logs -f deployment/keycloak -n $NAMESPACE"
echo "View Postgres logs:   kubectl logs -f statefulset/keycloak-postgres -n $NAMESPACE"
echo "Port-forward:         kubectl port-forward svc/keycloak 8080:8080 -n $NAMESPACE"
echo "Get admin password:   kubectl get secret keycloak-admin -n $NAMESPACE -o jsonpath='{.data.password}' | base64 -d"
echo ""
