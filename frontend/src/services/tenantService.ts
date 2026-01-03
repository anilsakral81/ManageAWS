import { apiClient } from './apiClient'
import { Tenant, TenantScaleRequest, Pod, Container, PodLogs } from '@/types'

export const tenantService = {
  // Get all tenants (namespaces)
  async list(skip = 0, limit = 100): Promise<Tenant[]> {
    return apiClient.get<Tenant[]>('/tenants', { skip, limit })
  },

  // Get single tenant by namespace
  async get(namespace: string): Promise<Tenant> {
    return apiClient.get<Tenant>(`/tenants/${namespace}`)
  },

  // Scale tenant (all deployments in namespace)
  async scale(namespace: string, replicas: number): Promise<Tenant> {
    const data: TenantScaleRequest = { replicas }
    return apiClient.post<Tenant>(`/tenants/${namespace}/scale`, data)
  },

  // Start tenant (scale all deployments to 1)
  async start(namespace: string): Promise<Tenant> {
    return apiClient.post<Tenant>(`/tenants/${namespace}/start`)
  },

  // Stop tenant (scale all deployments to 0)
  async stop(namespace: string): Promise<Tenant> {
    return apiClient.post<Tenant>(`/tenants/${namespace}/stop`)
  },

  // Get pods in tenant namespace
  async getPods(namespace: string): Promise<Pod[]> {
    return apiClient.get<Pod[]>(`/tenants/${namespace}/pods`)
  },

  // Get containers in a pod
  async getPodContainers(namespace: string, podName: string): Promise<Container[]> {
    return apiClient.get<Container[]>(`/tenants/${namespace}/pods/${podName}/containers`)
  },

  // Get pod logs
  async getPodLogs(namespace: string, podName: string, container?: string, tailLines = 100): Promise<PodLogs> {
    const params: any = { tail_lines: tailLines }
    if (container) {
      params.container = container
    }
    return apiClient.get<PodLogs>(`/tenants/${namespace}/pods/${podName}/logs`, params)
  },

  // Execute command in pod
  async execPodCommand(namespace: string, podName: string, command: string[], container?: string): Promise<any> {
    const data: any = { command }
    if (container) {
      data.container = container
    }
    return apiClient.post<any>(`/tenants/${namespace}/pods/${podName}/exec`, data)
  },
}
