import { useState } from 'react'
import {
  Box,
  Typography,
  Paper,
  Grid,
  TextField,
  Button,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Stack,
  Alert,
} from '@mui/material'
import { Save, VpnKey } from '@mui/icons-material'
import { useMutation } from '@tanstack/react-query'
import { userService, type PasswordReset } from '@/services/userService'

export default function Settings() {
  const [saved, setSaved] = useState(false)
  const [passwordData, setPasswordData] = useState<PasswordReset>({
    password: '',
    temporary: false,
  })
  const [confirmPassword, setConfirmPassword] = useState('')

  // Reset own password mutation
  const resetPasswordMutation = useMutation({
    mutationFn: (password: PasswordReset) => userService.resetOwnPassword(password),
    onSuccess: () => {
      setPasswordData({ password: '', temporary: false })
      setConfirmPassword('')
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    },
  })

  const handleSave = () => {
    console.log('Settings saved')
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
    // TODO: Call API to save settings
  }

  const handleResetPassword = () => {
    if (passwordData.password === confirmPassword && passwordData.password.length >= 8) {
      resetPasswordMutation.mutate(passwordData)
    }
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Settings
      </Typography>

      {saved && (
        <Alert severity="success" sx={{ mb: 3 }}>
          Settings saved successfully!
        </Alert>
      )}

      {resetPasswordMutation.isSuccess && (
        <Alert severity="success" sx={{ mb: 3 }}>
          Password changed successfully!
        </Alert>
      )}

      {resetPasswordMutation.isError && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Failed to change password: {resetPasswordMutation.error instanceof Error ? resetPasswordMutation.error.message : 'Unknown error'}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Security Settings - Password Change */}
        <Grid item xs={12} lg={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Security Settings
            </Typography>
            <Divider sx={{ mb: 3 }} />

            <Stack spacing={3}>
              <Typography variant="subtitle2" color="text.secondary">
                Change Password
              </Typography>
              
              <TextField
                fullWidth
                type="password"
                label="New Password"
                value={passwordData.password}
                onChange={(e) => setPasswordData({ ...passwordData, password: e.target.value })}
                helperText="Minimum 8 characters"
              />

              <TextField
                fullWidth
                type="password"
                label="Confirm Password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                error={confirmPassword.length > 0 && passwordData.password !== confirmPassword}
                helperText={
                  confirmPassword.length > 0 && passwordData.password !== confirmPassword
                    ? "Passwords don't match"
                    : ""
                }
              />

              <Button
                variant="contained"
                startIcon={<VpnKey />}
                onClick={handleResetPassword}
                disabled={
                  !passwordData.password ||
                  passwordData.password.length < 8 ||
                  passwordData.password !== confirmPassword ||
                  resetPasswordMutation.isPending
                }
              >
                {resetPasswordMutation.isPending ? 'Changing Password...' : 'Change Password'}
              </Button>
            </Stack>
          </Paper>
        </Grid>

        {/* General Settings */}
        <Grid item xs={12} lg={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              General Settings
            </Typography>
            <Divider sx={{ mb: 3 }} />

            <Stack spacing={3}>
              <TextField
                fullWidth
                label="API Endpoint"
                defaultValue="http://localhost:8000"
                helperText="Backend API base URL"
              />

              <FormControl fullWidth>
                <InputLabel>Default Replicas on Start</InputLabel>
                <Select defaultValue="1" label="Default Replicas on Start">
                  <MenuItem value="1">1</MenuItem>
                  <MenuItem value="2">2</MenuItem>
                  <MenuItem value="3">3</MenuItem>
                </Select>
              </FormControl>

              <FormControl fullWidth>
                <InputLabel>Refresh Interval</InputLabel>
                <Select defaultValue="30" label="Refresh Interval">
                  <MenuItem value="10">10 seconds</MenuItem>
                  <MenuItem value="30">30 seconds</MenuItem>
                  <MenuItem value="60">1 minute</MenuItem>
                  <MenuItem value="300">5 minutes</MenuItem>
                </Select>
              </FormControl>
            </Stack>
          </Paper>
        </Grid>

        {/* Keycloak Settings */}
        <Grid item xs={12} lg={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Keycloak Settings
            </Typography>
            <Divider sx={{ mb: 3 }} />

            <Stack spacing={3}>
              <TextField
                fullWidth
                label="Keycloak URL"
                defaultValue="http://localhost:8080"
                helperText="Keycloak server URL"
              />

              <TextField
                fullWidth
                label="Realm"
                defaultValue="saas-management"
                helperText="Keycloak realm name"
              />

              <TextField
                fullWidth
                label="Client ID"
                defaultValue="tenant-management-portal"
                helperText="Keycloak client ID"
              />

              <FormControlLabel
                control={<Switch defaultChecked />}
                label="Enable Single Sign-On (SSO)"
              />
            </Stack>
          </Paper>
        </Grid>

        {/* Default Schedule Settings */}
        <Grid item xs={12} lg={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Default Schedule Settings
            </Typography>
            <Divider sx={{ mb: 3 }} />

            <Stack spacing={3}>
              <TextField
                fullWidth
                label="Default Stop Schedule"
                defaultValue="0 18 * * 1-5"
                helperText="Cron expression for default stop time (6 PM weekdays)"
              />

              <TextField
                fullWidth
                label="Default Start Schedule"
                defaultValue="0 8 * * 1-5"
                helperText="Cron expression for default start time (8 AM weekdays)"
              />

              <FormControlLabel
                control={<Switch defaultChecked />}
                label="Auto-create default schedules for new tenants"
              />

              <FormControlLabel
                control={<Switch />}
                label="Stop tenants on weekends"
              />
            </Stack>
          </Paper>
        </Grid>

        {/* Notification Settings */}
        <Grid item xs={12} lg={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Notification Settings
            </Typography>
            <Divider sx={{ mb: 3 }} />

            <Stack spacing={3}>
              <FormControlLabel
                control={<Switch defaultChecked />}
                label="Email notifications"
              />

              <TextField
                fullWidth
                label="Notification Email"
                defaultValue="admin@example.com"
                helperText="Email address for notifications"
                disabled
              />

              <FormControlLabel
                control={<Switch />}
                label="Slack notifications"
              />

              <TextField
                fullWidth
                label="Slack Webhook URL"
                placeholder="https://hooks.slack.com/services/..."
                helperText="Slack webhook URL for notifications"
                disabled
              />
            </Stack>
          </Paper>
        </Grid>

        {/* Kubernetes Settings */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Kubernetes Settings
            </Typography>
            <Divider sx={{ mb: 3 }} />

            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="K8s API Server"
                  defaultValue="https://kubernetes.default.svc"
                  helperText="Kubernetes API server endpoint"
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Authentication Method</InputLabel>
                  <Select defaultValue="serviceaccount" label="Authentication Method">
                    <MenuItem value="serviceaccount">Service Account</MenuItem>
                    <MenuItem value="kubeconfig">Kubeconfig File</MenuItem>
                    <MenuItem value="token">Bearer Token</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Namespace Pattern"
                  defaultValue="tenant-*"
                  helperText="Pattern to match tenant namespaces"
                />
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* Save Button */}
        <Grid item xs={12}>
          <Box display="flex" justifyContent="flex-end">
            <Button variant="contained" size="large" startIcon={<Save />} onClick={handleSave}>
              Save Settings
            </Button>
          </Box>
        </Grid>
      </Grid>
    </Box>
  )
}
