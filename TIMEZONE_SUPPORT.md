# Timezone Support for Schedules - Solution Summary

## Problem
- Backend pods run in UTC timezone
- Users configure schedules in their local timezone
- Schedules were executing in UTC instead of user's intended time
- Example: User in IST (UTC+5:30) sets "6 PM" but it executed at 6 PM UTC (11:30 PM IST)

## Solution Implemented

### 1. **Database Schema**
Added `timezone` column to `schedules` table:
```sql
ALTER TABLE schedules ADD COLUMN timezone VARCHAR(50) NOT NULL DEFAULT 'UTC';
```

Stores IANA timezone names (e.g., `Asia/Kolkata`, `America/New_York`, `Europe/London`)

### 2. **Frontend Auto-Detection**
```typescript
// Automatically detect user's timezone
timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
```

- Detects timezone from browser: `Asia/Kolkata`, `America/New_York`, etc.
- Sends timezone with every schedule create/update
- Displays timezone in schedule table as badge
- Shows timezone info in schedule dialog

### 3. **Backend Scheduler**
Updated APScheduler to use each schedule's timezone:

```python
# Before (all schedules in UTC)
trigger = CronTrigger.from_crontab(
    schedule.cron_expression,
    timezone="UTC"  # Global UTC
)

# After (each schedule in its own timezone)
schedule_timezone = schedule.timezone or "UTC"
trigger = CronTrigger.from_crontab(
    schedule.cron_expression,
    timezone=schedule_timezone  # Per-schedule timezone
)
```

### 4. **How It Works**

**Example: User in India (IST = UTC+5:30) creates schedule**

1. User selects: "Stop tenant at 6:00 PM every weekday"
2. Frontend sends:
   ```json
   {
     "cron_expression": "0 18 * * 1-5",
     "timezone": "Asia/Kolkata"
   }
   ```
3. Backend stores both cron and timezone together
4. Scheduler creates job with `Asia/Kolkata` timezone
5. APScheduler handles conversion internally:
   - At 6:00 PM IST (12:30 PM UTC), it executes the schedule
   - Pod runs in UTC, but APScheduler converts the time

**Result**: Schedule executes at 6 PM local time, regardless of pod timezone!

### 5. **Additional Fixes**

#### Audit Log Improvements:
- Show "System" instead of "Unknown" for scheduler actions
- Show user names instead of user IDs (e.g., "John Doe" not "aa9645d9-b31a...")

```python
# Scheduler actions
if user_id == "scheduler":
    user_name = "System"

# Regular users - fetch from Keycloak
else:
    user_name = fetch_user_name_from_keycloak(user_id)
```

## Files Changed

### Backend
- `backend/app/models/schedule.py` - Added timezone column
- `backend/app/schemas/schedule.py` - Added timezone field to schemas
- `backend/app/services/scheduler.py` - Use per-schedule timezone
- `backend/app/services/tenant_service.py` - Fix audit log user display
- `backend/app/services/schedule_service.py` - Fix audit log user display
- `backend/alembic/versions/005_add_timezone_to_schedules.py` - Migration

### Frontend
- `frontend/src/types/index.ts` - Added timezone to Schedule interfaces
- `frontend/src/pages/Schedules.tsx` - Auto-detect and display timezone
- `frontend/src/pages/Dashboard.tsx` - Show user names in recent activities
- `frontend/src/pages/AuditLogs.tsx` - Show "System" for scheduler

## Deployment

1. **Database Migration**:
   ```bash
   ALTER TABLE schedules ADD COLUMN timezone VARCHAR(50) NOT NULL DEFAULT 'UTC';
   ```

2. **Backend**:
   ```bash
   docker buildx build --platform linux/amd64 \
     -t 122610483530.dkr.ecr.ap-south-1.amazonaws.com/tenant-management-backend:latest \
     --push backend/
   kubectl rollout restart deployment/backend -n tenant-management
   ```

3. **Frontend**:
   ```bash
   npm run build --prefix frontend
   kubectl cp frontend/dist/. tenant-management/${FRONTEND_POD}:/usr/share/nginx/html/
   ```

## User Experience

### Before
- User in IST sets schedule for "6 PM"
- Schedule runs at 6 PM UTC = 11:30 PM IST ❌
- Confusion about when schedules actually run

### After
- User in IST sets schedule for "6 PM"
- Frontend detects timezone: `Asia/Kolkata`
- Schedule runs at 6 PM IST ✅
- Timezone badge shows: "Asia/Kolkata" for clarity

## Testing

1. **Create Schedule**: Timezone auto-detected (e.g., `Asia/Kolkata`)
2. **View Schedules**: Timezone displayed in table
3. **Check Execution**: Scheduler logs show: `Added schedule 1 to scheduler (timezone: Asia/Kolkata)`
4. **Verify Time**: Schedule executes at user's local time

## Benefits

✅ **User-Friendly**: Schedules work as users expect (local time)  
✅ **Flexible**: Each schedule can have different timezone  
✅ **Reliable**: APScheduler handles timezone conversion automatically  
✅ **Transparent**: Timezone displayed clearly in UI  
✅ **No Breaking Changes**: Existing schedules default to UTC  

## Future Enhancements

1. **Timezone Picker**: Allow users to manually select timezone
2. **Next Run Display**: Show next execution time in user's timezone
3. **Timezone Warning**: Alert if user's timezone changes
4. **Schedule Preview**: Show execution times for next 5 runs

## References

- [APScheduler CronTrigger with Timezone](https://apscheduler.readthedocs.io/en/3.x/modules/triggers/cron.html#timezone-handling)
- [IANA Timezone Database](https://www.iana.org/time-zones)
- [JavaScript Intl.DateTimeFormat](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/DateTimeFormat/DateTimeFormat)
