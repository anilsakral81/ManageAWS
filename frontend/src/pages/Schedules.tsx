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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Stack,
  Switch,
  FormControlLabel,
  Tooltip,
  CircularProgress,
  Alert,
} from '@mui/material'
import { Add, Edit, Delete } from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { scheduleService } from '@/services/scheduleService'
import { tenantService } from '@/services/tenantService'
import { Schedule, ScheduleCreate } from '@/types'
import CronBuilder from '@/components/CronBuilder'

export default function Schedules() {
  const [openDialog, setOpenDialog] = useState(false)
  const [editingSchedule, setEditingSchedule] = useState<Schedule | null>(null)
  const [formData, setFormData] = useState<ScheduleCreate>({
    namespace: '',
    action: 'start',
    cron_expression: '',
    description: '',
    enabled: true,
  })
  const queryClient = useQueryClient()

  // Fetch schedules
  const { data: schedules = [], isLoading, error } = useQuery({
    queryKey: ['schedules'],
    queryFn: () => scheduleService.list(),
  })

  // Fetch tenants for dropdown
  const { data: tenants = [] } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => tenantService.list(),
  })

  // Create schedule mutation
  const createMutation = useMutation({
    mutationFn: (data: ScheduleCreate) => scheduleService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedules'] })
      setOpenDialog(false)
      resetForm()
    },
  })

  // Update schedule mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => 
      scheduleService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedules'] })
      setOpenDialog(false)
      resetForm()
    },
  })

  // Delete schedule mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) => scheduleService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedules'] })
    },
  })

  const resetForm = () => {
    setFormData({
      namespace: '',
      action: 'start',
      cron_expression: '',
      description: '',
      enabled: true,
    })
    setEditingSchedule(null)
  }
  const handleAddSchedule = () => {
    resetForm()
    setOpenDialog(true)
  }

  const handleEditSchedule = (schedule: Schedule) => {
    setEditingSchedule(schedule)
    setFormData({
      namespace: schedule.tenant_name || '',  // Use tenant_name as namespace
      action: schedule.action,
      cron_expression: schedule.cron_expression,
      description: schedule.description || '',
      enabled: schedule.enabled,
    })
    setOpenDialog(true)
  }

  const handleDeleteSchedule = (scheduleId: number) => {
    if (confirm('Are you sure you want to delete this schedule?')) {
      deleteMutation.mutate(scheduleId)
    }
  }

  const handleSaveSchedule = () => {
    if (editingSchedule) {
      updateMutation.mutate({
        id: editingSchedule.id,
        data: {
          action: formData.action,
          cron_expression: formData.cron_expression,
          description: formData.description,
          enabled: formData.enabled,
        },
      })
    } else {
      createMutation.mutate(formData)
    }
  }

  const isFormValid = formData.namespace && formData.namespace.trim() !== '' && formData.cron_expression.trim() !== ''

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Schedules</Typography>
        <Button variant="contained" startIcon={<Add />} onClick={handleAddSchedule}>
          Add Schedule
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Failed to load schedules: {error instanceof Error ? error.message : 'Unknown error'}
        </Alert>
      )}

      {(createMutation.isError || updateMutation.isError || deleteMutation.isError) && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Action failed: {createMutation.error?.message || updateMutation.error?.message || deleteMutation.error?.message}
        </Alert>
      )}

      {/* Schedules Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Tenant</TableCell>
              <TableCell>Action</TableCell>
              <TableCell>Schedule (Cron)</TableCell>
              <TableCell>Description</TableCell>
              <TableCell>Next Run</TableCell>
              <TableCell>Status</TableCell>
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
            ) : schedules.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 5 }}>
                  <Typography color="textSecondary">No schedules found</Typography>
                </TableCell>
              </TableRow>
            ) : (
              schedules.map((schedule) => (
                <TableRow key={schedule.id} hover>
                  <TableCell>
                    <Typography fontWeight="bold">{schedule.tenant_name || `Tenant ${schedule.tenant_id}`}</Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={schedule.action.toUpperCase()}
                      color={schedule.action === 'start' ? 'success' : 'error'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" fontFamily="monospace">
                      {schedule.cron_expression}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="textSecondary">
                      {schedule.description || 'N/A'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">{schedule.next_run || 'N/A'}</Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={schedule.enabled ? 'Enabled' : 'Disabled'}
                      color={schedule.enabled ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={1}>
                      <Tooltip title="Edit Schedule">
                        <IconButton
                          size="small"
                          color="primary"
                          onClick={() => handleEditSchedule(schedule)}
                        >
                          <Edit />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete Schedule">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleDeleteSchedule(schedule.id)}
                          disabled={deleteMutation.isPending}
                        >
                          <Delete />
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

      {/* Add/Edit Schedule Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingSchedule ? 'Edit Schedule' : 'Add New Schedule'}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={3} sx={{ mt: 2 }}>
            <FormControl fullWidth>
              <InputLabel>Tenant</InputLabel>
              <Select 
                label="Tenant" 
                value={formData.namespace}
                onChange={(e) => setFormData({ ...formData, namespace: e.target.value })}
                disabled={!!editingSchedule}
              >
                {tenants.map((tenant) => (
                  <MenuItem key={tenant.id} value={tenant.namespace}>
                    {tenant.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl fullWidth>
              <InputLabel>Action</InputLabel>
              <Select 
                label="Action" 
                value={formData.action}
                onChange={(e) => setFormData({ ...formData, action: e.target.value as 'start' | 'stop' })}
              >
                <MenuItem value="start">Start</MenuItem>
                <MenuItem value="stop">Stop</MenuItem>
              </Select>
            </FormControl>

            <CronBuilder
              value={formData.cron_expression}
              onChange={(value) => setFormData({ ...formData, cron_expression: value })}
            />

            <TextField
              fullWidth
              label="Description"
              placeholder="Stop at 6 PM on weekdays"
              multiline
              rows={2}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            />

            <FormControlLabel
              control={
                <Switch 
                  checked={formData.enabled}
                  onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                />
              }
              label="Enable this schedule"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)} disabled={createMutation.isPending || updateMutation.isPending}>
            Cancel
          </Button>
          <Button 
            onClick={handleSaveSchedule} 
            variant="contained"
            disabled={!isFormValid || createMutation.isPending || updateMutation.isPending}
            startIcon={
              (createMutation.isPending || updateMutation.isPending) ? <CircularProgress size={16} /> : null
            }
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
