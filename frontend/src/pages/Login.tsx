import { Box, Paper, Typography, Button } from '@mui/material'
import { Login as LoginIcon } from '@mui/icons-material'

export default function Login() {
  const handleLogin = () => {
    console.log('Login with Keycloak')
    // TODO: Redirect to Keycloak login
  }

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        bgcolor: 'background.default',
      }}
    >
      <Paper
        sx={{
          p: 4,
          maxWidth: 400,
          width: '100%',
          textAlign: 'center',
        }}
      >
        <Typography variant="h4" gutterBottom>
          Tenant Management Portal
        </Typography>
        <Typography variant="body1" color="textSecondary" sx={{ mb: 4 }}>
          Please sign in to continue
        </Typography>
        <Button
          variant="contained"
          size="large"
          fullWidth
          startIcon={<LoginIcon />}
          onClick={handleLogin}
        >
          Sign in with Keycloak
        </Button>
        <Typography variant="caption" color="textSecondary" sx={{ mt: 3, display: 'block' }}>
          Manage your AWS Kubernetes tenants
        </Typography>
      </Paper>
    </Box>
  )
}
