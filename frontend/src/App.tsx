import { Routes, Route, Navigate } from 'react-router-dom'
import { Box, CircularProgress, Typography } from '@mui/material'
import { useKeycloak } from './contexts/KeycloakContext'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Tenants from './pages/Tenants'
import Schedules from './pages/Schedules'
import AuditLogs from './pages/AuditLogs'
import Settings from './pages/Settings'
import Login from './pages/Login'
import UserManagement from './pages/UserManagement'

function App() {
  const { initialized, authenticated } = useKeycloak()

  // Show loading while Keycloak initializes
  if (!initialized) {
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '100vh',
          gap: 2,
        }}
      >
        <CircularProgress />
        <Typography variant="body2" color="textSecondary">
          Initializing authentication...
        </Typography>
      </Box>
    )
  }

  // Show login page if not authenticated
  if (!authenticated) {
    return <Login />
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/tenants" element={<Tenants />} />
        <Route path="/schedules" element={<Schedules />} />
        <Route path="/audit-logs" element={<AuditLogs />} />
        <Route path="/users" element={<UserManagement />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Layout>
  )
}

export default App
