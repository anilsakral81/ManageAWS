"""Kubernetes client for cluster operations"""

import logging
from typing import Dict, Optional
from functools import lru_cache

from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

from app.config import settings

logger = logging.getLogger(__name__)


class KubernetesClient:
    """Kubernetes client wrapper for deployment operations"""
    
    def __init__(self):
        """Initialize Kubernetes client"""
        self._apps_v1 = None
        self._core_v1 = None
        self._load_config()
    
    def _load_config(self):
        """Load Kubernetes configuration"""
        try:
            if settings.in_cluster:
                # Load in-cluster configuration
                config.load_incluster_config()
                logger.info("Loaded in-cluster Kubernetes configuration")
            elif settings.kubeconfig_path:
                # Load from specific kubeconfig file
                config.load_kube_config(config_file=settings.kubeconfig_path)
                logger.info(f"Loaded Kubernetes configuration from {settings.kubeconfig_path}")
            else:
                # Load from default kubeconfig location
                config.load_kube_config()
                logger.info("Loaded Kubernetes configuration from default location")
            
            self._apps_v1 = client.AppsV1Api()
            self._core_v1 = client.CoreV1Api()
            
        except Exception as e:
            logger.error(f"Failed to load Kubernetes configuration: {e}")
            raise
    
    async def get_deployment(self, name: str, namespace: str) -> Optional[Dict]:
        """
        Get deployment information
        
        Args:
            name: Deployment name
            namespace: Namespace name
            
        Returns:
            Dict: Deployment information or None if not found
        """
        try:
            deployment = self._apps_v1.read_namespaced_deployment(
                name=name,
                namespace=namespace
            )
            
            return {
                "name": deployment.metadata.name,
                "namespace": deployment.metadata.namespace,
                "replicas": deployment.spec.replicas,
                "available_replicas": deployment.status.available_replicas or 0,
                "ready_replicas": deployment.status.ready_replicas or 0,
                "updated_replicas": deployment.status.updated_replicas or 0,
                "conditions": [
                    {
                        "type": c.type,
                        "status": c.status,
                        "reason": c.reason,
                        "message": c.message,
                    }
                    for c in (deployment.status.conditions or [])
                ],
            }
            
        except ApiException as e:
            if e.status == 404:
                logger.warning(f"Deployment {name} not found in namespace {namespace}")
                return None
            logger.error(f"Failed to get deployment {name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting deployment {name}: {e}")
            raise
    
    async def scale_deployment(
        self,
        name: str,
        namespace: str,
        replicas: int
    ) -> Dict:
        """
        Scale deployment to specified replica count
        
        Args:
            name: Deployment name
            namespace: Namespace name
            replicas: Target replica count
            
        Returns:
            Dict: Updated deployment information
        """
        try:
            # Create scale object
            scale = client.V1Scale(
                spec=client.V1ScaleSpec(replicas=replicas)
            )
            
            # Patch the deployment scale
            response = self._apps_v1.patch_namespaced_deployment_scale(
                name=name,
                namespace=namespace,
                body=scale
            )
            
            logger.info(
                f"Scaled deployment {name} in namespace {namespace} to {replicas} replicas"
            )
            
            return {
                "name": response.metadata.name,
                "namespace": response.metadata.namespace,
                "replicas": response.spec.replicas,
                "status_replicas": response.status.replicas,
            }
            
        except ApiException as e:
            logger.error(f"Failed to scale deployment {name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error scaling deployment {name}: {e}")
            raise
    
    async def list_namespaces(self) -> list[str]:
        """
        List all namespaces in the cluster
        
        Returns:
            list[str]: List of namespace names
        """
        try:
            namespaces = self._core_v1.list_namespace()
            return [ns.metadata.name for ns in namespaces.items]
        except Exception as e:
            logger.error(f"Failed to list namespaces: {e}")
            raise
    
    async def namespace_exists(self, namespace: str) -> bool:
        """
        Check if namespace exists
        
        Args:
            namespace: Namespace name
            
        Returns:
            bool: True if namespace exists
        """
        try:
            self._core_v1.read_namespace(name=namespace)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            raise
    
    async def deployment_exists(self, name: str, namespace: str) -> bool:
        """
        Check if deployment exists
        
        Args:
            name: Deployment name
            namespace: Namespace name
            
        Returns:
            bool: True if deployment exists
        """
        deployment = await self.get_deployment(name, namespace)
        return deployment is not None


@lru_cache()
def get_k8s_client() -> KubernetesClient:
    """
    Get singleton Kubernetes client instance
    
    Returns:
        KubernetesClient: Kubernetes client
    """
    return KubernetesClient()
