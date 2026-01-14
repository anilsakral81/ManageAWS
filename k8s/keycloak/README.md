# Keycloak Deployment Guide for EKS

## Overview

This directory contains all necessary Kubernetes manifests to deploy Keycloak with pre-configured realm, clients, roles, and users for the Tenant Management system.

## Architecture

```
┌─────────────────────────────────────────────┐
│         Istio Ingress Gateway (ALB)         │
│   http://ALB-URL/  (Tenant Manager)        │
│   http://ALB-URL/  (Keycloak via hostname) │
└──────────────────┬──────────────────────────┘
                   │
         ┌─────────┴──────────┐
         │                    │
         ▼                    ▼
┌────────────────┐   ┌────────────────┐
│  Keycloak NS   │   │  Tenant-Mgmt   │
│                │   │   Namespace    │
│  ┌──────────┐  │   │                │
│  │Keycloak  │  │   │  ┌──────────┐  │
│  │  Pod     │◄─┼───┼──┤ Backend  │  │
│  └────┬─────┘  │   │  │   Pod    │  │
│       │        │   │  └──────────┘  │
│       ▼        │   │                │
│  ┌──────────┐  │   │  ┌──────────┐  │
│  │PostgreSQL│  │   │  │ Frontend │  │
│  │   Pod    │  │   │  │   Pod    │  │
│  └──────────┘  │   │  └──────────┘  │
└────────────────┘   └────────────────┘
```

## Prerequisites

- Kubernetes cluster (EKS) with Istio installed
- `kubectl` configured to access the cluster
- Istio Ingress Gateway deployed
- Persistent Volume support (for PostgreSQL)

## Files Structure

```
k8s/keycloak/
├── 00-namespace.yaml          # Keycloak namespace with Istio injection
├── 01-configmaps.yaml         # Keycloak config + Realm import JSON
├── 02-postgres.yaml           # PostgreSQL StatefulSet for Keycloak
├── 03-keycloak.yaml           # Keycloak Deployment and Service
├── 04-istio.yaml              # Gateway, VirtualService, DestinationRule
├── deploy-keycloak.sh         # Automated deployment script
└── README.md                  # This file
```

## Quick Start

### Automated Deployment

```bash
# From the project root
cd k8s/keycloak
./deploy-keycloak.sh
```

The script will:
1. Create the keycloak namespace
2. Deploy PostgreSQL database
3. Deploy Keycloak with realm auto-import
4. Configure Istio routing
5. Display access information

### Manual Deployment

```bash
# 1. Create namespace
kubectl apply -f 00-namespace.yaml

# 2. Create configurations
kubectl apply -f 01-configmaps.yaml

# 3. Deploy PostgreSQL
kubectl apply -f 02-postgres.yaml

# Wait for PostgreSQL to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n keycloak --timeout=300s

# 4. Deploy Keycloak
kubectl apply -f 03-keycloak.yaml

# Wait for Keycloak to be ready (2-3 minutes)
kubectl wait --for=condition=ready pod -l app=keycloak -n keycloak --timeout=300s

# 5. Configure Istio routing
kubectl apply -f 04-istio.yaml
```

## Pre-configured Components

### Realm: tenant-management

#### Roles:
- `admin` - Full administrative access
- `tenant-admin` - Tenant administrator with full access
- `tenant-operator` - Can manage tenant resources
- `tenant-viewer` - Read-only access to tenants

#### Clients:

**1. tenant-manager-backend** (Confidential)
- Client ID: `tenant-manager-backend`
- Client Secret: `backend-client-secret-change-in-production`
- Service Accounts Enabled: Yes
- Authorization Enabled: Yes
- Used by: Backend API for token validation

**2. tenant-manager-frontend** (Public)
- Client ID: `tenant-manager-frontend`
- PKCE Enabled: Yes
- Public Client: Yes
- Used by: Frontend application for user authentication

#### Pre-configured Users:

| Username | Password    | Role            | Email                          |
|----------|-------------|-----------------|--------------------------------|
| admin    | admin123    | admin           | admin@tenant-manager.local     |
| operator | operator123 | tenant-operator | operator@tenant-manager.local  |
| viewer   | viewer123   | tenant-viewer   | viewer@tenant-manager.local    |

> **⚠️ IMPORTANT**: Change all default passwords in production!

## Access Keycloak

### Get Ingress Gateway Address

```bash
kubectl get svc istio-ingressgateway -n istio-system

# For ALB (AWS)
export INGRESS_HOST=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# For LoadBalancer with IP
export INGRESS_HOST=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo $INGRESS_HOST
```

### Option 1: Using /etc/hosts (Development)

```bash
# Add to /etc/hosts
echo "$INGRESS_HOST keycloak.local" | sudo tee -a /etc/hosts

# Access Keycloak
open http://keycloak.local/admin
```

### Option 2: Using DNS (Production)

Configure DNS A record:
- Hostname: `keycloak.yourdomain.com`
- Value: `$INGRESS_HOST` (ALB hostname or IP)

Then access: `http://keycloak.yourdomain.com/admin`

### Option 3: Port Forward (Testing)

```bash
kubectl port-forward svc/keycloak 8080:8080 -n keycloak

# Access at http://localhost:8080/admin
```

## Integration with Tenant Manager

### 1. Update Frontend Configuration

Get the ALB URL:
```bash
INGRESS_HOST=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
```

Update frontend ConfigMap:
```bash
kubectl edit configmap frontend-config -n tenant-management
```

Change:
```yaml
VITE_KEYCLOAK_URL: "http://keycloak.local"  # or http://$INGRESS_HOST
VITE_KEYCLOAK_REALM: "tenant-management"
VITE_KEYCLOAK_CLIENT_ID: "tenant-manager-frontend"
```

### 2. Verify Backend Configuration

```bash
kubectl get configmap backend-config -n tenant-management -o yaml
```

Should show:
```yaml
KEYCLOAK_URL: "http://keycloak.keycloak.svc.cluster.local:8080"
KEYCLOAK_REALM: "tenant-management"
KEYCLOAK_CLIENT_ID: "tenant-manager-backend"
DEBUG: "false"
```

### 3. Verify Backend Secret

```bash
kubectl get secret backend-secret -n tenant-management -o jsonpath='{.data.KEYCLOAK_CLIENT_SECRET}' | base64 -d
```

Should output: `backend-client-secret-change-in-production`

### 4. Restart Deployments

```bash
# Restart backend to pick up new config
kubectl rollout restart deployment backend -n tenant-management

# Restart frontend to pick up new config
kubectl rollout restart deployment frontend -n tenant-management

# Check status
kubectl rollout status deployment backend -n tenant-management
kubectl rollout status deployment frontend -n tenant-management
```

## Usage

### Login to Tenant Manager

1. Access Tenant Manager: `http://$INGRESS_HOST/tm/`
2. You'll be redirected to Keycloak login
3. Login with any pre-configured user (e.g., admin/admin123)
4. After successful login, you'll be redirected back to the app

### Grant Namespace Access

As an admin user:

1. Navigate to **User Management** in the sidebar
2. Click **Grant Access**
3. Enter user's Keycloak ID (from token sub field)
4. Select namespace from dropdown
5. Click **Grant Access**

To get user's Keycloak ID:
```bash
# After login, decode the JWT token from browser localStorage
# The 'sub' field is the user ID

# Or via Keycloak Admin Console:
# Users → Select User → Details → ID field
```

### Create New Users

#### Via Keycloak Admin Console:

1. Go to http://keycloak.local/admin
2. Login with admin/admin123
3. Select `tenant-management` realm
4. Navigate to Users → Add user
5. Fill in details, save
6. Go to Credentials tab → Set password
7. Go to Role Mappings → Assign roles

#### Via REST API:

```bash
# Get admin token
ADMIN_TOKEN=$(curl -X POST "http://keycloak.local/realms/master/protocol/openid-connect/token" \
  -d "client_id=admin-cli" \
  -d "username=admin" \
  -d "password=admin123" \
  -d "grant_type=password" \
  | jq -r '.access_token')

# Create user
curl -X POST "http://keycloak.local/admin/realms/tenant-management/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "newuser@example.com",
    "firstName": "New",
    "lastName": "User",
    "enabled": true,
    "credentials": [{
      "type": "password",
      "value": "password123",
      "temporary": false
    }],
    "realmRoles": ["tenant-operator"]
  }'
```

## Customization

### Change Default Passwords

Edit `01-configmaps.yaml`:

```yaml
# In keycloak-secrets Secret
KEYCLOAK_ADMIN_PASSWORD: "your-secure-admin-password"
KC_DB_PASSWORD: "your-secure-db-password"

# In postgres-secrets Secret
POSTGRES_PASSWORD: "your-secure-db-password"

# In keycloak-realm-import ConfigMap
# Under users section, change credentials.value for each user
```

Then reapply:
```bash
kubectl delete secret keycloak-secrets -n keycloak
kubectl delete secret postgres-secrets -n keycloak
kubectl apply -f 01-configmaps.yaml
kubectl rollout restart deployment keycloak -n keycloak
kubectl rollout restart statefulset postgres -n keycloak
```

### Change Client Secrets

Edit `01-configmaps.yaml` in the realm JSON:
```json
{
  "clientId": "tenant-manager-backend",
  "secret": "your-new-secure-secret"
}
```

Also update backend secret:
```bash
kubectl edit secret backend-secret -n tenant-management
# Update KEYCLOAK_CLIENT_SECRET
```

Then restart backend:
```bash
kubectl rollout restart deployment backend -n tenant-management
```

### Add Custom Roles

Edit `01-configmaps.yaml` in the realm JSON:
```json
"roles": {
  "realm": [
    {
      "name": "custom-role",
      "description": "Custom role description",
      "composite": false
    }
  ]
}
```

Or add via Keycloak Admin Console:
- Realm Settings → Roles → Create Role

### Modify Token Lifespan

Edit `01-configmaps.yaml` in the realm JSON:
```json
{
  "realm": "tenant-management",
  "accessTokenLifespan": 3600,           // 1 hour
  "ssoSessionIdleTimeout": 86400,        // 24 hours
  "ssoSessionMaxLifespan": 864000,       // 10 days
  "offlineSessionIdleTimeout": 2592000   // 30 days
}
```

## Backup and Restore

### Backup Keycloak Data

```bash
# Backup PostgreSQL database
kubectl exec -n keycloak statefulset/postgres -- \
  pg_dump -U keycloak keycloak > keycloak-backup-$(date +%Y%m%d).sql

# Backup realm configuration
kubectl get configmap keycloak-realm-import -n keycloak -o yaml > keycloak-realm-backup.yaml
```

### Restore Keycloak Data

```bash
# Restore database
kubectl exec -i -n keycloak statefulset/postgres -- \
  psql -U keycloak keycloak < keycloak-backup-20260103.sql

# Restart Keycloak
kubectl rollout restart deployment keycloak -n keycloak
```

## Troubleshooting

### Keycloak Pod Not Starting

```bash
# Check logs
kubectl logs -n keycloak deployment/keycloak

# Common issues:
# 1. PostgreSQL not ready
kubectl get pods -n keycloak -l app=postgres

# 2. Database connection issues
kubectl exec -n keycloak deployment/keycloak -- env | grep KC_DB

# 3. Realm import errors
kubectl logs -n keycloak deployment/keycloak | grep -i "import"
```

### Cannot Access Keycloak via Browser

```bash
# Check Istio Gateway
kubectl get gateway -n keycloak

# Check VirtualService
kubectl get virtualservice -n keycloak

# Check Service
kubectl get svc -n keycloak keycloak

# Test internal access
kubectl run test-pod --rm -it --image=curlimages/curl -- \
  curl -v http://keycloak.keycloak.svc.cluster.local:8080/health
```

### Authentication Fails in Tenant Manager

```bash
# Check backend logs for auth errors
kubectl logs -n tenant-management deployment/backend | grep -i keycloak

# Verify backend can reach Keycloak
kubectl exec -n tenant-management deployment/backend -- \
  curl -v http://keycloak.keycloak.svc.cluster.local:8080/health

# Check if DEBUG mode is disabled
kubectl get configmap backend-config -n tenant-management -o yaml | grep DEBUG
```

### User Cannot Access Namespaces

```bash
# Check user's namespace permissions in database
kubectl exec -n tenant-management deployment/backend -- \
  python -c "
from app.database import SessionLocal
from app.models.user_namespace import UserNamespace
db = SessionLocal()
perms = db.query(UserNamespace).all()
for p in perms:
    print(f'{p.user_id} -> {p.namespace} (enabled={p.enabled})')
"

# Or via API (as admin)
curl http://ALB-URL/tm/api/v1/admin/users/namespaces \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## Production Hardening

### Security Checklist

- [ ] Change all default passwords
- [ ] Change client secrets
- [ ] Enable HTTPS/TLS on Istio Gateway
- [ ] Restrict Keycloak admin access
- [ ] Configure proper CORS origins
- [ ] Enable MFA for admin accounts
- [ ] Set up backup automation
- [ ] Configure resource limits
- [ ] Enable audit logging
- [ ] Restrict network access with NetworkPolicies
- [ ] Use strong database password
- [ ] Enable PostgreSQL SSL
- [ ] Configure session timeouts appropriately
- [ ] Regular security updates

### Enable HTTPS

Update `04-istio.yaml`:
```yaml
servers:
- port:
    number: 443
    name: https
    protocol: HTTPS
  tls:
    mode: SIMPLE
    credentialName: keycloak-tls-cert
  hosts:
  - "keycloak.yourdomain.com"
```

Create TLS certificate secret:
```bash
kubectl create secret tls keycloak-tls-cert \
  --cert=path/to/cert.pem \
  --key=path/to/key.pem \
  -n keycloak
```

## Monitoring

### Health Checks

```bash
# Keycloak health
curl http://keycloak.local/health

# Readiness
curl http://keycloak.local/health/ready

# Liveness
curl http://keycloak.local/health/live

# Metrics (if enabled)
curl http://keycloak.local/metrics
```

### Resource Usage

```bash
# Pod resource usage
kubectl top pods -n keycloak

# View resource limits
kubectl describe deployment keycloak -n keycloak | grep -A 5 "Limits:"
```

## Migration to New EKS Cluster

### Export Configuration

```bash
# 1. Backup manifests (already in git)
git clone your-repo
cd k8s/keycloak

# 2. Export secrets (encrypted)
kubectl get secret -n keycloak -o yaml > secrets-backup.yaml

# 3. Export database
kubectl exec -n keycloak statefulset/postgres -- \
  pg_dump -U keycloak keycloak > keycloak-db-$(date +%Y%m%d).sql
```

### Import to New Cluster

```bash
# 1. Deploy Keycloak
./deploy-keycloak.sh

# 2. Restore database (optional, if you have existing users)
kubectl cp keycloak-db-20260103.sql keycloak/postgres-0:/tmp/
kubectl exec -n keycloak statefulset/postgres -- \
  psql -U keycloak keycloak < /tmp/keycloak-db-20260103.sql

# 3. Update tenant-management ConfigMaps with new cluster details
kubectl edit configmap backend-config -n tenant-management
kubectl edit configmap frontend-config -n tenant-management

# 4. Restart deployments
kubectl rollout restart deployment backend -n tenant-management
kubectl rollout restart deployment frontend -n tenant-management
```

## Support

For issues or questions:
1. Check logs: `kubectl logs -n keycloak deployment/keycloak`
2. Review [Keycloak Documentation](https://www.keycloak.org/documentation)
3. Check [Troubleshooting](#troubleshooting) section above
