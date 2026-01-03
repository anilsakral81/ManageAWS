import { tenantService } from './tenantService'
import { DashboardStats } from '@/types'

export const dashboardService = {
  // Get dashboard statistics
  async getStats(): Promise<DashboardStats> {
    // Fetch all tenants and calculate stats
    const tenants = await tenantService.list()
    
    const stats: DashboardStats = {
      total_tenants: tenants.length,
      running_tenants: tenants.filter(t => t.status.toLowerCase() === 'running').length,
      stopped_tenants: tenants.filter(t => t.status.toLowerCase() === 'stopped').length,
      scheduled_actions: 0, // Will be calculated from schedules
    }
    
    return stats
  },
}
