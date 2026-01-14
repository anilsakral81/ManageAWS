# Access Verification - Uptime Tracking Feature

## ✅ All Services Accessible via HTTPS

**Base URL:** `https://governance.mrtmcloud.com`

---

## 🌐 Frontend (with Uptime Metrics)

**URL:** https://governance.mrtmcloud.com/tm

**Status:** ✅ **LIVE** - HTTP/2 200 OK

**New Feature:** 
- Navigate to **Tenants** page
- Click on any tenant
- See **two tabs**: "Details & Pods" and **"Uptime Metrics"** (NEW!)
- Uptime Metrics tab shows:
  - Current state duration (e.g., "Running for 2h 15m")
  - Monthly uptime/downtime percentages with progress bars
  - Auto-refreshes every 30 seconds

---

## 🔧 Backend API

**Base URL:** https://governance.mrtmcloud.com/tm/api/v1

**Health Check:** https://governance.mrtmcloud.com/tm/health  
**Status:** ✅ **LIVE** - Returns `{"status": "healthy", "app": "Kubernetes Tenant Management Portal", "environment": "production"}`

### New Uptime Metrics Endpoints:

1. **Current State Duration**  
   `GET https://governance.mrtmcloud.com/tm/api/v1/tenants/{id}/metrics/current-state`

2. **Monthly Metrics**  
   `GET https://governance.mrtmcloud.com/tm/api/v1/tenants/{id}/metrics/monthly?year=2026&month=1`

3. **State History**  
   `GET https://governance.mrtmcloud.com/tm/api/v1/tenants/{id}/metrics/history?limit=50`

4. **Comprehensive Metrics**  
   `GET https://governance.mrtmcloud.com/tm/api/v1/tenants/{id}/metrics`

**API Docs:** https://governance.mrtmcloud.com/tm/docs

---

## 🔐 Keycloak

**Realm:** https://governance.mrtmcloud.com/realms/tenant-management

**OIDC Configuration:** https://governance.mrtmcloud.com/realms/tenant-management/.well-known/openid-configuration  
**Status:** ✅ **LIVE** - HTTP/2 200 OK

**Admin Console:** https://governance.mrtmcloud.com/admin/master/console/

---

## 🔒 Security

- ✅ **HTTPS Enabled** - All traffic over TLS
- ✅ **HTTP/2** - Modern protocol in use
- ✅ **HSTS** - Strict-Transport-Security header present
- ✅ **Security Headers** - X-Frame-Options, X-Content-Type-Options enabled

---

## 📊 Test Data

**Tenant #6 (pvg-commontools)** has sample uptime metrics:
- Multiple state transitions recorded
- Running/stopped/scaling states tracked
- Monthly aggregation available for January 2026

**To view:**
1. Go to https://governance.mrtmcloud.com/tm
2. Login with your credentials
3. Click on "pvg-commontools" tenant
4. Switch to **"Uptime Metrics"** tab

---

## 🎯 Quick Test

```bash
# Test Frontend
curl -I https://governance.mrtmcloud.com/tm

# Test Backend Health
curl https://governance.mrtmcloud.com/tm/health

# Test Keycloak
curl -I https://governance.mrtmcloud.com/realms/tenant-management/.well-known/openid-configuration

# Test Metrics API (requires auth)
curl -H "Authorization: Bearer <token>" \
  https://governance.mrtmcloud.com/tm/api/v1/tenants/6/metrics
```

---

## ✅ Deployment Summary

- **Frontend:** Deployed with new Uptime Metrics UI
- **Backend:** Deployed with metrics calculation services
- **Database:** tenant_state_history table created and populated
- **HTTPS:** Already configured and working
- **DNS:** governance.mrtmcloud.com resolving correctly
- **Path:** /tm base path configured in Istio VirtualService

**Everything is LIVE and accessible! 🎉**
