export interface VirtualService {
  name: string
  host: string
  gateways: string
}

export interface Tenant {
  id: number
  name: string
  namespace: string
  deployment_name: string
  current_replicas: number
  desired_replicas: number
  status: 'Running' | 'Stopped' | 'Scaling'
  created_at: string
  updated_at: string
  last_action?: string
  last_action_by?: string
  last_action_at?: string
  virtualservices?: VirtualService[]
}

export interface Pod {
  name: string
  status: string
  ready: number
  total_containers: number
  restarts: number
  node: string
  created_at: string
}

export interface Container {
  name: string
  image: string
  ready: boolean
  restart_count: number
  state: string
}

export interface PodLogs {
  logs: string
  pod: string
  container: string | null
}

export interface TenantCreate {
  name: string
  namespace: string
  deployment_name: string
  desired_replicas?: number
}

export interface TenantUpdate {
  name?: string
  desired_replicas?: number
}

export interface TenantScaleRequest {
  replicas: number
}

export interface Schedule {
  id: number
  tenant_id: number
  tenant_name?: string
  action: 'start' | 'stop'
  cron_expression: string
  description?: string
  enabled: boolean
  next_run?: string
  created_at: string
  updated_at: string
}

export interface ScheduleCreate {
  tenant_id?: number  // deprecated
  namespace?: string
  action: 'start' | 'stop'
  cron_expression: string
  description?: string
  enabled?: boolean
}

export interface ScheduleUpdate {
  action?: 'start' | 'stop'
  cron_expression?: string
  description?: string
  enabled?: boolean
}

export interface AuditLog {
  id: number
  user_id: string
  user_name?: string
  tenant_id?: number
  tenant_name?: string
  action: string
  status: 'success' | 'failed'
  details?: string
  ip_address?: string
  created_at: string
}

export interface DashboardStats {
  total_tenants: number
  running_tenants: number
  stopped_tenants: number
  scheduled_actions: number
}

// Metrics types

export interface CurrentStateDuration {
  current_state: string
  duration_seconds: number
  duration_formatted: string
  state_since: string | null
  changed_by: string | null
}

export interface MonthlyMetrics {
  year: number
  month: number
  uptime_seconds: number
  downtime_seconds: number
  scaling_seconds: number
  uptime_percentage: number
  downtime_percentage: number
  uptime_formatted: string
  downtime_formatted: string
  scaling_formatted: string
  total_seconds: number
  month_start: string
  month_end: string
}

export interface StateHistoryRecord {
  id: number
  previous_state: string | null
  new_state: string
  previous_replicas: number | null
  new_replicas: number
  changed_at: string
  changed_by: string | null
  reason: string | null
}

export interface TenantMetrics {
  tenant_id: number
  tenant_name: string
  namespace: string
  current_state: CurrentStateDuration
  monthly_metrics: MonthlyMetrics | null
  recent_history: StateHistoryRecord[]
}

export interface CurrentStateDuration {
  current_state: string
  duration_seconds: number
  duration_formatted: string
  state_since: string | null
  changed_by: string | null
}

export interface MonthlyMetrics {
  year: number
  month: number
  uptime_seconds: number
  downtime_seconds: number
  scaling_seconds: number
  uptime_percentage: number
  downtime_percentage: number
  uptime_formatted: string
  downtime_formatted: string
  scaling_formatted: string
  total_seconds: number
  month_start: string
  month_end: string
}

export interface StateHistoryRecord {
  id: number
  previous_state: string | null
  new_state: string
  previous_replicas: number | null
  new_replicas: number
  changed_at: string
  changed_by: string | null
  reason: string | null
}

export interface TenantMetrics {
  tenant_id: number
  tenant_name: string
  namespace: string
  current_state: CurrentStateDuration
  monthly_metrics?: MonthlyMetrics
  recent_history: StateHistoryRecord[]
}
