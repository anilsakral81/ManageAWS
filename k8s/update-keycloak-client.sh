#!/bin/bash

# Script to update Keycloak client configuration for new domain
# This updates the tenant-manager-frontend client to allow the new domain

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

NAMESPACE="tenant-management"
REALM="tenant-management"
CLIENT_ID="tenant-manager-frontend"
NEW_DOMAIN="governance.mrtmcloud.com"

echo -e "${GREEN}Updating Keycloak Client Configuration${NC}"
echo "Domain: $NEW_DOMAIN"
echo "Realm: $REALM"
echo "Client: $CLIENT_ID"
echo ""

# Get Keycloak pod name
KEYCLOAK_POD=$(kubectl get pods -n $NAMESPACE -l app=keycloak -o jsonpath='{.items[0].metadata.name}')

if [ -z "$KEYCLOAK_POD" ]; then
    echo -e "${RED}Error: Keycloak pod not found${NC}"
    exit 1
fi

echo -e "${YELLOW}Found Keycloak pod: $KEYCLOAK_POD${NC}"

# Get admin credentials
ADMIN_USER="admin"
ADMIN_PASS="admin123"

echo -e "${GREEN}Step 1: Logging in to Keycloak...${NC}"

# Login and get access token
TOKEN=$(kubectl exec -n $NAMESPACE $KEYCLOAK_POD -- /opt/keycloak/bin/kcadm.sh config credentials \
    --server http://localhost:8080 \
    --realm master \
    --user $ADMIN_USER \
    --password $ADMIN_PASS 2>&1 | grep -v "Logging" || true)

echo -e "${GREEN}Step 2: Getting client configuration...${NC}"

# Get the client's internal ID
CLIENT_UUID=$(kubectl exec -n $NAMESPACE $KEYCLOAK_POD -- /opt/keycloak/bin/kcadm.sh get clients \
    -r $REALM \
    --fields id,clientId \
    2>/dev/null | grep -B 1 "\"clientId\" : \"$CLIENT_ID\"" | grep "\"id\"" | sed 's/.*"id" : "\([^"]*\)".*/\1/')

if [ -z "$CLIENT_UUID" ]; then
    echo -e "${RED}Error: Client $CLIENT_ID not found in realm $REALM${NC}"
    exit 1
fi

echo -e "${YELLOW}Client UUID: $CLIENT_UUID${NC}"

echo -e "${GREEN}Step 3: Updating client configuration...${NC}"

# Update the client with new redirect URIs and web origins
kubectl exec -n $NAMESPACE $KEYCLOAK_POD -- /opt/keycloak/bin/kcadm.sh update clients/$CLIENT_UUID \
    -r $REALM \
    -s "redirectUris=[\"http://${NEW_DOMAIN}/*\",\"https://${NEW_DOMAIN}/*\",\"http://localhost:3000/*\",\"http://localhost:8080/*\"]" \
    -s "webOrigins=[\"http://${NEW_DOMAIN}\",\"https://${NEW_DOMAIN}\",\"http://localhost:3000\",\"http://localhost:8080\",\"*\"]" \
    -s "attributes.\"post.logout.redirect.uris\"=\"http://${NEW_DOMAIN}/* https://${NEW_DOMAIN}/* http://localhost:3000/* http://localhost:8080/*\"" \
    2>/dev/null

echo -e "${GREEN}✓ Client configuration updated successfully!${NC}"
echo ""
echo -e "${GREEN}Updated settings:${NC}"
echo "  - Valid Redirect URIs: http://${NEW_DOMAIN}/*, https://${NEW_DOMAIN}/*"
echo "  - Web Origins: http://${NEW_DOMAIN}, https://${NEW_DOMAIN}"
echo "  - Post Logout Redirect URIs: http://${NEW_DOMAIN}/*, https://${NEW_DOMAIN}/*"
echo ""
echo -e "${GREEN}You can now access the application at:${NC}"
echo "  http://${NEW_DOMAIN}/tm/"
echo ""
