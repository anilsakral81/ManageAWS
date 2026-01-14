import { useEffect } from 'react'
import { Box, CircularProgress, Typography } from '@mui/material'
import { useKeycloak } from '../contexts/KeycloakContext'

export default function Login() {
  const { login } = useKeycloak()

  // Automatically redirect to Keycloak login when component mounts
  useEffect(() => {
    login()
  }, [login])

  // Show loading indicator while redirecting to Keycloak
  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        bgcolor: '#f5f5f5',
      }}
    >
      <Box
        sx={{
          textAlign: 'center',
          p: 4,
          bgcolor: 'white',
          borderRadius: 2,
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          minWidth: 300,
        }}
      >
        <Typography variant="h4" gutterBottom sx={{ fontWeight: 600, color: '#1976d2' }}>
          Tenant Management
        </Typography>
        <Typography variant="body2" color="textSecondary" sx={{ mb: 3 }}>
          Redirecting to authentication...
        </Typography>
        <CircularProgress />
      </Box>
    </Box>
  )
}
