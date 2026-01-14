import { useState, useEffect } from 'react'
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  List,
  Typography,
  Divider,
  IconButton,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Avatar,
  Menu,
  MenuItem,
  Stack,
  Chip,
} from '@mui/material'
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  Storage as StorageIcon,
  Schedule as ScheduleIcon,
  History as HistoryIcon,
  Settings as SettingsIcon,
  AccountCircle,
  People as PeopleIcon,
} from '@mui/icons-material'
import { useNavigate, useLocation } from 'react-router-dom'
import { useKeycloak } from '../contexts/KeycloakContext'

const drawerWidth = 240

const menuItems = [
  { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard' },
  { text: 'Tenants', icon: <StorageIcon />, path: '/tenants' },
  { text: 'Schedules', icon: <ScheduleIcon />, path: '/schedules' },
  { text: 'Audit Logs', icon: <HistoryIcon />, path: '/audit-logs' },
  { text: 'User Management', icon: <PeopleIcon />, path: '/users' },
  { text: 'Settings', icon: <SettingsIcon />, path: '/settings' },
]

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const navigate = useNavigate()
  const location = useLocation()
  const { logout, user, keycloak, authenticated } = useKeycloak()
  
  // Debug logging
  useEffect(() => {
    console.log('=== Layout User Debug ===')
    console.log('Authenticated:', authenticated)
    console.log('User object:', user)
    console.log('Keycloak tokenParsed:', keycloak?.tokenParsed)
    console.log('=====================')
  }, [user, keycloak, authenticated])
  
  // Get user display name
  const getUserDisplay = () => {
    // Debug: show what we have
    console.log('=== getUserDisplay Debug ===')
    console.log('authenticated:', authenticated)
    console.log('keycloak:', keycloak)
    console.log('keycloak?.tokenParsed:', keycloak?.tokenParsed)
    console.log('user:', user)
    
    // Try keycloak token directly first (most reliable)
    if (keycloak?.tokenParsed) {
      const token = keycloak.tokenParsed as any
      console.log('Token contents:', { email: token.email, preferred_username: token.preferred_username, name: token.name })
      if (token.email) {
        console.log('Returning email:', token.email)
        return token.email
      }
      if (token.preferred_username) {
        console.log('Returning preferred_username:', token.preferred_username)
        return token.preferred_username
      }
      if (token.name) {
        console.log('Returning name:', token.name)
        return token.name
      }
    }
    
    // Fallback to user state
    if (user?.email) {
      console.log('Returning user.email:', user.email)
      return user.email
    }
    if (user?.username) {
      console.log('Returning user.username:', user.username)
      return user.username
    }
    if (user?.name) {
      console.log('Returning user.name:', user.name)
      return user.name
    }
    
    console.log('No user info found anywhere, returning fallback')
    // Show if authenticated at least
    return authenticated ? 'Authenticated User' : 'User'
  }

  // Get user full name from token
  const getUserName = (): string | null => {
    if (keycloak?.tokenParsed) {
      const token = keycloak.tokenParsed as any
      // Try full name first
      if (token.name) {
        return token.name
      }
      // Construct from given_name and family_name
      if (token.given_name || token.family_name) {
        return [token.given_name, token.family_name].filter(Boolean).join(' ')
      }
    }
    return null
  }

  // Get user ID from token
  const getUserId = (): string | null => {
    if (keycloak?.tokenParsed) {
      const token = keycloak.tokenParsed as any
      return token.sub || null
    }
    return null
  }

  // Get user roles from token
  const getUserRoles = (): string[] => {
    if (keycloak?.tokenParsed) {
      const token = keycloak.tokenParsed as any
      if (token.realm_access?.roles) {
        // Filter to only show our custom roles
        return token.realm_access.roles.filter((role: string) => 
          ['admin', 'operator', 'viewer'].includes(role)
        )
      }
    }
    return []
  }

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen)
  }

  const handleMenuClick = (path: string) => {
    navigate(path)
    setMobileOpen(false)
  }

  const handleProfileMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget)
  }

  const handleProfileMenuClose = () => {
    setAnchorEl(null)
  }

  const handleLogout = () => {
    logout()
    handleProfileMenuClose()
  }

  const drawer = (
    <div>
      <Toolbar>
        <Typography variant="h6" noWrap component="div">
          Tenant Manager
        </Typography>
      </Toolbar>
      <Divider />
      <List>
        {menuItems.map((item) => (
          <ListItem key={item.text} disablePadding>
            <ListItemButton
              selected={location.pathname === item.path}
              onClick={() => handleMenuClick(item.path)}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </div>
  )

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            Tenant Management System for CVS SaaS Apps
          </Typography>
          <IconButton
            size="large"
            edge="end"
            aria-label="account of current user"
            aria-controls="menu-appbar"
            aria-haspopup="true"
            onClick={handleProfileMenuOpen}
            color="inherit"
          >
            <Avatar sx={{ width: 32, height: 32, bgcolor: 'secondary.main' }}>
              <AccountCircle />
            </Avatar>
          </IconButton>
          <Menu
            id="menu-appbar"
            anchorEl={anchorEl}
            anchorOrigin={{
              vertical: 'top',
              horizontal: 'right',
            }}
            keepMounted
            transformOrigin={{
              vertical: 'top',
              horizontal: 'right',
            }}
            open={Boolean(anchorEl)}
            onClose={handleProfileMenuClose}
            PaperProps={{
              sx: { minWidth: 280 }
            }}
          >
            <MenuItem disabled>
              <Stack spacing={1} sx={{ width: '100%' }}>
                {getUserName() && (
                  <Typography variant="body2" fontWeight="bold">
                    {getUserName()}
                  </Typography>
                )}
                <Typography variant="body2" color="text.secondary">
                  {getUserDisplay()}
                </Typography>
                {getUserId() && (
                  <Typography variant="caption" color="text.secondary" fontFamily="monospace">
                    ID: {getUserId()}
                  </Typography>
                )}
                {getUserRoles().length > 0 && (
                  <Stack direction="row" spacing={0.5} flexWrap="wrap" gap={0.5}>
                    {getUserRoles().map((role) => (
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
                    ))}
                  </Stack>
                )}
              </Stack>
            </MenuItem>
            <Divider />
            <MenuItem onClick={() => { navigate('/settings'); handleProfileMenuClose(); }}>
              Settings
            </MenuItem>
            <MenuItem onClick={handleLogout}>Logout</MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>
      <Box
        component="nav"
        sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true,
          }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          minHeight: '100vh',
          bgcolor: 'background.default',
        }}
      >
        <Toolbar />
        {children}
      </Box>
    </Box>
  )
}
