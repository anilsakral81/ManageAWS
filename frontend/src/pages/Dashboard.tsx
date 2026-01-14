import {
  Grid,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  CircularProgress,
  Alert,
} from '@mui/material'
import {
  TrendingUp,
  TrendingDown,
  CloudQueue,
  Schedule as ScheduleIcon,
} from '@mui/icons-material'
import { useQuery } from '@tanstack/react-query'
import { tenantService } from '@/services/tenantService'
import { scheduleService } from '@/services/scheduleService'
import { auditService } from '@/services/auditService'
import { useNavigate } from 'react-router-dom'

export default function Dashboard() {
  const navigate = useNavigate()

  // Fetch tenants
  const { data: tenants = [], isLoading: tenantsLoading, error: tenantsError } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => tenantService.list(),
    refetchInterval: 30000,
  })

  // Fetch schedules
  const { data: schedules = [] } = useQuery({
    queryKey: ['schedules'],
    queryFn: () => scheduleService.list(),
  })

  // Fetch recent audit logs
  const { data: auditLogs = [] } = useQuery({
    queryKey: ['audit-logs-recent'],
    queryFn: () => auditService.list({ limit: 10 }),
  })

  // Filter tenants with deployments only
  const tenantsWithDeployments = tenants.filter(t => 
    t.deployment_name && !t.deployment_name.includes('0 deployment') && t.deployment_name !== 'none'
  )

  // Calculate stats
  const stats = {
    totalTenants: tenantsWithDeployments.length,
    runningTenants: tenantsWithDeployments.filter(t => t.status.toLowerCase() === 'running').length,
    stoppedTenants: tenantsWithDeployments.filter(t => t.status.toLowerCase() === 'stopped').length,
    scheduledActions: schedules.filter(s => s.enabled).length,
  }

  // Get active tenants (running ones)
  const activeTenants = tenantsWithDeployments.filter(t => t.status.toLowerCase() === 'running').slice(0, 4)

  // Format audit logs for recent activity
  const recentActivity = auditLogs.slice(0, 4).map(log => ({
    id: log.id,
    tenant: log.tenant_name || 'Unknown',
    action: log.action,
    user: log.user_id,
    time: formatRelativeTime(log.created_at),
  }))

  function formatRelativeTime(timestamp: string): string {
    const now = new Date()
    const past = new Date(timestamp)
    const diffMs = now.getTime() - past.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    
    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins} mins ago`
    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
    const diffDays = Math.floor(diffHours / 24)
    return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>

      {tenantsError && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Failed to load dashboard data: {tenantsError instanceof Error ? tenantsError.message : 'Unknown error'}
        </Alert>
      )}

      {tenantsLoading ? (
        <Box display="flex" justifyContent="center" py={5}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          {/* Stats Cards */}
          <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card 
            sx={{ cursor: 'pointer', '&:hover': { boxShadow: 4 } }}
            onClick={() => navigate('/tenants?status=all')}
          >
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Total Tenants
                  </Typography>
                  <Typography variant="h4">{stats.totalTenants}</Typography>
                </Box>
                <CloudQueue sx={{ fontSize: 48, color: 'primary.main', opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card 
            sx={{ cursor: 'pointer', '&:hover': { boxShadow: 4 } }}
            onClick={() => navigate('/tenants?status=running')}
          >
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Running
                  </Typography>
                  <Typography variant="h4" color="success.main">
                    {stats.runningTenants}
                  </Typography>
                </Box>
                <TrendingUp sx={{ fontSize: 48, color: 'success.main', opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card 
            sx={{ cursor: 'pointer', '&:hover': { boxShadow: 4 } }}
            onClick={() => navigate('/tenants?status=stopped')}
          >
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Stopped
                  </Typography>
                  <Typography variant="h4" color="error.main">
                    {stats.stoppedTenants}
                  </Typography>
                </Box>
                <TrendingDown sx={{ fontSize: 48, color: 'error.main', opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Scheduled Actions
                  </Typography>
                  <Typography variant="h4">{stats.scheduledActions}</Typography>
                </Box>
                <ScheduleIcon sx={{ fontSize: 48, color: 'primary.main', opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* Active Tenants */}
        <Grid item xs={12} lg={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Active Tenants
            </Typography>
            {activeTenants.length === 0 ? (
              <Typography color="textSecondary" align="center" py={3}>
                No active tenants
              </Typography>
            ) : (
              activeTenants.map((tenant) => (
                <Card key={tenant.id} sx={{ mb: 2 }}>
                  <CardContent>
                    <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                      <Box>
                        <Typography variant="h6">{tenant.name}</Typography>
                        <Typography variant="body2" color="textSecondary">
                          Namespace: {tenant.namespace}
                        </Typography>
                      </Box>
                      <Chip
                        label={tenant.status}
                        color={tenant.status === 'Running' ? 'success' : 'default'}
                        size="small"
                      />
                    </Box>
                    <Grid container spacing={2}>
                      <Grid item xs={12} sm={6}>
                        <Typography variant="body2" color="textSecondary">
                          Replicas: {tenant.current_replicas} / {tenant.desired_replicas}
                        </Typography>
                        <Typography variant="body2" color="textSecondary">
                          Resources: {tenant.deployment_name}
                        </Typography>
                      </Grid>
                      {tenant.virtualservices && tenant.virtualservices.length > 0 && (
                        <Grid item xs={12} sm={6}>
                          <Typography variant="body2" color="textSecondary">
                            Host:{' '}
                            <a
                              href={`http://${tenant.virtualservices[0].host}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{ color: '#1976d2', textDecoration: 'none' }}
                            >
                              {tenant.virtualservices[0].host}
                            </a>
                          </Typography>
                        </Grid>
                      )}
                    </Grid>
                  </CardContent>
                  <CardActions>
                    <Button size="small" onClick={() => navigate(`/tenants?namespace=${tenant.namespace}`)}>View Details</Button>
                  </CardActions>
                </Card>
              ))
            )}
          </Paper>
        </Grid>

        {/* Recent Activity */}
        <Grid item xs={12} lg={4}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Recent Activity
            </Typography>
            {recentActivity.length === 0 ? (
              <Typography color="textSecondary" align="center" py={3}>
                No recent activity
              </Typography>
            ) : (
              recentActivity.map((activity) => (
                <Box key={activity.id} sx={{ mb: 2, pb: 2, borderBottom: '1px solid #e0e0e0' }}>
                  <Typography variant="body1" fontWeight="bold">
                    {activity.tenant}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    {activity.action} by {activity.user}
                  </Typography>
                  <Typography variant="caption" color="textSecondary">
                    {activity.time}
                  </Typography>
                </Box>
              ))
            )}
          </Paper>
        </Grid>
      </Grid>
        </>
      )}
    </Box>
  )
}
