# Keycloak Test Users

## Simplified Role Structure

The system now uses 3 simplified roles:

### 1. **admin**
- Full access to all features and all tenants
- Can create user-to-tenant mappings
- Can perform all operations (create, read, update, delete, start, stop, schedule)
- Sees all tenants regardless of permissions

### 2. **operator**
- Can manage only assigned tenants
- Can start, stop, scale, and schedule assigned tenants
- Must be explicitly granted access to namespaces via User Management
- Does not see tenants they don't have access to

### 3. **viewer**
- Read-only access to all tenant information
- Cannot perform any write operations (start, stop, schedule, etc.)
- Can view all tenants but cannot modify them

## Test User Accounts

The following test users have been created in the `tenant-management` realm:

### 1. Admin User
- **Username**: `admin.user`
- **Password**: `Admin@123`
- **Email**: admin@example.com
- **Role**: `admin`
- **Permissions**: Full administrative access - sees all tenants, manages user mappings
- **Use Case**: System administration, user-to-tenant mapping management

### 2. Operator Users
- **Username**: `tenant.admin`
- **Password**: `TenantAdmin@123`
- **Email**: tenant-admin@example.com
- **Role**: `operator`
- **Permissions**: Can manage assigned tenants (start/stop/schedule)
- **Use Case**: Tenant operations on assigned namespaces

- **Username**: `operator.user`
- **Password**: `Operator@123`
- **Email**: operator@example.com
- **Role**: `operator`
- **Permissions**: Can manage assigned tenants (start/stop/schedule)
- **Use Case**: Day-to-day tenant operations

### 3. Viewer User
- **Username**: `viewer.user`
- **Password**: `Viewer@123`
- **Email**: viewer@example.com
- **Role**: `viewer`
- **Permissions**: Read-only access to view all tenant information
- **Use Case**: Monitoring and reporting

## How Tenant Access Works

### Admin Role
- **Sees**: All tenants in the cluster
- **Can Do**: Everything (manage users, start/stop tenants, create schedules)
- **No Assignment Needed**: Admin automatically has access to all namespaces

### Operator Role
- **Sees**: Only tenants explicitly assigned to them
- **Can Do**: Start, stop, scale, and schedule their assigned tenants
- **Assignment Required**: Must be granted access via User Management page

**To grant operator access to a namespace:**
1. Login as `admin.user`
2. Go to "User Management" page
3. Click "Grant Access"
4. Select operator user (e.g., "Tenant Admin")
5. Select namespace (e.g., "tenant-management")
6. Click "Grant Access"

### Viewer Role
- **Sees**: All tenants in the cluster
- **Can Do**: View only - no modifications allowed
- **No Assignment Needed**: Viewer can see everything but cannot modify

## Testing Login

### Using cURL
```bash
# Test login with tenant.admin
curl -X POST "http://k8s-istiosys-istioing-a033e299eb-2401607831df82f9.elb.ap-south-1.amazonaws.com/realms/tenant-management/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=tenant.admin" \
  -d "password=TenantAdmin@123" \
  -d "grant_type=password" \
  -d "client_id=tenant-manager-frontend"
```

### Using the Frontend
1. Navigate to the frontend application
2. Click "Login"
3. You'll be redirected to Keycloak
4. Enter username and password from above
5. You'll be redirected back with an access token

### Token Information
After successful login, you'll receive:
- **access_token**: JWT token for API authentication
- **refresh_token**: Token to refresh the access token
- **expires_in**: Token validity period (typically 300 seconds)
- **token_type**: "Bearer"

## Verifying User Roles

You can verify a user's roles by decoding the JWT token:

```bash
# Get token (example with tenant.admin)
TOKEN=$(curl -s -X POST "http://k8s-istiosys-istioing-a033e299eb-2401607831df82f9.elb.ap-south-1.amazonaws.com/realms/tenant-management/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=tenant.admin" \
  -d "password=TenantAdmin@123" \
  -d "grant_type=password" \
  -d "client_id=tenant-manager-frontend" | jq -r '.access_token')

# Decode token payload (Base64)
echo $TOKEN | cut -d'.' -f2 | base64 -d 2>/dev/null | jq .
```

The decoded token will show:
- `preferred_username`: The username
- `email`: User's email
- `realm_access.roles`: Array of assigned roles
- `resource_access`: Client-specific roles

## Using with Backend API

### Authentication Header
```bash
# Get token
TOKEN=$(curl -s -X POST "http://ALB-URL/realms/tenant-management/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=tenant.admin" \
  -d "password=TenantAdmin@123" \
  -d "grant_type=password" \
  -d "client_id=tenant-manager-frontend" | jq -r '.access_token')

# Make authenticated API request
curl -H "Authorization: Bearer $TOKEN" \
  http://ALB-URL/api/v1/tenants
```

## Managing Users via Admin Console

Access the Keycloak Admin Console:
- **URL**: http://k8s-istiosys-istioing-a033e299eb-2401607831df82f9.elb.ap-south-1.amazonaws.com/admin
- **Username**: admin
- **Password**: admin123

### To Create Additional Users:
1. Select "tenant-management" realm from dropdown
2. Navigate to "Users" in the left menu
3. Click "Add user"
4. Fill in user details
5. Save the user
6. Go to "Credentials" tab and set password
7. Go to "Role mappings" tab and assign roles

### To Modify User Roles:
1. Select user from Users list
2. Go to "Role mappings" tab
3. Select roles from "Available Roles"
4. Click "Assign" to add roles
5. Or click "Unassign" to remove roles

## Security Notes

⚠️ **IMPORTANT**: These are test credentials for development/testing only!

For production:
1. Use strong, unique passwords
2. Enable MFA (Multi-Factor Authentication)
3. Implement password policies
4. Regular password rotation
5. Monitor login attempts
6. Set up session timeout policies
7. Enable account lockout on failed attempts

## Troubleshooting

### Login Fails
- Verify Keycloak is running: `kubectl get pods -n tenant-management -l app=keycloak`
- Check user exists: Login to admin console and verify user
- Verify password: Reset password in admin console if needed
- Check client configuration: Ensure `tenant-manager-frontend` client exists and is enabled

### Token Invalid
- Check token expiration
- Verify issuer matches your Keycloak URL
- Ensure backend KEYCLOAK_URL matches your deployment
- Check backend can reach Keycloak service

### Role Not Working
- Verify role is assigned in admin console
- Check JWT token contains the role in `realm_access.roles`
- Ensure backend role mapping is correct
- Check backend logs for authorization errors

## Next Steps

1. **Test Authentication Flow**: Login via frontend
2. **Test API Access**: Make authenticated API calls with each user
3. **Verify Permissions**: Ensure each role has appropriate access
4. **Configure Namespace Mappings**: Use admin API to grant namespace access to users
5. **Test End-to-End**: Create tenant, assign user, verify access

## User Management API Examples

### Grant Namespace Access (Admin Only)
```bash
curl -X POST "http://ALB-URL/api/v1/admin/users/tenant.admin/namespaces" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"namespace": "production"}'
```

### List User's Namespaces
```bash
curl -X GET "http://ALB-URL/api/v1/admin/users/tenant.admin/namespaces" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Revoke Namespace Access
```bash
curl -X DELETE "http://ALB-URL/api/v1/admin/users/tenant.admin/namespaces/production" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```
