import { apiClient } from './apiClient'
import { Schedule, ScheduleCreate, ScheduleUpdate } from '@/types'

export const scheduleService = {
  // Get all schedules
  async list(tenantId?: number, skip = 0, limit = 100): Promise<Schedule[]> {
    const params: any = { skip, limit }
    if (tenantId) {
      params.tenant_id = tenantId
    }
    return apiClient.get<Schedule[]>('/schedules', params)
  },

  // Get single schedule by ID
  async get(id: number): Promise<Schedule> {
    return apiClient.get<Schedule>(`/schedules/${id}`)
  },

  // Create new schedule
  async create(data: ScheduleCreate): Promise<Schedule> {
    return apiClient.post<Schedule>('/schedules', data)
  },

  // Update schedule
  async update(id: number, data: ScheduleUpdate): Promise<Schedule> {
    return apiClient.put<Schedule>(`/schedules/${id}`, data)
  },

  // Delete schedule
  async delete(id: number): Promise<void> {
    return apiClient.delete<void>(`/schedules/${id}`)
  },

  // Toggle schedule enabled/disabled
  async toggle(id: number, enabled: boolean): Promise<Schedule> {
    return apiClient.patch<Schedule>(`/schedules/${id}`, { enabled })
  },
}
