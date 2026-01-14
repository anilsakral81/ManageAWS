import { apiClient } from './apiClient';

export interface UserNamespacePermission {
  user_id: string;
  namespace: string;
  enabled: boolean;
  granted_by: string | null;
  granted_at: string;
  granted_by_email?: string | null;
  granted_by_name?: string | null;
}

export interface UserNamespaceCreate {
  user_id: string;
  namespace: string;
}

export interface KeycloakUser {
  id: string;
  username: string;
  email: string;
  firstName: string;
  lastName: string;
  enabled: boolean;
  roles?: string[];
}

export interface UserCreate {
  username: string;
  email: string;
  firstName: string;
  lastName: string;
  password: string;
  enabled?: boolean;
  emailVerified?: boolean;
  roles?: string[];
}

export interface PasswordReset {
  password: string;
  temporary?: boolean;
}

export const userService = {
  /**
   * Fetch all users from Keycloak
   */
  getKeycloakUsers: async (): Promise<KeycloakUser[]> => {
    return await apiClient.get('/keycloak/users');
  },

  /**
   * Create a new user in Keycloak
   */
  createUser: async (user: UserCreate): Promise<KeycloakUser> => {
    return await apiClient.post('/keycloak/users', user);
  },

  /**
   * Delete a user from Keycloak
   */
  deleteUser: async (userId: string): Promise<void> => {
    await apiClient.delete(`/keycloak/users/${userId}`);
  },

  /**
   * Reset user password (admin only)
   */
  resetUserPassword: async (userId: string, passwordReset: PasswordReset): Promise<void> => {
    await apiClient.put(`/keycloak/users/${userId}/reset-password`, passwordReset);
  },

  /**
   * Reset own password
   */
  resetOwnPassword: async (passwordReset: PasswordReset): Promise<void> => {
    await apiClient.put('/profile/reset-password', passwordReset);
  },

  /**
   * Grant user access to a namespace
   */
  grantNamespaceAccess: async (permission: UserNamespaceCreate): Promise<UserNamespacePermission> => {
    return await apiClient.post('/users/namespaces', permission);
  },

  /**
   * Revoke user access to a namespace
   */
  revokeNamespaceAccess: async (userId: string, namespace: string): Promise<void> => {
    await apiClient.delete(`/users/${userId}/namespaces/${namespace}`);
  },

  /**
   * List namespaces accessible to a user
   */
  getUserNamespaces: async (userId: string): Promise<string[]> => {
    return await apiClient.get(`/users/${userId}/namespaces`);
  },

  /**
   * List all user-namespace permissions
   */
  getAllPermissions: async (): Promise<UserNamespacePermission[]> => {
    return await apiClient.get('/users/namespaces');
  },

  /**
   * List users who have access to a namespace
   */
  getNamespaceUsers: async (namespace: string): Promise<string[]> => {
    return await apiClient.get(`/namespaces/${namespace}/users`);
  },
};

export default userService;
