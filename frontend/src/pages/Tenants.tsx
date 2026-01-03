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
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { tenantService } from '@/services/tenantService'
import { Tenant } from '@/types'
import PodTerminal from '@/components/PodTerminal'

export default function Tenants() {
  const [searchParams] = useSearchParams()
  const [searchQuery, setSearchQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState(searchParams.get('status') || 'all')
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null)
  const [actionDialogOpen, setActionDialogOpen] = useState(false)
  const [actionType, setActionType] = useState<'start' | 'stop'>('start')
  const [infoDialogOpen, setInfoDialogOpen] = useState(false)
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
    const matchesSearch = tenant.name.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus =
      filterStatus === 'all' || tenant.status.toLowerCase() === filterStatus
    return matchesSearch && matchesStatus
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
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
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
                        <IconButton size="small">
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
        <DialogContent>
          {selectedTenant && (
            <Box>
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
                          gap: 2,
                          borderBottom: '1px solid #e0e0e0'
                        }}
                      >
                        <Box sx={{ flex: 1, minWidth: 0 }}>
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
                                  <Typography variant="caption" sx={{ fontFamily: 'monospace', flex: 1 }}>
                                    {container.name}
                                  </Typography>
                                  <Typography variant="caption" color="textSecondary">
                                    {container.state}
                                  </Typography>
                                  {container.restarts > 0 && (
                                    <Typography variant="caption" color="warning.main">
                                      ↻{container.restarts}
                                    </Typography>
                                  )}
                                </Box>
                              ))}
                            </Box>
                          )}
                        </Box>
                        <Stack direction="row" spacing={0.5}>
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
