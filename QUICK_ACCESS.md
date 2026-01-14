# Quick Access Guide - Tenant Management System for CVS SaaS Apps

## Application URLs

### Main Application
- **URL**: http://k8s-istiosys-istioing-a033e299eb-2401607831df82f9.elb.ap-south-1.amazonaws.com/tm
- **Description**: Main frontend application with CVS branding

### Keycloak Login
- **URL**: http://k8s-istiosys-istioing-a033e299eb-2401607831df82f9.elb.ap-south-1.amazonaws.com/realms/tenant-management/protocol/openid-connect/auth
- **Theme**: CVS Light Theme
- **Features**:
  - Light background with gradient
  - CVS blue branding (#1976d2)
  - Modern card-based design
  - White login form with rounded corners

### Keycloak Admin Console
- **URL**: http://k8s-istiosys-istioing-a033e299eb-2401607831df82f9.elb.ap-south-1.amazonaws.com/admin
- **Username**: admin
- **Password**: admin123
- **Use For**: Managing users, roles, and realm settings

### API Documentation (Swagger)
- **URL**: http://k8s-istiosys-istioing-a033e299eb-2401607831df82f9.elb.ap-south-1.amazonaws.com/tm/api/v1/docs
- **Title**: Tenant Management System for CVS SaaS Apps
- **Access**: Requires admin login

## Test Users

### Admin User
- **Username**: `admin.user`
- **Password**: `Admin@123`
- **Role**: admin
- **Access**: Full system access

### Operator Users
- **Username**: `tenant.admin` or `operator.user`
- **Password**: `TenantAdmin@123` or `Operator@123`
- **Role**: operator
- **Access**: Manage assigned tenants only

### Viewer User
- **Username**: `viewer.user`
- **Password**: `Viewer@123`
- **Role**: viewer
- **Access**: Read-only access

## New Branding Features

### ✨ Application Title
- **Old**: AWS Tenant Management Portal
- **New**: Tenant Management System for CVS SaaS Apps

### ✨ Keycloak Login Theme
- **Background**: Light gradient (blue to light blue)
- **Card**: White with subtle shadow and rounded corners
- **Buttons**: CVS blue (#1976d2) with hover effects
- **Inputs**: Light gray background with blue focus state
- **Typography**: Improved hierarchy with CVS branding

### ✨ Color Scheme
- **Primary**: #1976d2 (CVS Blue)
- **Dark**: #424242 (Text)
- **Background**: #f5f7fa → #e8eef5 (Gradient)
- **Card**: #ffffff (White)
- **Input**: #f8f9fa (Light Gray)

## Quick Test Checklist

### 1. Frontend Branding
- [ ] Navigate to application URL
- [ ] Verify browser tab shows "Tenant Management System for CVS SaaS Apps"
- [ ] Check header shows full application name
- [ ] Login page shows split title (Tenant Management System / CVS SaaS Apps)

### 2. Keycloak Theme
- [ ] Click "Sign in with Keycloak" on login page
- [ ] Verify light background (no dark theme)
- [ ] Check login form is on white card
- [ ] Verify CVS blue button color
- [ ] Test input field focus (should show blue border)

### 3. Authentication
- [ ] Login as admin.user
- [ ] Verify dashboard loads
- [ ] Check user dropdown shows correct role
- [ ] Navigate to different pages (Tenants, Schedules, etc.)

### 4. User Management
- [ ] As admin, go to User Management
- [ ] Grant namespace access to tenant.admin
- [ ] Logout and login as tenant.admin
- [ ] Verify only assigned namespaces are visible

### 5. API Documentation
- [ ] Navigate to /tm/api/v1/docs (as admin)
- [ ] Verify title is "Tenant Management System for CVS SaaS Apps"
- [ ] Check description mentions CVS applications

## Screenshots

### Login Page (Before Keycloak)
- Clean design with centered card
- "Tenant Management System" in large text
- "CVS SaaS Apps" in blue below
- "Sign in with Keycloak" button

### Keycloak Login Page
- Light gradient background
- "Tenant Management System" in CVS blue
- "for CVS SaaS Apps" in gray below
- White login form card
- Username and Password fields with light background
- Blue "Sign In" button

### Application Dashboard
- Header: "Tenant Management System for CVS SaaS Apps"
- Navigation drawer with menu items
- User profile in top right
- Main content area with tenant cards

## Troubleshooting

### Login page not showing new branding
- **Solution**: Clear browser cache and hard refresh (Ctrl+Shift+R or Cmd+Shift+R)

### Keycloak still showing dark theme
- **Solution**: 
  1. Check Keycloak pod is running: `kubectl get pods -n tenant-management -l app=keycloak`
  2. Verify theme ConfigMap: `kubectl get cm keycloak-cvs-theme -n tenant-management`
  3. Check theme is set in realm: Login to admin console → Realm Settings → Themes → Login Theme should be "cvs-light"

### API docs not showing new title
- **Solution**: 
  1. Check backend pod is running: `kubectl get pods -n tenant-management -l app=backend`
  2. Verify pod started after code update
  3. Clear browser cache and refresh

### Theme CSS not loading
- **Solution**:
  1. Verify theme files are mounted: `kubectl exec -n tenant-management deployment/keycloak -- ls -la /opt/keycloak/themes/cvs-light/login/`
  2. Check Keycloak logs: `kubectl logs -n tenant-management deployment/keycloak`
  3. Restart Keycloak: `kubectl rollout restart deployment/keycloak -n tenant-management`

## Monitoring

### Check Pod Status
```bash
kubectl get pods -n tenant-management -l 'app in (keycloak,frontend,backend)'
```

### View Keycloak Logs
```bash
kubectl logs -n tenant-management deployment/keycloak --tail=50
```

### View Frontend Logs
```bash
kubectl logs -n tenant-management deployment/frontend --tail=50
```

### View Backend Logs
```bash
kubectl logs -n tenant-management deployment/backend --tail=50
```

## Access from Different Locations

### Browser
Simply navigate to: http://k8s-istiosys-istioing-a033e299eb-2401607831df82f9.elb.ap-south-1.amazonaws.com/tm

### cURL (API Testing)
```bash
# Get access token
TOKEN=$(curl -s -X POST \
  "http://k8s-istiosys-istioing-a033e299eb-2401607831df82f9.elb.ap-south-1.amazonaws.com/realms/tenant-management/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin.user" \
  -d "password=Admin@123" \
  -d "grant_type=password" \
  -d "client_id=tenant-manager-frontend" | jq -r '.access_token')

# Call API
curl -H "Authorization: Bearer $TOKEN" \
  "http://k8s-istiosys-istioing-a033e299eb-2401607831df82f9.elb.ap-south-1.amazonaws.com/tm/api/v1/tenants"
```

---

**Updated**: January 3, 2026
**Status**: ✅ All services running with new branding
