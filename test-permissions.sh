#!/bin/bash
# Test script to verify operator permissions are working correctly

set -e

# Configuration
ALB_URL="http://k8s-istiosys-istioing-a033e299eb-2401607831df82f9.elb.ap-south-1.amazonaws.com"
KEYCLOAK_URL="${ALB_URL}/realms/tenant-management/protocol/openid-connect/token"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}Testing Operator Permission Filtering${NC}"
echo -e "${BLUE}================================================================${NC}"

# Test 1: Login as operator.user and list tenants
echo -e "\n${YELLOW}Test 1: Operator User (should see limited or NO tenants)${NC}"
echo "Getting token for operator.user..."

OPERATOR_TOKEN=$(curl -s -X POST "$KEYCLOAK_URL" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=operator.user" \
  -d "password=Operator@123" \
  -d "grant_type=password" \
  -d "client_id=tenant-manager-frontend" | jq -r '.access_token')

if [ "$OPERATOR_TOKEN" == "null" ] || [ -z "$OPERATOR_TOKEN" ]; then
    echo -e "${RED}✗ Failed to get operator token${NC}"
    exit 1
fi

echo "Fetching tenants as operator.user..."
OPERATOR_TENANTS=$(curl -s -H "Authorization: Bearer $OPERATOR_TOKEN" \
  "${ALB_URL}/api/v1/tenants" | jq '.')

OPERATOR_COUNT=$(echo "$OPERATOR_TENANTS" | jq 'length')
echo -e "${GREEN}Operator sees $OPERATOR_COUNT tenant(s):${NC}"
echo "$OPERATOR_TENANTS" | jq -r '.[] | "  - " + .namespace'

# Test 2: Login as admin.user and list tenants
echo -e "\n${YELLOW}Test 2: Admin User (should see ALL tenants)${NC}"
echo "Getting token for admin.user..."

ADMIN_TOKEN=$(curl -s -X POST "$KEYCLOAK_URL" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin.user" \
  -d "password=Admin@123" \
  -d "grant_type=password" \
  -d "client_id=tenant-manager-frontend" | jq -r '.access_token')

if [ "$ADMIN_TOKEN" == "null" ] || [ -z "$ADMIN_TOKEN" ]; then
    echo -e "${RED}✗ Failed to get admin token${NC}"
    exit 1
fi

echo "Fetching tenants as admin.user..."
ADMIN_TENANTS=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
  "${ALB_URL}/api/v1/tenants" | jq '.')

ADMIN_COUNT=$(echo "$ADMIN_TENANTS" | jq 'length')
echo -e "${GREEN}Admin sees $ADMIN_COUNT tenant(s):${NC}"
echo "$ADMIN_TENANTS" | jq -r '.[] | "  - " + .namespace'

# Test 3: Check user permissions in database
echo -e "\n${YELLOW}Test 3: Checking User-Namespace Permissions in Database${NC}"
echo "Fetching all user permissions..."

USER_PERMS=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
  "${ALB_URL}/api/v1/admin/users/namespaces" | jq '.')

PERM_COUNT=$(echo "$USER_PERMS" | jq 'length')
echo -e "${GREEN}Found $PERM_COUNT active permission(s):${NC}"
echo "$USER_PERMS" | jq -r '.[] | "  - User: " + .user_id + " → Namespace: " + .namespace'

# Results
echo -e "\n${BLUE}================================================================${NC}"
echo -e "${BLUE}Results Summary${NC}"
echo -e "${BLUE}================================================================${NC}"

if [ "$OPERATOR_COUNT" -lt "$ADMIN_COUNT" ]; then
    echo -e "${GREEN}✓ SUCCESS: Operator sees fewer tenants than Admin${NC}"
    echo -e "  Admin: $ADMIN_COUNT tenants"
    echo -e "  Operator: $OPERATOR_COUNT tenants"
    echo -e "\n${GREEN}Permission filtering is WORKING CORRECTLY!${NC}"
elif [ "$OPERATOR_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}⚠ Operator sees NO tenants${NC}"
    echo -e "  This is expected if no permissions have been granted yet."
    echo -e "\n${YELLOW}To grant access:${NC}"
    echo -e "  1. Login to frontend as admin.user"
    echo -e "  2. Go to User Management page"
    echo -e "  3. Click 'Grant Access'"
    echo -e "  4. Select operator.user"
    echo -e "  5. Select a namespace to grant"
elif [ "$OPERATOR_COUNT" -eq "$ADMIN_COUNT" ]; then
    echo -e "${RED}✗ FAILURE: Operator sees ALL tenants (same as Admin)${NC}"
    echo -e "  Both see: $OPERATOR_COUNT tenants"
    echo -e "\n${RED}Permission filtering is NOT working!${NC}"
    echo -e "Check backend logs for issues."
else
    echo -e "${BLUE}ℹ Operator: $OPERATOR_COUNT, Admin: $ADMIN_COUNT${NC}"
fi

echo -e "\n${BLUE}================================================================${NC}"
