# Tenant Uptime/Downtime Tracking

## Overview

This system tracks how long tenants have been running (scaled >= 1) and shutdown (scaled to 0), including monthly aggregated metrics. The system also considers "scaling" state (when pods are not all ready yet) as part of uptime.

## How It Works

### 1. State Tracking Model

**TenantStateHistory** records every state transition:
- `previous_state`: The state before the change (running, stopped, scaling, unknown)
- `new_state`: The state after the change
- `previous_replicas`: Number of replicas before the change
- `new_replicas`: Number of replicas after the change
- `changed_at`: Timestamp of the state change
- `changed_by`: User who triggered the change
- `reason`: Description of why the state changed

### 2. State Types

- **RUNNING**: Tenant is scaled to >= 1 replicas and all pods are ready
- **SCALING**: Tenant is scaled to >= 1 replicas but not all pods are ready yet (considered uptime)
- **STOPPED**: Tenant is scaled to 0 replicas
- **UNKNOWN**: Initial or undefined state

### 3. When States Are Recorded

State changes are automatically recorded when:
- Tenant is started (scale to 1)
- Tenant is stopped (scale to 0)
- Tenant is scaled to any replica count
- First time a tenant is scaled (creates initial state record)

### 4. Metrics Calculation

#### Current State Duration
Calculates how long the tenant has been in its current state by finding the most recent state change and computing the time difference.

#### Monthly Uptime/Downtime
For a given month, the system:
1. Retrieves all state changes in and before the month
2. Determines the initial state at month start
3. Calculates duration spent in each state
4. Aggregates:
   - **Uptime**: Time spent in RUNNING or SCALING states
   - **Downtime**: Time spent in STOPPED state
   - **Scaling time**: Subset of uptime when state was SCALING

### 5. API Endpoints

#### Get Current State Duration
```
GET /api/tenants/{namespace}/metrics/current-state
```
Returns how long the tenant has been in its current state.

**Response:**
```json
{
  "current_state": "running",
  "duration_seconds": 86400,
  "duration_formatted": "1d",
  "state_since": "2026-01-13T10:00:00",
  "changed_by": "user@example.com"
}
```

#### Get Monthly Metrics
```
GET /api/tenants/{namespace}/metrics/monthly?year=2026&month=1
```
Returns uptime/downtime statistics for a specific month (defaults to current month).

**Response:**
```json
{
  "year": 2026,
  "month": 1,
  "uptime_seconds": 2592000,
  "downtime_seconds": 86400,
  "scaling_seconds": 3600,
  "uptime_percentage": 96.77,
  "downtime_percentage": 3.23,
  "uptime_formatted": "30d",
  "downtime_formatted": "1d",
  "scaling_formatted": "1h",
  "total_seconds": 2678400,
  "month_start": "2026-01-01T00:00:00",
  "month_end": "2026-01-31T23:59:59"
}
```

#### Get State History
```
GET /api/tenants/{namespace}/metrics/history?limit=100
```
Returns recent state change records.

**Response:**
```json
[
  {
    "id": 123,
    "previous_state": "stopped",
    "new_state": "running",
    "previous_replicas": 0,
    "new_replicas": 1,
    "changed_at": "2026-01-14T10:00:00",
    "changed_by": "user@example.com",
    "reason": "Scale to 1 replicas"
  }
]
```

#### Get Comprehensive Metrics
```
GET /api/tenants/{namespace}/metrics
```
Returns all metrics in one call: current state, monthly metrics, and recent history.

## Frontend Display

### Tenant Info Dialog - Uptime Metrics Tab

The tenant information dialog now has two tabs:
1. **Details & Pods**: Original pod and deployment information
2. **Uptime Metrics**: New metrics display showing:
   - Current state and duration
   - Monthly uptime/downtime with percentage bars
   - Recent state change history

### Metrics Display Features

1. **Current State Card**
   - Shows current state (Running/Stopped/Scaling)
   - Duration in current state (formatted as "Xd Yh" or "Xh Ym")
   - Timestamp when state changed

2. **Monthly Metrics Card**
   - Visual progress bars showing uptime/downtime percentages
   - Green bar for uptime percentage
   - Red bar for downtime percentage
   - Formatted durations (e.g., "29d 12h")
   - Note about scaling time if applicable

3. **Recent State Changes Table**
   - Chronological list of state transitions
   - Shows: timestamp, state change, replica changes
   - Color-coded chips for states

## Running State Considerations

The system considers a tenant "running" when:
- Replicas are scaled to >= 1
- This includes the **SCALING** state where pods are being created but not all are ready yet

This design ensures that:
- Upscaling time is counted as uptime (since the tenant is attempting to run)
- Time spent waiting for pods to become ready doesn't count as downtime
- More accurate representation of when a tenant is "operational" vs truly stopped

## Database Migration

To enable this feature, run the database migration:

```bash
cd backend
alembic upgrade head
```

This creates the `tenant_state_history` table with the following schema:
- id (primary key)
- tenant_id (foreign key to tenants)
- previous_state, new_state (enum: running, stopped, scaling, unknown)
- previous_replicas, new_replicas (integer)
- changed_at (timestamp, indexed)
- changed_by (user identifier)
- reason (text description)

## Usage Examples

### Check Current Uptime
To see how long a tenant has been running:
1. Go to Tenants page
2. Click Info button for the tenant
3. Switch to "Uptime Metrics" tab
4. View "Current State" section

### View Monthly Statistics
To see a tenant's uptime/downtime for the current month:
1. Open tenant info dialog
2. Go to "Uptime Metrics" tab
3. View "Monthly Uptime" section with percentage breakdown

### Analyze State Changes
To understand when and why a tenant's state changed:
1. Open tenant info dialog
2. Go to "Uptime Metrics" tab
3. Scroll to "Recent State Changes" table
4. Review chronological state transitions

## Implementation Notes

### State Recording
- State changes are recorded **automatically** when any scaling operation occurs
- The system stores both the previous and new state for complete history
- First scaling operation for a tenant creates an initial state record

### Metrics Calculation
- Monthly metrics are calculated **on-demand** when requested
- The system handles partial months (for current month, calculations use current time as end)
- Historical months use the full month duration

### Performance Considerations
- State history table is indexed on `tenant_id` and `changed_at` for fast queries
- Monthly metrics queries are optimized to only fetch relevant time ranges
- Frontend caches metrics with 30-second refresh interval

## Future Enhancements

Possible improvements:
1. **Historical Trends**: Graph showing uptime trends over multiple months
2. **SLA Monitoring**: Alert when uptime falls below threshold
3. **Scheduled Reports**: Automatic monthly uptime reports
4. **Cost Correlation**: Link uptime to infrastructure costs
5. **Comparison View**: Compare uptime across multiple tenants
