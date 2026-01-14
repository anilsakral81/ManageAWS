import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Button,
  TextField,
  InputAdornment,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Stack,
  Tooltip,
  CircularProgress,
  Alert,
  List,
  ListItem,
  ListItemText,
  Divider,
  Tabs,
  Tab,
  LinearProgress,
} from '@mui/material'
import {
  Search,
  PlayArrow,
  Stop,
  Refresh,
  Info,
  Schedule as ScheduleIcon,
  Terminal as TerminalIcon,
  Article as LogsIcon,
  Timeline as TimelineIcon,
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { tenantService } from '@/services/tenantService'
import { Tenant } from '@/types'
import PodTerminal from '@/components/PodTerminal'

export default function Tenants() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState(searchParams.get('status') || 'all')
  const [filterNamespace, setFilterNamespace] = useState(searchParams.get('namespace') || '')
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null)
  const [actionDialogOpen, setActionDialogOpen] = useState(false)
  const [actionType, setActionType] = useState<'start' | 'stop'>('start')
  const [infoDialogOpen, setInfoDialogOpen] = useState(false)
  const [infoTab, setInfoTab] = useState(0)
  const [logsDialogOpen, setLogsDialogOpen] = useState(false)
  const [terminalDialogOpen, setTerminalDialogOpen] = useState(false)
  const [selectedPod, setSelectedPod] = useState<string>('')
  const [selectedContainer, setSelectedContainer] = useState<string>('')
  const [availableContainers, setAvailableContainers] = useState<any[]>([])
  const queryClient = useQueryClient()

  // Update filter when URL changes
  useEffect(() => {
    const status = searchParams.get('status')
    if (status && ['all', 'running', 'stopped'].includes(status)) {
      setFilterStatus(status)
    }
    const namespace = searchParams.get('namespace')
    if (namespace) {
      setFilterNamespace(namespace)
    }
  }, [searchParams])

  // Fetch tenants
  const { data: tenants = [], isLoading, error, refetch } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => tenantService.list(),
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Fetch pods for selected tenant
  const { data: pods = [], isLoading: isLoadingPods } = useQuery({
    queryKey: ['pods', selectedTenant?.namespace],
    queryFn: () => tenantService.getPods(selectedTenant!.namespace),
    enabled: !!selectedTenant && infoDialogOpen,
  })

  // Fetch tenant metrics
  const { data: tenantMetrics, isLoading: isLoadingMetrics } = useQuery({
    queryKey: ['tenant-metrics', selectedTenant?.namespace],
    queryFn: () => tenantService.getMetrics(selectedTenant!.namespace),
    enabled: !!selectedTenant && infoDialogOpen,
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Fetch pod containers
  useQuery({
    queryKey: ['containers', selectedTenant?.namespace, selectedPod],
    queryFn: async () => {
      const result = await tenantService.getPodContainers(selectedTenant!.namespace, selectedPod)
      if (result && result.length > 0) {
        setAvailableContainers(result)
        if (!selectedContainer) {
          setSelectedContainer(result[0].name)
        }
      }
      return result
    },
    enabled: !!selectedTenant && !!selectedPod && (logsDialogOpen || terminalDialogOpen),
  })

  // Fetch pod logs
  const { data: logsData, isLoading: isLoadingLogs } = useQuery({
    queryKey: ['logs', selectedTenant?.namespace, selectedPod, selectedContainer],
    queryFn: async () => {
      const result = await tenantService.getPodLogs(selectedTenant!.namespace, selectedPod, selectedContainer)
      return result.logs || result || ''
    },
    enabled: !!selectedTenant && !!selectedPod && logsDialogOpen,
  })

  const logs: string = String(typeof logsData === 'string' ? logsData : (logsData || ''))

  // Start tenant mutation
  const startMutation = useMutation({
    mutationFn: (namespace: string) => tenantService.start(namespace),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] })
      setActionDialogOpen(false)
    },
  })

  // Stop tenant mutation
  const stopMutation = useMutation({
    mutationFn: (namespace: string) => tenantService.stop(namespace),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] })
      setActionDialogOpen(false)
    },
  })

  const filteredTenants = tenants.filter((tenant) => {
    // Filter out tenants with no deployments
    const hasDeployments = tenant.deployment_name && !tenant.deployment_name.includes('0 deployment') && tenant.deployment_name !== 'none'
    const matchesSearch = tenant.name.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus =
      filterStatus === 'all' || tenant.status.toLowerCase() === filterStatus
    const matchesNamespace = !filterNamespace || tenant.namespace === filterNamespace
    return hasDeployments && matchesSearch && matchesStatus && matchesNamespace
  })

  const handleAction = (tenant: Tenant, action: 'start' | 'stop') => {
    setSelectedTenant(tenant)
    setActionType(action)
    setActionDialogOpen(true)
  }

  const handleConfirmAction = () => {
    if (!selectedTenant) return
    
    if (actionType === 'start') {
      startMutation.mutate(selectedTenant.namespace)
    } else {
      stopMutation.mutate(selectedTenant.namespace)
    }
  }

  const handleShowInfo = (tenant: Tenant) => {
    setSelectedTenant(tenant)
    setInfoDialogOpen(true)
  }

  const handleShowPodLogs = (podName: string) => {
    setSelectedPod(podName)
    setSelectedContainer('')
    setAvailableContainers([])
    setLogsDialogOpen(true)
  }

  const handleShowPodTerminal = (podName: string) => {
    setSelectedPod(podName)
    setSelectedContainer('')
    setTerminalDialogOpen(true)
  }

  const isActionLoading = startMutation.isPending || stopMutation.isPending

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Tenants</Typography>
        <Button 
          variant="outlined" 
          startIcon={<Refresh />}
          onClick={() => refetch()}
          disabled={isLoading}
        >
          Refresh
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Failed to load tenants: {error instanceof Error ? error.message : 'Unknown error'}
        </Alert>
      )}

      {(startMutation.isError || stopMutation.isError) && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Action failed: {startMutation.error?.message || stopMutation.error?.message}
        </Alert>
      )}

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems="center">
          <TextField
            placeholder="Search tenants..."
            variant="outlined"
            size="small"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search />
                </InputAdornment>
              ),
            }}
            sx={{ flexGrow: 1 }}
          />
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={filterStatus}
              label="Status"
              onChange={(e) => setFilterStatus(e.target.value)}
            >
              <MenuItem value="all">All</MenuItem>
              <MenuItem value="running">Running</MenuItem>
              <MenuItem value="stopped">Stopped</MenuItem>
            </Select>
          </FormControl>
          {filterNamespace && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Chip 
                label={`Filtered: ${filterNamespace}`}
                onDelete={() => {
                  setFilterNamespace('')
                  setSearchParams({})
                }}
                color="primary"
                size="small"
              />
            </Box>
          )}
        </Stack>
      </Paper>

      {/* Tenants Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Tenant Name</TableCell>
              <TableCell>Namespace</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Replicas</TableCell>
              <TableCell>Resources</TableCell>
              <TableCell>VirtualService</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 5 }}>
                  <CircularProgress />
                </TableCell>
              </TableRow>
            ) : filteredTenants.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 5 }}>
                  <Typography color="textSecondary">No tenants found</Typography>
                </TableCell>
              </TableRow>
            ) : (
              filteredTenants.map((tenant) => (
                <TableRow key={tenant.namespace} hover>
                  <TableCell>
                    <Typography fontWeight="bold">{tenant.name}</Typography>
                  </TableCell>
                  <TableCell>{tenant.namespace}</TableCell>
                  <TableCell>
                    <Chip
                      label={tenant.status}
                      color={tenant.status.toLowerCase() === 'running' ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>{tenant.current_replicas}</TableCell>
                  <TableCell>
                    <Typography variant="body2" color="textSecondary">
                      {tenant.deployment_name}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {tenant.virtualservices && tenant.virtualservices.length > 0 ? (
                      <a
                        href={`http://${tenant.virtualservices[0].host}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ textDecoration: 'none', color: '#1976d2' }}
                      >
                        {tenant.virtualservices[0].host}
                      </a>
                    ) : (
                      <Typography variant="body2" color="textSecondary">N/A</Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={1}>
                      {tenant.status.toLowerCase() === 'stopped' ? (
                        <Tooltip title="Start Tenant">
                          <IconButton
                            color="success"
                            size="small"
                            onClick={() => handleAction(tenant, 'start')}
                          >
                            <PlayArrow />
                          </IconButton>
                        </Tooltip>
                      ) : (
                        <Tooltip title="Stop Tenant">
                          <IconButton
                            color="error"
                            size="small"
                            onClick={() => handleAction(tenant, 'stop')}
                          >
                            <Stop />
                          </IconButton>
                        </Tooltip>
                      )}
                      <Tooltip title="Tenant Info">
                        <IconButton size="small" onClick={() => handleShowInfo(tenant)}>
                          <Info />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Manage Schedule">
                        <IconButton size="small" onClick={() => navigate('/schedules')}>
                          <ScheduleIcon />
                        </IconButton>
                      </Tooltip>
                    </Stack>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Action Confirmation Dialog */}
      <Dialog open={actionDialogOpen} onClose={() => setActionDialogOpen(false)}>
        <DialogTitle>
          Confirm {actionType === 'start' ? 'Start' : 'Stop'} Tenant
        </DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to {actionType} tenant{' '}
            <strong>{selectedTenant?.name}</strong>?
          </Typography>
          {actionType === 'stop' && (
            <Typography variant="body2" color="error" sx={{ mt: 2 }}>
              Warning: This will scale the deployment to 0 replicas and stop all running
              pods.
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setActionDialogOpen(false)} disabled={isActionLoading}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirmAction}
            variant="contained"
            color={actionType === 'start' ? 'success' : 'error'}
            disabled={isActionLoading}
            startIcon={isActionLoading ? <CircularProgress size={16} /> : null}
          >
            {actionType === 'start' ? 'Start' : 'Stop'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Tenant Info Dialog */}
      <Dialog 
        open={infoDialogOpen} 
        onClose={() => setInfoDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Tenant Information - {selectedTenant?.name}</DialogTitle>
        <Tabs value={infoTab} onChange={(_, newValue) => setInfoTab(newValue)} sx={{ borderBottom: 1, borderColor: 'divider', px: 3 }}>
          <Tab label="Details & Pods" />
          <Tab label="Uptime Metrics" icon={<TimelineIcon />} iconPosition="start" />
        </Tabs>
        <DialogContent>
          {selectedTenant && (
            <Box>
              {/* Tab 0: Details & Pods */}
              {infoTab === 0 && (
                <>
                  <Typography variant="h6" gutterBottom>Details</Typography>
                  <Stack spacing={1} mb={3}>
                    <Typography><strong>Namespace:</strong> {selectedTenant.namespace}</Typography>
                    <Typography><strong>Status:</strong> {selectedTenant.status}</Typography>
                    <Typography><strong>Replicas:</strong> {selectedTenant.current_replicas}</Typography>
                    <Typography><strong>Deployment:</strong> {selectedTenant.deployment_name}</Typography>
                  </Stack>

                  {selectedTenant.virtualservices && selectedTenant.virtualservices.length > 0 && (
                    <>
                      <Divider sx={{ my: 2 }} />
                      <Typography variant="h6" gutterBottom>VirtualServices</Typography>
                      <List dense>
                        {selectedTenant.virtualservices.map((vs, index) => (
                          <ListItem key={index}>
                            <ListItemText
                              primary={
                                <a 
                                  href={`http://${vs.host}`} 
                                  target="_blank" 
                                  rel="noopener noreferrer"
                                  style={{ textDecoration: 'none', color: '#1976d2' }}
                                >
                                  {vs.host}
                                </a>
                              }
                              secondary={`Gateway: ${vs.gateways} | VS: ${vs.name}`}
                            />
                          </ListItem>
                        ))}
                      </List>
                    </>
                  )}

                  <Divider sx={{ my: 2 }} />

                  <Typography variant="h6" gutterBottom>Pods</Typography>
                  {isLoadingPods ? (
                    <Box display="flex" justifyContent="center" py={2}>
                      <CircularProgress />
                    </Box>
                  ) : pods.length === 0 ? (
                    <Typography color="textSecondary">No pods found</Typography>
                  ) : (
                    <List sx={{ py: 0 }}>
                      {pods.map((pod: any) => (
                        <Box key={pod.name}>
                          <ListItem 
                            sx={{ 
                              py: 1,
                              px: 2,
                              display: 'flex',
                              alignItems: 'flex-start',
                              justifyContent: 'space-between',
                              gap: 2,
                              borderBottom: '1px solid #e0e0e0'
                            }}
                          >
                            <Box sx={{ minWidth: 0 }}>
                              <Typography variant="body2" fontWeight="medium">
                                {pod.name}
                              </Typography>
                              <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 0.5, mb: 0.5 }}>
                                <Chip 
                                  label={pod.status} 
                                  size="small"
                                  color={pod.status === 'Running' ? 'success' : 'default'}
                                  sx={{ height: 20, fontSize: '0.7rem' }}
                                />
                                <Typography variant="caption" color="textSecondary">
                                  Ready: {pod.ready_containers}/{pod.total_containers}
                                </Typography>
                              </Stack>
                              {pod.containers && pod.containers.length > 0 && (
                                <Box sx={{ mt: 1, ml: 1 }}>
                                  {pod.containers.map((container: any) => (
                                    <Box key={container.name} sx={{ display: 'flex', gap: 1, mb: 0.5 }}>
                                      <Typography variant="caption" color="textSecondary" sx={{ minWidth: 20 }}>
                                        {container.ready ? '✓' : '✗'}
                                      </Typography>
                                      <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>
                                        {container.name}
                                      </Typography>
                                      <Typography variant="caption" color="textSecondary" sx={{ ml: 1 }}>
                                        {container.state}
                                      </Typography>
                                      {container.restarts > 0 && (
                                        <Typography variant="caption" color="warning.main" sx={{ ml: 0.5 }}>
                                          ↻{container.restarts}
                                        </Typography>
                                      )}
                                    </Box>
                                  ))}
                                </Box>
                              )}
                            </Box>
                            <Stack direction="row" spacing={0.5} sx={{ flexShrink: 0 }}>
                              <Tooltip title="View Logs">
                                <IconButton 
                                  size="small"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    handleShowPodLogs(pod.name)
                                  }}
                                >
                                  <LogsIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title="Open Terminal">
                                <IconButton 
                                  size="small"
                                  color="primary"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    handleShowPodTerminal(pod.name)
                                  }}
                                >
                                  <TerminalIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            </Stack>
                          </ListItem>
                        </Box>
                      ))}
                    </List>
                  )}
                </>
              )}

              {/* Tab 1: Metrics */}
              {infoTab === 1 && (
                <>
                  {isLoadingMetrics ? (
                    <Box display="flex" justifyContent="center" py={4}>
                      <CircularProgress />
                    </Box>
                  ) : tenantMetrics ? (
                    <Box>
                      {/* Current State */}
                      <Typography variant="h6" gutterBottom>Current State</Typography>
                      <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
                        <Stack spacing={2}>
                          <Box>
                            <Typography variant="body2" color="textSecondary">Status</Typography>
                            <Chip 
                              label={tenantMetrics.current_state.current_state.toUpperCase()}
                              color={tenantMetrics.current_state.current_state === 'running' ? 'success' : 
                                     tenantMetrics.current_state.current_state === 'stopped' ? 'default' : 'warning'}
                              sx={{ mt: 0.5 }}
                            />
                          </Box>
                          {tenantMetrics.current_state.current_state === 'running' && (
                            <Box>
                              <Typography variant="body2" color="textSecondary">Uptime from Last Startup</Typography>
                              <Typography variant="h5" color="success.main" fontWeight="bold">
                                {tenantMetrics.current_state.duration_formatted}
                              </Typography>
                              {tenantMetrics.current_state.state_since && (
                                <Typography variant="caption" color="textSecondary" sx={{ display: 'block', mt: 0.5 }}>
                                  Started: {new Date(tenantMetrics.current_state.state_since).toLocaleString()}
                                </Typography>
                              )}
                            </Box>
                          )}
                          {tenantMetrics.current_state.current_state !== 'running' && (
                            <Box>
                              <Typography variant="body2" color="textSecondary">Duration in Current State</Typography>
                              <Typography variant="h6">{tenantMetrics.current_state.duration_formatted}</Typography>
                              {tenantMetrics.current_state.state_since && (
                                <Typography variant="caption" color="textSecondary" sx={{ display: 'block', mt: 0.5 }}>
                                  Since: {new Date(tenantMetrics.current_state.state_since).toLocaleString()}
                                </Typography>
                              )}
                            </Box>
                          )}
                        </Stack>
                      </Paper>

                      {/* Monthly Metrics */}
                      {tenantMetrics.monthly_metrics && (
                        <>
                          <Typography variant="h6" gutterBottom>
                            Total Time from 1st of {new Date(tenantMetrics.monthly_metrics.year, tenantMetrics.monthly_metrics.month - 1).toLocaleString('default', { month: 'long', year: 'numeric' })}
                          </Typography>
                          <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
                            <Stack spacing={3}>
                              {/* Total Uptime Summary */}
                              <Box sx={{ bgcolor: 'success.50', p: 2, borderRadius: 1, border: '1px solid', borderColor: 'success.200' }}>
                                <Typography variant="body2" color="textSecondary" gutterBottom>Total Uptime This Month</Typography>
                                <Typography variant="h4" color="success.main" fontWeight="bold">
                                  {tenantMetrics.monthly_metrics.uptime_formatted}
                                </Typography>
                                <Typography variant="caption" color="textSecondary">
                                  {tenantMetrics.monthly_metrics.uptime_percentage.toFixed(1)}% of the month
                                  {tenantMetrics.monthly_metrics.scaling_seconds > 0 && 
                                    ` (includes ${tenantMetrics.monthly_metrics.scaling_formatted} scaling time)`}
                                </Typography>
                              </Box>

                              {/* Progress Bars */}
                              <Box>
                                <Box display="flex" justifyContent="space-between" mb={1}>
                                  <Typography variant="body2">Running Time</Typography>
                                  <Typography variant="body2" fontWeight="bold" color="success.main">
                                    {tenantMetrics.monthly_metrics.uptime_percentage.toFixed(1)}%
                                  </Typography>
                                </Box>
                                <LinearProgress 
                                  variant="determinate" 
                                  value={tenantMetrics.monthly_metrics.uptime_percentage} 
                                  color="success"
                                  sx={{ height: 10, borderRadius: 5 }}
                                />
                              </Box>
                              <Box>
                                <Box display="flex" justifyContent="space-between" mb={1}>
                                  <Typography variant="body2">Stopped Time</Typography>
                                  <Typography variant="body2" fontWeight="bold" color="error.main">
                                    {tenantMetrics.monthly_metrics.downtime_percentage.toFixed(1)}%
                                  </Typography>
                                </Box>
                                <LinearProgress 
                                  variant="determinate" 
                                  value={tenantMetrics.monthly_metrics.downtime_percentage} 
                                  color="error"
                                  sx={{ height: 10, borderRadius: 5 }}
                                />
                                <Typography variant="caption" color="textSecondary" sx={{ mt: 0.5, display: 'block' }}>
                                  {tenantMetrics.monthly_metrics.downtime_formatted} stopped
                                </Typography>
                              </Box>
                            </Stack>
                          </Paper>
                        </>
                      )}

                      {/* Recent History */}
                      {tenantMetrics.recent_history && tenantMetrics.recent_history.length > 0 && (
                        <>
                          <Typography variant="h6" gutterBottom>Recent State Changes</Typography>
                          <TableContainer component={Paper} variant="outlined">
                            <Table size="small">
                              <TableHead>
                                <TableRow>
                                  <TableCell>Time</TableCell>
                                  <TableCell>State Change</TableCell>
                                  <TableCell>Replicas</TableCell>
                                </TableRow>
                              </TableHead>
                              <TableBody>
                                {tenantMetrics.recent_history.map((record) => (
                                  <TableRow key={record.id}>
                                    <TableCell>
                                      <Typography variant="caption">
                                        {new Date(record.changed_at).toLocaleString()}
                                      </Typography>
                                    </TableCell>
                                    <TableCell>
                                      <Stack direction="row" spacing={1} alignItems="center">
                                        {record.previous_state && (
                                          <Chip label={record.previous_state} size="small" />
                                        )}
                                        <Typography variant="caption">→</Typography>
                                        <Chip 
                                          label={record.new_state} 
                                          size="small"
                                          color={record.new_state === 'running' ? 'success' : 
                                                 record.new_state === 'stopped' ? 'default' : 'warning'}
                                        />
                                      </Stack>
                                    </TableCell>
                                    <TableCell>
                                      {record.previous_replicas !== null && `${record.previous_replicas} → `}
                                      {record.new_replicas}
                                    </TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </TableContainer>
                        </>
                      )}
                    </Box>
                  ) : (
                    <Alert severity="info">No metrics available for this tenant</Alert>
                  )}
                </>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setInfoDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Pod Logs Dialog */}
      <Dialog 
        open={logsDialogOpen} 
        onClose={() => setLogsDialogOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">Pod Logs - {selectedPod}</Typography>
            {availableContainers.length > 1 && (
              <FormControl size="small" sx={{ minWidth: 200 }}>
                <InputLabel>Container</InputLabel>
                <Select
                  value={selectedContainer}
                  label="Container"
                  onChange={(e) => setSelectedContainer(e.target.value)}
                >
                  {availableContainers.map((container: any) => (
                    <MenuItem key={container.name} value={container.name}>
                      {container.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}
          </Box>
        </DialogTitle>
        <DialogContent>
          {isLoadingLogs ? (
            <Box display="flex" justifyContent="center" py={5}>
              <CircularProgress />
            </Box>
          ) : (
            <Paper 
              sx={{ 
                p: 2, 
                bgcolor: '#1e1e1e', 
                color: '#d4d4d4',
                fontFamily: 'monospace',
                fontSize: '12px',
                maxHeight: '500px',
                overflow: 'auto',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
              }}
            >
              {logs || 'No logs available'}
            </Paper>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setLogsDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Pod Terminal Dialog */}
      <Dialog 
        open={terminalDialogOpen} 
        onClose={() => setTerminalDialogOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>Terminal - {selectedPod}</DialogTitle>
        <DialogContent sx={{ p: 0, height: '500px' }}>
          {selectedTenant && selectedPod && (
            <PodTerminal 
              namespace={selectedTenant.namespace}
              podName={selectedPod}
              container={selectedContainer}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTerminalDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
