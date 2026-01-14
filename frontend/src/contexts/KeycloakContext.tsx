import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import Keycloak from 'keycloak-js'
import { setKeycloakToken } from '../utils/tokenStore'

interface KeycloakContextType {
  keycloak: Keycloak | null
  initialized: boolean
  authenticated: boolean
  token: string | null
  login: () => void
  logout: () => void
  user: {
    username?: string
    email?: string
    name?: string
    roles?: string[]
  } | null
}

const KeycloakContext = createContext<KeycloakContextType | undefined>(undefined)

export const useKeycloak = () => {
  const context = useContext(KeycloakContext)
  if (!context) {
    throw new Error('useKeycloak must be used within KeycloakProvider')
  }
  return context
}

interface KeycloakProviderProps {
  children: ReactNode
}

export const KeycloakProvider = ({ children }: KeycloakProviderProps) => {
  const [keycloak, setKeycloak] = useState<Keycloak | null>(null)
  const [initialized, setInitialized] = useState(false)
  const [authenticated, setAuthenticated] = useState(false)
  const [token, setToken] = useState<string | null>(null)
  const [user, setUser] = useState<KeycloakContextType['user']>(null)

  useEffect(() => {
    const initKeycloak = async () => {
      try {
        const keycloakUrl = import.meta.env.VITE_KEYCLOAK_URL
        const realm = import.meta.env.VITE_KEYCLOAK_REALM || 'tenant-management'
        const clientId = import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'tenant-manager-frontend'

        console.log('Initializing Keycloak...', { keycloakUrl, realm, clientId })

        const kc = new Keycloak({
          url: keycloakUrl,
          realm: realm,
          clientId: clientId,
        })

        const auth = await kc.init({
          onLoad: 'check-sso',
          checkLoginIframe: false,
          pkceMethod: 'S256',
        })

        console.log('Keycloak initialized. Authenticated:', auth)

        setKeycloak(kc)
        setAuthenticated(auth)
        setToken(kc.token || null)
        setKeycloakToken(kc.token || null) // Update global token store

        if (auth && kc.tokenParsed) {
          const userInfo = {
            username: kc.tokenParsed.preferred_username,
            email: kc.tokenParsed.email,
            name: kc.tokenParsed.name,
            roles: kc.tokenParsed.realm_access?.roles || [],
          }
          console.log('User info from token:', userInfo)
          setUser(userInfo)
        } else {
          console.log('No user info available - not authenticated or token not parsed')
        }

        // Auto-refresh token
        if (auth) {
          setInterval(() => {
            kc.updateToken(70)
              .then((refreshed) => {
                if (refreshed) {
                  console.log('Token refreshed')
                  setToken(kc.token || null)
                  setKeycloakToken(kc.token || null) // Update global token store
                  
                  // Update user info from refreshed token
                  if (kc.tokenParsed) {
                    setUser({
                      username: kc.tokenParsed.preferred_username,
                      email: kc.tokenParsed.email,
                      name: kc.tokenParsed.name,
                      roles: kc.tokenParsed.realm_access?.roles || [],
                    })
                  }
                }
              })
              .catch(() => {
                console.error('Failed to refresh token')
              })
          }, 60000) // Check every minute
        }

        setInitialized(true)
      } catch (error) {
        console.error('Failed to initialize Keycloak:', error)
        setInitialized(true)
      }
    }

    initKeycloak()
  }, [])

  const login = () => {
    keycloak?.login()
  }

  const logout = () => {
    keycloak?.logout({ redirectUri: window.location.origin + import.meta.env.VITE_BASE_PATH })
  }

  const value: KeycloakContextType = {
    keycloak,
    initialized,
    authenticated,
    token,
    login,
    logout,
    user,
  }

  return <KeycloakContext.Provider value={value}>{children}</KeycloakContext.Provider>
}
