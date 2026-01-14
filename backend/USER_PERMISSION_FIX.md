# User Permission Fix Summary

## Problem
Operator role users were able to see ALL tenants even though they should only see tenants that have been explicitly granted to them through user-to-namespace mappings.

## Root Cause
The authentication bypass in `backend/app/auth/keycloak.py` was too permissive:
```python
if settings.keycloak_url == "https://keycloak.example.com" or settings.debug:
    # This gave admin access to ALL users in debug mode
```

## Fixes Applied

### 1. Removed Debug Mode Bypass (backend/app/auth/keycloak.py)
**Before:**
```python
if settings.keycloak_url == "https://keycloak.example.com" or settings.debug:
    return UserInfo(roles=["admin", "tenant-admin"], allowed_namespaces=["*"])
```

**After:**
```python
if settings.keycloak_url == "https://keycloak.example.com":
    # Only bypass when Keycloak is not configured (local dev only)
    return UserInfo(roles=["admin"], allowed_namespaces=["*"])
```

This ensures that when `debug=True` in production, users are not automatically given admin access.

### 2. Enhanced Role-Based Namespace Access (backend/app/auth/keycloak.py)
Added proper handling for the viewer role:

```python
async def get_user_allowed_namespaces(user: UserInfo, db) -> List[str]:
    # Admin role: access all namespaces with full permissions
    if "admin" in user.roles:
        return ["*"]
    
    # Viewer role: can see all namespaces but read-only
    if "viewer" in user.roles:
        return ["*"]
    
    # Operator role: only see explicitly granted namespaces
    result = await db.execute(
        select(UserNamespace.namespace)
        .where(UserNamespace.user_id == user.sub)
        .where(UserNamespace.enabled == True)
    )
    namespaces = [row[0] for row in result.all()]
    return namespaces if namespaces else []
```

## How It Works Now

### Admin Role (`admin`)
- **Access**: ALL namespaces (wildcard `*`)
- **Permissions**: Full control (create, read, update, delete, start, stop, schedule)
- **Mapping Required**: NO - automatic access to everything

### Viewer Role (`viewer`)
- **Access**: ALL namespaces (wildcard `*`)
- **Permissions**: Read-only (can view but cannot modify)
- **Mapping Required**: NO - automatic read access to everything

### Operator Role (`operator`)
- **Access**: ONLY explicitly granted namespaces
- **Permissions**: Can start, stop, scale, and schedule assigned tenants
- **Mapping Required**: YES - must be granted via User Management page

## Granting Access to Operators

1. Login as `admin.user` (username: `admin.user`, password: `Admin@123`)
2. Navigate to "User Management" page in the frontend
3. Click "Grant Access" button
4. Select the operator user (e.g., "operator.user" or "tenant.admin")
5. Select the namespace to grant access to
6. Click "Grant Access" to confirm

The operator will now see only the namespaces they've been granted access to.

## Verifying the Fix

### Option 1: Run the Test Script
```bash
cd /Users/comviva/Documents/Code/ManageAWS/backend
python test_user_permissions.py
```

This will show:
- Which users have namespace permissions
- What namespaces each operator can access
- Whether permissions are correctly applied

### Option 2: Manual Testing
1. Login as `operator.user` (password: `Operator@123`)
2. Check the tenant list - should be EMPTY if no permissions granted
3. Login as `admin.user`
4. Grant `operator.user` access to a specific namespace (e.g., "tenant-management")
5. Logout and login as `operator.user` again
6. Now should see ONLY the "tenant-management" namespace

### Option 3: API Testing
```bash
# Get operator token
TOKEN=$(curl -s -X POST "http://YOUR_ALB_URL/realms/tenant-management/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=operator.user" \
  -d "password=Operator@123" \
  -d "grant_type=password" \
  -d "client_id=tenant-manager-frontend" | jq -r '.access_token')

# List tenants as operator (should be limited)
curl -H "Authorization: Bearer $TOKEN" \
  http://YOUR_ALB_URL/api/v1/tenants | jq .
```

## Database Schema
The permissions are stored in the `user_namespaces` table:

| Column | Description |
|--------|-------------|
| user_id | Keycloak user UUID (from JWT `sub` claim) |
| namespace | Kubernetes namespace name |
| enabled | Boolean - whether permission is active |
| granted_by | Admin user who granted access |
| granted_at | Timestamp when access was granted |

## Important Notes

1. **User ID**: The system uses Keycloak's user UUID (`sub` claim from JWT), not the username
2. **Case Sensitivity**: Roles are case-sensitive: `"operator"` not `"Operator"`
3. **Empty List**: Operators with no granted namespaces will see an empty tenant list
4. **Real-time**: Changes to permissions require the user to refresh or re-fetch tenants
5. **Backend Restart**: If you modified environment variables (like `debug` or `keycloak_url`), restart the backend service

## Troubleshooting

### Operator still sees all tenants
1. Check if `debug=True` in backend environment variables
2. Verify Keycloak URL is properly configured (not the default)
3. Restart backend service after config changes
4. Check backend logs for "Auth bypass enabled" warnings

### Operator sees no tenants even after granting access
1. Verify the correct user UUID is being used (check database)
2. Ensure `enabled=True` in `user_namespaces` table
3. Check that the namespace actually exists in Kubernetes
4. Verify operator role is correctly assigned in Keycloak

### How to check user UUID
```bash
# Decode JWT token to see user sub (UUID)
TOKEN="<paste token here>"
echo $TOKEN | cut -d'.' -f2 | base64 -d 2>/dev/null | jq .sub
```

## Next Steps

1. Restart backend service to apply changes
2. Test with an operator user
3. Grant necessary namespace access via User Management
4. Verify operators can only see their assigned tenants
