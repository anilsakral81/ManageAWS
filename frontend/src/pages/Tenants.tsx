import { useState } from 'react'
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
} from '@mui/material'
import {
  Search,
  PlayArrow,
  Stop,
  Refresh,
  Info,
  Schedule as ScheduleIcon,
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { tenantService } from '@/services/tenantService'
import { Tenant } from '@/types'

export default function Tenants() {
  const [searchQuery, setSearchQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState('all')
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null)
  const [actionDialogOpen, setActionDialogOpen] = useState(false)
  const [actionType, setActionType] = useState<'start' | 'stop'>('start')
  const queryClient = useQueryClient()

  // Fetch tenants
  const { data: tenants = [], isLoading, error, refetch } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => tenantService.list(),
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Start tenant mutation
  const startMutation = useMutation({
    mutationFn: (id: number) => tenantService.start(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] })
      setActionDialogOpen(false)
    },
  })

  // Stop tenant mutation
  const stopMutation = useMutation({
    mutationFn: (id: number) => tenantService.stop(id),
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
      startMutation.mutate(selectedTenant.id)
    } else {
      stopMutation.mutate(selectedTenant.id)
    }
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
              <TableCell>Deployment</TableCell>
              <TableCell>Last Action</TableCell>
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
                <TableRow key={tenant.id} hover>
                  <TableCell>
                    <Typography fontWeight="bold">{tenant.name}</Typography>
                  </TableCell>
                  <TableCell>{tenant.namespace}</TableCell>
                  <TableCell>
                    <Chip
                      label={tenant.status}
                      color={tenant.status === 'Running' ? 'success' : 'default'}
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
                    <Typography variant="body2">{tenant.last_action || 'N/A'}</Typography>
                    {tenant.last_action_by && (
                      <Typography variant="caption" color="textSecondary">
                        by {tenant.last_action_by}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={1}>
                      {tenant.status === 'Stopped' ? (
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
                        <IconButton size="small">
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
    </Box>
  )
}
