import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Tenants from './pages/Tenants'
import Schedules from './pages/Schedules'
import AuditLogs from './pages/AuditLogs'
import Settings from './pages/Settings'
import Login from './pages/Login'

function App() {
  // TODO: Integrate Keycloak authentication
  const isAuthenticated = true // Dummy value for now

  if (!isAuthenticated) {
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
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Layout>
  )
}

export default App
