#!/usr/bin/env python3
"""
Test script to verify user permissions for operator role
This script tests that operator users can only see tenants they have been granted access to.
"""

import asyncio
import sys
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Add backend to path
sys.path.insert(0, '/Users/comviva/Documents/Code/ManageAWS/backend')

from app.database import get_db_session
from app.models.user_namespace import UserNamespace
from app.schemas.user import UserInfo
from app.auth.keycloak import get_user_allowed_namespaces


async def test_permissions():
    """Test user permissions"""
    
    # Create database session
    async for db in get_db_session():
        print("=" * 70)
        print("TESTING USER PERMISSIONS")
        print("=" * 70)
        
        # Test 1: Admin user should see all namespaces
        print("\n1. Testing Admin User...")
        admin_user = UserInfo(
            sub="admin-123",
            email="admin@example.com",
            preferred_username="admin.user",
            name="Admin User",
            roles=["admin"],
            groups=[],
            allowed_namespaces=[]
        )
        admin_namespaces = await get_user_allowed_namespaces(admin_user, db)
        print(f"   Admin can access: {admin_namespaces}")
        assert admin_namespaces == ["*"], "Admin should have wildcard access"
        print("   ✓ PASS: Admin has access to all namespaces")
        
        # Test 2: Viewer user should see all namespaces (read-only)
        print("\n2. Testing Viewer User...")
        viewer_user = UserInfo(
            sub="viewer-123",
            email="viewer@example.com",
            preferred_username="viewer.user",
            name="Viewer User",
            roles=["viewer"],
            groups=[],
            allowed_namespaces=[]
        )
        viewer_namespaces = await get_user_allowed_namespaces(viewer_user, db)
        print(f"   Viewer can access: {viewer_namespaces}")
        assert viewer_namespaces == ["*"], "Viewer should have wildcard access (read-only)"
        print("   ✓ PASS: Viewer has access to all namespaces (read-only)")
        
        # Test 3: Operator user with no grants should see nothing
        print("\n3. Testing Operator User (no grants)...")
        operator_user_no_grants = UserInfo(
            sub="operator-no-grants-123",
            email="operator-nogrants@example.com",
            preferred_username="operator.nogrants",
            name="Operator No Grants",
            roles=["operator"],
            groups=[],
            allowed_namespaces=[]
        )
        operator_no_grants_namespaces = await get_user_allowed_namespaces(operator_user_no_grants, db)
        print(f"   Operator (no grants) can access: {operator_no_grants_namespaces}")
        assert operator_no_grants_namespaces == [], "Operator with no grants should see nothing"
        print("   ✓ PASS: Operator with no grants sees no namespaces")
        
        # Test 4: Check existing operator user permissions
        print("\n4. Testing Existing Operator Users in Database...")
        result = await db.execute(
            select(UserNamespace).where(UserNamespace.enabled == True)
        )
        user_namespaces = result.scalars().all()
        
        if user_namespaces:
            print(f"   Found {len(user_namespaces)} active namespace permissions:")
            for un in user_namespaces:
                print(f"   - User: {un.user_id} -> Namespace: {un.namespace}")
                
                # Test this specific user
                test_operator = UserInfo(
                    sub=un.user_id,
                    email=f"{un.user_id}@example.com",
                    preferred_username=un.user_id,
                    name=f"Test Operator {un.user_id}",
                    roles=["operator"],
                    groups=[],
                    allowed_namespaces=[]
                )
                test_namespaces = await get_user_allowed_namespaces(test_operator, db)
                print(f"     -> This operator can access: {test_namespaces}")
        else:
            print("   No active namespace permissions found in database")
            print("   ⚠ WARNING: You need to grant namespaces to operator users!")
        
        # Test 5: Check for operators with tenant.admin or operator.user
        print("\n5. Checking specific test users from Keycloak...")
        test_user_ids = [
            "tenant.admin",
            "operator.user"
        ]
        
        for user_id in test_user_ids:
            result = await db.execute(
                select(UserNamespace)
                .where(UserNamespace.user_id == user_id)
                .where(UserNamespace.enabled == True)
            )
            perms = result.scalars().all()
            
            if perms:
                namespaces = [p.namespace for p in perms]
                print(f"   User '{user_id}' has access to: {namespaces}")
            else:
                print(f"   User '{user_id}' has NO namespace permissions")
                print(f"   ⚠ This user will see ZERO tenants unless granted access!")
        
        print("\n" + "=" * 70)
        print("RECOMMENDATIONS:")
        print("=" * 70)
        print("1. Operator users MUST be granted namespace access via User Management")
        print("2. Login as admin.user to the frontend")
        print("3. Go to User Management page")
        print("4. Click 'Grant Access' for each operator user")
        print("5. Select the operator user (e.g., 'operator.user')")
        print("6. Select the namespace they should access")
        print("7. Verify the operator can now see only their assigned tenants")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_permissions())
