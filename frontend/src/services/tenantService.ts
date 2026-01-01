import { apiClient } from './apiClient'
import { Tenant, TenantCreate, TenantUpdate, TenantScaleRequest } from '@/types'

export const tenantService = {
  // Get all tenants
  async list(skip = 0, limit = 100): Promise<Tenant[]> {
    return apiClient.get<Tenant[]>('/tenants', { skip, limit })
  },

  // Get single tenant by ID
  async get(id: number): Promise<Tenant> {
    return apiClient.get<Tenant>(`/tenants/${id}`)
  },

  // Create new tenant
  async create(data: TenantCreate): Promise<Tenant> {
    return apiClient.post<Tenant>('/tenants', data)
  },

  // Update tenant
  async update(id: number, data: TenantUpdate): Promise<Tenant> {
    return apiClient.put<Tenant>(`/tenants/${id}`, data)
  },

  // Delete tenant
  async delete(id: number): Promise<void> {
    return apiClient.delete<void>(`/tenants/${id}`)
  },

  // Scale tenant (start/stop)
  async scale(id: number, replicas: number): Promise<Tenant> {
    const data: TenantScaleRequest = { replicas }
    return apiClient.post<Tenant>(`/tenants/${id}/scale`, data)
  },

  // Start tenant (scale to desired replicas)
  async start(id: number): Promise<Tenant> {
    return apiClient.post<Tenant>(`/tenants/${id}/start`)
  },

  // Stop tenant (scale to 0)
  async stop(id: number): Promise<Tenant> {
    return apiClient.post<Tenant>(`/tenants/${id}/stop`)
  },

  // Get tenant status from Kubernetes
  async getStatus(id: number): Promise<Tenant> {
    return apiClient.get<Tenant>(`/tenants/${id}/status`)
  },
}
