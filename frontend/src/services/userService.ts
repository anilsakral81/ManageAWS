import apiClient from './apiClient';

export interface UserNamespacePermission {
  user_id: string;
  namespace: string;
  enabled: boolean;
  granted_by: string | null;
  granted_at: string;
}

export interface UserNamespaceCreate {
  user_id: string;
  namespace: string;
}

export const userService = {
  /**
   * Grant user access to a namespace
   */
  grantNamespaceAccess: async (permission: UserNamespaceCreate): Promise<UserNamespacePermission> => {
    const response = await apiClient.post('/api/v1/admin/users/namespaces', permission);
    return response.data;
  },

  /**
   * Revoke user access to a namespace
   */
  revokeNamespaceAccess: async (userId: string, namespace: string): Promise<void> => {
    await apiClient.delete(`/api/v1/admin/users/${userId}/namespaces/${namespace}`);
  },

  /**
   * List namespaces accessible to a user
   */
  getUserNamespaces: async (userId: string): Promise<string[]> => {
    const response = await apiClient.get(`/api/v1/admin/users/${userId}/namespaces`);
    return response.data;
  },

  /**
   * List all user-namespace permissions
   */
  getAllPermissions: async (): Promise<UserNamespacePermission[]> => {
    const response = await apiClient.get('/api/v1/admin/users/namespaces');
    return response.data;
  },

  /**
   * List users who have access to a namespace
   */
  getNamespaceUsers: async (namespace: string): Promise<string[]> => {
    const response = await apiClient.get(`/api/v1/admin/namespaces/${namespace}/users`);
    return response.data;
  },
};

export default userService;
