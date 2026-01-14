// Global Keycloak token accessor
// This allows apiClient to access the token without React context

let keycloakToken: string | null = null

export const setKeycloakToken = (token: string | null) => {
  keycloakToken = token
}

export const getKeycloakToken = (): string | null => {
  return keycloakToken
}
