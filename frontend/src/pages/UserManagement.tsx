import { useState } from 'react'
import {
  Box,
  Typography,
  Paper,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Chip,
  Alert,
  Stack,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material'
import { Delete, Add, PersonAdd } from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { userService, type UserNamespacePermission } from '@/services/userService'
import { tenantService } from '@/services/tenantService'

export default function UserManagement() {
  const [grantDialogOpen, setGrantDialogOpen] = useState(false)
  const [selectedUserId, setSelectedUserId] = useState('')
  const [selectedNamespace, setSelectedNamespace] = useState('')
  const queryClient = useQueryClient()

  // Fetch all permissions
  const { data: permissions = [], isLoading, error } = useQuery({
    queryKey: ['user-permissions'],
    queryFn: () => userService.getAllPermissions(),
  })

  // Fetch all namespaces (tenants)
  const { data: tenants = [] } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => tenantService.list(),
  })

  // Grant access mutation
  const grantMutation = useMutation({
    mutationFn: (permission: { user_id: string; namespace: string }) =>
      userService.grantNamespaceAccess(permission),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-permissions'] })
      setGrantDialogOpen(false)
      setSelectedUserId('')
      setSelectedNamespace('')
    },
  })

  // Revoke access mutation
  const revokeMutation = useMutation({
    mutationFn: ({ userId, namespace }: { userId: string; namespace: string }) =>
      userService.revokeNamespaceAccess(userId, namespace),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-permissions'] })
    },
  })

  const handleGrantAccess = () => {
    if (selectedUserId && selectedNamespace) {
      grantMutation.mutate({
        user_id: selectedUserId,
        namespace: selectedNamespace,
      })
    }
  }

  const handleRevokeAccess = (userId: string, namespace: string) => {
    if (confirm(`Revoke access for ${userId} to namespace ${namespace}?`)) {
      revokeMutation.mutate({ userId, namespace })
    }
  }

  // Group permissions by user
  const groupedPermissions = permissions.reduce((acc, perm) => {
    if (!acc[perm.user_id]) {
      acc[perm.user_id] = []
    }
    acc[perm.user_id].push(perm)
    return acc
  }, {} as Record<string, UserNamespacePermission[]>)

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">User Management</Typography>
        <Button
          variant="contained"
          startIcon={<PersonAdd />}
          onClick={() => setGrantDialogOpen(true)}
        >
          Grant Access
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to load user permissions
        </Alert>
      )}

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>User ID</TableCell>
              <TableCell>Allowed Namespaces</TableCell>
              <TableCell>Granted By</TableCell>
              <TableCell>Granted At</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  Loading...
                </TableCell>
              </TableRow>
            ) : Object.entries(groupedPermissions).length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  No user permissions configured
                </TableCell>
              </TableRow>
            ) : (
              Object.entries(groupedPermissions).map(([userId, userPerms]) => (
                <TableRow key={userId}>
                  <TableCell>
                    <Typography variant="body2" fontFamily="monospace">
                      {userId}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={1} flexWrap="wrap" gap={1}>
                      {userPerms.map((perm) => (
                        <Chip
                          key={perm.namespace}
                          label={perm.namespace}
                          size="small"
                          onDelete={() => handleRevokeAccess(userId, perm.namespace)}
                          deleteIcon={<Delete />}
                        />
                      ))}
                    </Stack>
                  </TableCell>
                  <TableCell>
                    {userPerms[0]?.granted_by || '-'}
                  </TableCell>
                  <TableCell>
                    {new Date(userPerms[0]?.granted_at).toLocaleString()}
                  </TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      onClick={() => {
                        setSelectedUserId(userId)
                        setGrantDialogOpen(true)
                      }}
                      title="Add more namespaces"
                    >
                      <Add />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Grant Access Dialog */}
      <Dialog open={grantDialogOpen} onClose={() => setGrantDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Grant Namespace Access</DialogTitle>
        <DialogContent>
          <Stack spacing={3} sx={{ mt: 2 }}>
            <TextField
              label="User ID (Keycloak sub)"
              value={selectedUserId}
              onChange={(e) => setSelectedUserId(e.target.value)}
              fullWidth
              placeholder="e.g., a1b2c3d4-e5f6-7890-abcd-ef1234567890"
              helperText="Enter the Keycloak user ID from the token"
            />
            <FormControl fullWidth>
              <InputLabel>Namespace</InputLabel>
              <Select
                value={selectedNamespace}
                label="Namespace"
                onChange={(e) => setSelectedNamespace(e.target.value)}
              >
                {tenants.map((tenant) => (
                  <MenuItem key={tenant.namespace} value={tenant.namespace}>
                    {tenant.namespace}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setGrantDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleGrantAccess}
            variant="contained"
            disabled={!selectedUserId || !selectedNamespace || grantMutation.isPending}
          >
            {grantMutation.isPending ? 'Granting...' : 'Grant Access'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
