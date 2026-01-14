#!/bin/bash
# Script to apply the user permission fixes

set -e

echo "=================================================="
echo "Applying User Permission Fixes"
echo "=================================================="

# Check if we're in the right directory
if [ ! -f "backend/app/auth/keycloak.py" ]; then
    echo "Error: Please run this script from the ManageAWS root directory"
    exit 1
fi

echo ""
echo "1. Updating ConfigMap with DEBUG=false..."
kubectl apply -f k8s/eks-manifests/01-configmaps.yaml

echo ""
echo "2. Restarting backend pods to apply new configuration..."
kubectl rollout restart deployment/tenant-management-backend -n tenant-management

echo ""
echo "3. Waiting for backend to be ready..."
kubectl rollout status deployment/tenant-management-backend -n tenant-management

echo ""
echo "=================================================="
echo "Fixes Applied Successfully!"
echo "=================================================="
echo ""
echo "NEXT STEPS:"
echo "1. Test operator user login (should see NO tenants initially)"
echo "2. Login as admin.user (password: Admin@123)"
echo "3. Go to User Management page"
echo "4. Grant namespace access to operator users"
echo "5. Verify operator users can only see granted namespaces"
echo ""
echo "To verify the fix, run:"
echo "  cd backend"
echo "  python test_user_permissions.py"
echo ""
