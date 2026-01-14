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
  Autocomplete,
  Tabs,
  Tab,
  FormControlLabel,
  Checkbox,
} from '@mui/material'
import { Delete, Add, PersonAdd, VpnKey } from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { userService, type UserNamespacePermission, type KeycloakUser, type UserCreate, type PasswordReset } from '@/services/userService'
import { tenantService } from '@/services/tenantService'
import { useKeycloak } from '@/contexts/KeycloakContext'

export default function UserManagement() {
  const { user: currentUser } = useKeycloak()
  const isAdmin = currentUser?.roles?.includes('admin') || false
  const [activeTab, setActiveTab] = useState(0)
  const [grantDialogOpen, setGrantDialogOpen] = useState(false)
  const [createUserDialogOpen, setCreateUserDialogOpen] = useState(false)
  const [resetPasswordDialogOpen, setResetPasswordDialogOpen] = useState(false)
  const [selectedUser, setSelectedUser] = useState<KeycloakUser | null>(null)
  const [selectedNamespace, setSelectedNamespace] = useState('')
  const [passwordReset, setPasswordReset] = useState<PasswordReset>({
    password: '',
    temporary: false,
  })
  const [newUser, setNewUser] = useState<UserCreate>({
    username: '',
    email: '',
    firstName: '',
    lastName: '',
    password: '',
    enabled: true,
    emailVerified: true,
    roles: [],
  })
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

  // Fetch Keycloak users
  const { data: keycloakUsers = [], isLoading: usersLoading } = useQuery({
    queryKey: ['keycloak-users'],
    queryFn: () => userService.getKeycloakUsers(),
  })

  // Grant access mutation
  const grantMutation = useMutation({
    mutationFn: (permission: { user_id: string; namespace: string }) =>
      userService.grantNamespaceAccess(permission),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-permissions'] })
      setGrantDialogOpen(false)
      setSelectedUser(null)
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

  // Create user mutation
  const createUserMutation = useMutation({
    mutationFn: (user: UserCreate) => userService.createUser(user),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['keycloak-users'] })
      setCreateUserDialogOpen(false)
      setNewUser({
        username: '',
        email: '',
        firstName: '',
        lastName: '',
        password: '',
        enabled: true,
        emailVerified: true,
        roles: [],
      })
    },
  })

  // Delete user mutation
  const deleteUserMutation = useMutation({
    mutationFn: (userId: string) => userService.deleteUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['keycloak-users'] })
      queryClient.invalidateQueries({ queryKey: ['user-permissions'] })
    },
  })

  // Reset password mutation
  const resetPasswordMutation = useMutation({
    mutationFn: ({ userId, password }: { userId: string; password: PasswordReset }) => 
      userService.resetUserPassword(userId, password),
    onSuccess: () => {
      setResetPasswordDialogOpen(false)
      setSelectedUser(null)
      setPasswordReset({ password: '', temporary: false })
    },
  })

  const handleGrantAccess = () => {
    if (selectedUser && selectedNamespace) {
      grantMutation.mutate({
        user_id: selectedUser.id,
        namespace: selectedNamespace,
      })
    }
  }

  const handleRevokeAccess = (userId: string, namespace: string) => {
    const user = keycloakUsers.find(u => u.id === userId)
    const userDisplay = user ? `${user.username} (${user.email})` : userId
    if (confirm(`Revoke access for ${userDisplay} to namespace ${namespace}?`)) {
      revokeMutation.mutate({ userId, namespace })
    }
  }

  const handleCreateUser = () => {
    createUserMutation.mutate(newUser)
  }

  const handleDeleteUser = (userId: string) => {
    const user = keycloakUsers.find(u => u.id === userId)
    const userDisplay = user ? `${user.username} (${user.email})` : userId
    if (confirm(`Are you sure you want to delete user ${userDisplay}? This action cannot be undone.`)) {
      deleteUserMutation.mutate(userId)
    }
  }

  const handleOpenResetPassword = (user: KeycloakUser) => {
    setSelectedUser(user)
    setPasswordReset({ password: '', temporary: false })
    setResetPasswordDialogOpen(true)
  }

  const handleResetPassword = () => {
    if (selectedUser && passwordReset.password) {
      resetPasswordMutation.mutate({
        userId: selectedUser.id,
        password: passwordReset
      })
    }
  }

  const handleRoleToggle = (role: string) => {
    setNewUser(prev => ({
      ...prev,
      roles: prev.roles?.includes(role)
        ? prev.roles.filter(r => r !== role)
        : [...(prev.roles || []), role]
    }))
  }

  // Helper function to get user display name
  const getUserDisplay = (userId: string) => {
    const user = keycloakUsers.find(u => u.id === userId)
    if (user) {
      const name = user.firstName || user.lastName 
        ? `${user.firstName} ${user.lastName}`.trim()
        : user.username
      return `${name} (${user.email})`
    }
    return userId
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
        {isAdmin && (
          <Stack direction="row" spacing={2}>
            <Button
              variant="outlined"
              startIcon={<PersonAdd />}
              onClick={() => setCreateUserDialogOpen(true)}
            >
              Create User
            </Button>
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => setGrantDialogOpen(true)}
            >
              Grant Access
            </Button>
          </Stack>
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to load user permissions. {!isAdmin && 'You can only view your own permissions.'}
        </Alert>
      )}

      {createUserMutation.isError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to create user: {createUserMutation.error instanceof Error ? createUserMutation.error.message : 'Unknown error'}
        </Alert>
      )}

      {deleteUserMutation.isError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to delete user: {deleteUserMutation.error instanceof Error ? deleteUserMutation.error.message : 'Unknown error'}
        </Alert>
      )}

      {resetPasswordMutation.isError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to reset password: {resetPasswordMutation.error instanceof Error ? resetPasswordMutation.error.message : 'Unknown error'}
        </Alert>
      )}

      {resetPasswordMutation.isSuccess && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Password reset successfully
        </Alert>
      )}

      <Paper sx={{ mb: 2 }}>
        <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
          <Tab label="User Permissions" />
          <Tab label="All Users" />
        </Tabs>
      </Paper>

      {activeTab === 0 && (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>User</TableCell>
                <TableCell>Allowed Namespaces</TableCell>
                <TableCell>Granted By</TableCell>
                <TableCell>Granted At</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading || usersLoading ? (
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
                      <Typography variant="body2">
                        {getUserDisplay(userId)}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" fontFamily="monospace">
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
                            {...(isAdmin ? {
                              onDelete: () => handleRevokeAccess(userId, perm.namespace),
                              deleteIcon: <Delete />
                            } : {})}
                          />
                        ))}
                      </Stack>
                    </TableCell>
                    <TableCell>
                      {userPerms[0]?.granted_by ? (
                        <Box>
                          <Typography variant="body2">
                            {userPerms[0].granted_by_name || userPerms[0].granted_by_email || getUserDisplay(userPerms[0].granted_by)}
                          </Typography>
                          {userPerms[0].granted_by_email && (
                            <Typography variant="caption" color="text.secondary">
                              {userPerms[0].granted_by_email}
                            </Typography>
                          )}
                          <Typography variant="caption" color="text.secondary" fontFamily="monospace" display="block">
                            {userPerms[0].granted_by}
                          </Typography>
                        </Box>
                      ) : (
                        '-'
                      )}
                    </TableCell>
                    <TableCell>
                      {new Date(userPerms[0]?.granted_at).toLocaleString()}
                    </TableCell>
                    <TableCell align="right">
                      {isAdmin && (
                        <IconButton
                          size="small"
                          onClick={() => {
                            const user = keycloakUsers.find(u => u.id === userId)
                            setSelectedUser(user || null)
                            setGrantDialogOpen(true)
                          }}
                          title="Add more namespaces"
                        >
                          <Add />
                        </IconButton>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {activeTab === 1 && (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Username</TableCell>
                <TableCell>Email</TableCell>
                <TableCell>Name</TableCell>
                <TableCell>Roles</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {usersLoading ? (
                <TableRow>
                  <TableCell colSpan={6} align="center">
                    Loading...
                  </TableCell>
                </TableRow>
              ) : keycloakUsers.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center">
                    No users found
                  </TableCell>
                </TableRow>
              ) : (
                keycloakUsers.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>{user.username}</TableCell>
                    <TableCell>{user.email}</TableCell>
                    <TableCell>
                      {user.firstName || user.lastName
                        ? `${user.firstName} ${user.lastName}`.trim()
                        : '-'}
                    </TableCell>
                    <TableCell>
                      <Stack direction="row" spacing={0.5} flexWrap="wrap" gap={0.5}>
                        {user.roles && user.roles.length > 0 ? (
                          user.roles.map((role) => (
                            <Chip
                              key={role}
                              label={role}
                              size="small"
                              color={
                                role === 'admin' ? 'error' : 
                                role === 'operator' ? 'primary' : 
                                'default'
                              }
                            />
                          ))
                        ) : (
                          <Typography variant="caption" color="text.secondary">
                            No roles
                          </Typography>
                        )}
                      </Stack>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={user.enabled ? 'Active' : 'Disabled'}
                        color={user.enabled ? 'success' : 'default'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell align="right">
                      <Stack direction="row" spacing={1} justifyContent="flex-end">
                        <IconButton
                          size="small"
                          color="primary"
                          onClick={() => handleOpenResetPassword(user)}
                          title="Reset password"
                        >
                          <VpnKey />
                        </IconButton>
                        {isAdmin && (
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => handleDeleteUser(user.id)}
                            title="Delete user"
                          >
                            <Delete />
                          </IconButton>
                        )}
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Grant Access Dialog */}
      <Dialog open={grantDialogOpen} onClose={() => setGrantDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Grant Namespace Access</DialogTitle>
        <DialogContent>
          <Stack spacing={3} sx={{ mt: 2 }}>
            <Autocomplete
              options={keycloakUsers}
              value={selectedUser}
              onChange={(_, newValue) => setSelectedUser(newValue)}
              getOptionLabel={(option) => {
                const name = option.firstName || option.lastName
                  ? `${option.firstName} ${option.lastName}`.trim()
                  : option.username
                return `${name} (${option.email})`
              }}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="User"
                  placeholder="Search by name, username, or email"
                  helperText="Select a user to grant namespace access"
                />
              )}
              renderOption={(props, option) => (
                <li {...props}>
                  <Box>
                    <Typography variant="body2">
                      {option.firstName || option.lastName
                        ? `${option.firstName} ${option.lastName}`.trim()
                        : option.username}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {option.email}
                    </Typography>
                  </Box>
                </li>
              )}
              loading={usersLoading}
              disabled={usersLoading}
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
            disabled={!selectedUser || !selectedNamespace || grantMutation.isPending}
          >
            {grantMutation.isPending ? 'Granting...' : 'Grant Access'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Create User Dialog */}
      <Dialog open={createUserDialogOpen} onClose={() => setCreateUserDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New User</DialogTitle>
        <DialogContent>
          <Stack spacing={3} sx={{ mt: 2 }}>
            <TextField
              label="Username"
              value={newUser.username}
              onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
              required
              fullWidth
            />
            <TextField
              label="Email"
              type="email"
              value={newUser.email}
              onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
              required
              fullWidth
            />
            <TextField
              label="First Name"
              value={newUser.firstName}
              onChange={(e) => setNewUser({ ...newUser, firstName: e.target.value })}
              required
              fullWidth
            />
            <TextField
              label="Last Name"
              value={newUser.lastName}
              onChange={(e) => setNewUser({ ...newUser, lastName: e.target.value })}
              required
              fullWidth
            />
            <TextField
              label="Password"
              type="password"
              value={newUser.password}
              onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
              required
              fullWidth
              helperText="Minimum 8 characters"
            />
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Roles
              </Typography>
              <Stack spacing={1}>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={newUser.roles?.includes('admin') || false}
                      onChange={() => handleRoleToggle('admin')}
                    />
                  }
                  label="Admin - Full access to all features and tenants"
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={newUser.roles?.includes('operator') || false}
                      onChange={() => handleRoleToggle('operator')}
                    />
                  }
                  label="Operator - Manage assigned tenants (start/stop/schedule)"
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={newUser.roles?.includes('viewer') || false}
                      onChange={() => handleRoleToggle('viewer')}
                    />
                  }
                  label="Viewer - Read-only access to view information"
                />
              </Stack>
            </Box>
            <FormControlLabel
              control={
                <Checkbox
                  checked={newUser.enabled}
                  onChange={(e) => setNewUser({ ...newUser, enabled: e.target.checked })}
                />
              }
              label="Account Enabled"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateUserDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleCreateUser}
            variant="contained"
            disabled={
              !newUser.username ||
              !newUser.email ||
              !newUser.firstName ||
              !newUser.lastName ||
              !newUser.password ||
              newUser.password.length < 8 ||
              createUserMutation.isPending
            }
          >
            {createUserMutation.isPending ? 'Creating...' : 'Create User'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Reset Password Dialog */}
      <Dialog open={resetPasswordDialogOpen} onClose={() => setResetPasswordDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          Reset Password for {selectedUser?.username}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={3} sx={{ mt: 2 }}>
            <TextField
              label="New Password"
              type="password"
              value={passwordReset.password}
              onChange={(e) => setPasswordReset({ ...passwordReset, password: e.target.value })}
              required
              fullWidth
              helperText="Minimum 8 characters"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={passwordReset.temporary || false}
                  onChange={(e) => setPasswordReset({ ...passwordReset, temporary: e.target.checked })}
                />
              }
              label="Temporary password (user must change on next login)"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResetPasswordDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleResetPassword}
            variant="contained"
            disabled={
              !passwordReset.password ||
              passwordReset.password.length < 8 ||
              resetPasswordMutation.isPending
            }
          >
            {resetPasswordMutation.isPending ? 'Resetting...' : 'Reset Password'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
