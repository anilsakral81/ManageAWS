import { apiClient } from './apiClient'
import { AuditLog } from '@/types'

export const auditService = {
  // Get audit logs with filters
  async list(params: {
    tenant_id?: number
    user_id?: string
    action?: string
    start_date?: string
    end_date?: string
    skip?: number
    limit?: number
  } = {}): Promise<AuditLog[]> {
    return apiClient.get<AuditLog[]>('/audit-logs', params)
  },

  // Get single audit log by ID
  async get(id: number): Promise<AuditLog> {
    return apiClient.get<AuditLog>(`/audit-logs/${id}`)
  },
}
