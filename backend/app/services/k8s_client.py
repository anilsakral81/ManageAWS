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
        self._networking_v1 = None
        self._custom_objects = None
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
            self._networking_v1 = client.NetworkingV1Api()
            self._custom_objects = client.CustomObjectsApi()
            
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
            # Get current deployment
            deployment = self._apps_v1.read_namespaced_deployment(name=name, namespace=namespace)
            current_replicas = deployment.spec.replicas
            
            # If scaling to 0, store current replica count in annotation
            if replicas == 0 and current_replicas > 0:
                if not deployment.metadata.annotations:
                    deployment.metadata.annotations = {}
                deployment.metadata.annotations['tenant-management/original-replicas'] = str(current_replicas)
                self._apps_v1.patch_namespaced_deployment(name=name, namespace=namespace, body=deployment)
            
            # If scaling up from 0, check for stored replica count
            if replicas > 0 and current_replicas == 0:
                if deployment.metadata.annotations and 'tenant-management/original-replicas' in deployment.metadata.annotations:
                    stored_replicas = int(deployment.metadata.annotations['tenant-management/original-replicas'])
                    replicas = stored_replicas
            
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
    
    async def scale_statefulset(
        self,
        name: str,
        namespace: str,
        replicas: int
    ) -> Dict:
        """
        Scale statefulset to specified replica count
        
        Args:
            name: StatefulSet name
            namespace: Namespace name
            replicas: Target replica count
            
        Returns:
            Dict: Updated statefulset information
        """
        try:
            # Get current statefulset
            statefulset = self._apps_v1.read_namespaced_stateful_set(name=name, namespace=namespace)
            current_replicas = statefulset.spec.replicas
            
            # If scaling to 0, store current replica count in annotation
            if replicas == 0 and current_replicas > 0:
                if not statefulset.metadata.annotations:
                    statefulset.metadata.annotations = {}
                statefulset.metadata.annotations['tenant-management/original-replicas'] = str(current_replicas)
                self._apps_v1.patch_namespaced_stateful_set(name=name, namespace=namespace, body=statefulset)
            
            # If scaling up from 0, check for stored replica count
            if replicas > 0 and current_replicas == 0:
                if statefulset.metadata.annotations and 'tenant-management/original-replicas' in statefulset.metadata.annotations:
                    stored_replicas = int(statefulset.metadata.annotations['tenant-management/original-replicas'])
                    replicas = stored_replicas
            
            # Create scale object
            scale = client.V1Scale(
                spec=client.V1ScaleSpec(replicas=replicas)
            )
            
            # Patch the statefulset scale
            response = self._apps_v1.patch_namespaced_stateful_set_scale(
                name=name,
                namespace=namespace,
                body=scale
            )
            
            logger.info(
                f"Scaled statefulset {name} in namespace {namespace} to {replicas} replicas"
            )
            
            return {
                "name": response.metadata.name,
                "namespace": response.metadata.namespace,
                "replicas": response.spec.replicas,
                "status_replicas": response.status.replicas,
            }
            
        except ApiException as e:
            logger.error(f"Failed to scale statefulset {name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error scaling statefulset {name}: {e}")
            raise
    
    async def scale_daemonset(self, name: str, namespace: str, stop: bool = False) -> Dict:
        """
        'Scale' a DaemonSet by manipulating node selectors
        
        Args:
            name: DaemonSet name
            namespace: Namespace name
            stop: True to stop (set impossible selector), False to start (restore selector)
            
        Returns:
            Dict: DaemonSet information
        """
        try:
            # Get current DaemonSet
            daemonset = self._apps_v1.read_namespaced_daemon_set(
                name=name,
                namespace=namespace
            )
            
            if not daemonset.metadata.annotations:
                daemonset.metadata.annotations = {}
            
            if stop:
                # Store original node selector if it exists
                if daemonset.spec.template.spec.node_selector:
                    import json
                    daemonset.metadata.annotations['tenant-management/original-node-selector'] = json.dumps(
                        daemonset.spec.template.spec.node_selector
                    )
                else:
                    daemonset.metadata.annotations['tenant-management/original-node-selector'] = '{}'
                
                # Set impossible node selector to prevent scheduling
                daemonset.spec.template.spec.node_selector = {
                    'tenant-management/stopped': 'true'  # No nodes should have this label
                }
                logger.info(f"Stopping DaemonSet {name} in namespace {namespace}")
            else:
                # Restore original node selector
                if 'tenant-management/original-node-selector' in daemonset.metadata.annotations:
                    import json
                    original_selector = json.loads(
                        daemonset.metadata.annotations['tenant-management/original-node-selector']
                    )
                    if original_selector:
                        daemonset.spec.template.spec.node_selector = original_selector
                    else:
                        daemonset.spec.template.spec.node_selector = None
                    # Clean up annotation
                    del daemonset.metadata.annotations['tenant-management/original-node-selector']
                else:
                    # If no stored selector, just remove the stop selector
                    daemonset.spec.template.spec.node_selector = None
                logger.info(f"Starting DaemonSet {name} in namespace {namespace}")
            
            # Update the DaemonSet
            response = self._apps_v1.patch_namespaced_daemon_set(
                name=name,
                namespace=namespace,
                body=daemonset
            )
            
            return {
                "name": response.metadata.name,
                "namespace": response.metadata.namespace,
                "desired_number_scheduled": response.status.desired_number_scheduled or 0,
                "current_number_scheduled": response.status.current_number_scheduled or 0,
                "number_ready": response.status.number_ready or 0,
            }
            
        except ApiException as e:
            logger.error(f"Failed to scale daemonset {name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error scaling daemonset {name}: {e}")
            raise
    
    async def list_namespaces(self, exclude_system: bool = True) -> list[str]:
        """
        List all namespaces in the cluster
        
        Args:
            exclude_system: Whether to exclude system namespaces
        
        Returns:
            list[str]: List of namespace names
        """
        # System namespaces to exclude
        system_namespaces = {
            'kube-system',
            'kube-public',
            'kube-node-lease',
            'istio-system',
            'default',
            'tenant-management',  # This application's namespace
        }
        
        try:
            namespaces = self._core_v1.list_namespace()
            all_namespaces = [ns.metadata.name for ns in namespaces.items]
            
            if exclude_system:
                return [ns for ns in all_namespaces if ns not in system_namespaces]
            
            return all_namespaces
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

    async def list_namespace_deployments(self, namespace: str) -> list[Dict]:
        """
        List all deployments and statefulsets in a namespace
        
        Args:
            namespace: Namespace name
            
        Returns:
            list[Dict]: List of deployment/statefulset information
        """
        resources = []
        
        try:
            # Get Deployments
            deployments = self._apps_v1.list_namespaced_deployment(namespace=namespace)
            for d in deployments.items:
                resources.append({
                    "name": d.metadata.name,
                    "namespace": d.metadata.namespace,
                    "type": "Deployment",
                    "replicas": d.spec.replicas,
                    "available_replicas": d.status.available_replicas or 0,
                    "ready_replicas": d.status.ready_replicas or 0,
                })
            
            # Get StatefulSets
            statefulsets = self._apps_v1.list_namespaced_stateful_set(namespace=namespace)
            for s in statefulsets.items:
                resources.append({
                    "name": s.metadata.name,
                    "namespace": s.metadata.namespace,
                    "type": "StatefulSet",
                    "replicas": s.spec.replicas,
                    "available_replicas": s.status.available_replicas or 0,
                    "ready_replicas": s.status.ready_replicas or 0,
                })
            
            # Get DaemonSets
            daemonsets = self._apps_v1.list_namespaced_daemon_set(namespace=namespace)
            for ds in daemonsets.items:
                # Check if DaemonSet is stopped (has the stop node selector)
                is_stopped = False
                if ds.spec.template.spec.node_selector:
                    is_stopped = ds.spec.template.spec.node_selector.get('tenant-management/stopped') == 'true'
                
                resources.append({
                    "name": ds.metadata.name,
                    "namespace": ds.metadata.namespace,
                    "type": "DaemonSet",
                    "replicas": ds.status.desired_number_scheduled or 0,
                    "available_replicas": ds.status.number_available or 0,
                    "ready_replicas": ds.status.number_ready or 0,
                    "is_stopped": is_stopped,
                })
            
            return resources
        except ApiException as e:
            if e.status == 404:
                logger.warning(f"Namespace {namespace} not found")
                return []
            logger.error(f"Failed to list deployments in namespace {namespace}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error listing deployments: {e}")
            raise

    async def scale_namespace(self, namespace: str, replicas: int) -> Dict:
        """
        Scale all deployments and statefulsets in a namespace
        
        Args:
            namespace: Namespace name
            replicas: Target replica count (0=stop, >0=start)
            
        Returns:
            Dict: Summary of scaled resources
        """
        try:
            resources = await self.list_namespace_deployments(namespace)
            
            results = []
            for resource in resources:
                try:
                    if resource["type"] == "Deployment":
                        result = await self.scale_deployment(
                            name=resource["name"],
                            namespace=namespace,
                            replicas=replicas
                        )
                    elif resource["type"] == "StatefulSet":
                        result = await self.scale_statefulset(
                            name=resource["name"],
                            namespace=namespace,
                            replicas=replicas
                        )
                    elif resource["type"] == "DaemonSet":
                        result = await self.scale_daemonset(
                            name=resource["name"],
                            namespace=namespace,
                            stop=(replicas == 0)
                        )
                    else:
                        continue
                    
                    results.append({
                        "resource": resource["name"],
                        "type": resource["type"],
                        "success": True,
                        "replicas": replicas if resource["type"] != "DaemonSet" else "N/A"
                    })
                except Exception as e:
                    logger.error(f"Failed to scale {resource['type']} {resource['name']}: {e}")
                    results.append({
                        "resource": resource["name"],
                        "type": resource["type"],
                        "success": False,
                        "error": str(e)
                    })
            
            return {
                "namespace": namespace,
                "target_replicas": replicas,
                "total_resources": len(resources),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Failed to scale namespace {namespace}: {e}")
            raise

    async def list_namespace_virtualservices(self, namespace: str) -> list[Dict[str, str]]:
        """
        List all VirtualService hosts in a namespace
        
        Args:
            namespace: Namespace name
            
        Returns:
            list[Dict]: List of VirtualService information with name, hosts, and gateway
        """
        try:
            # Get VirtualServices from Istio CRD
            virtualservices = self._custom_objects.list_namespaced_custom_object(
                group="networking.istio.io",
                version="v1beta1",
                namespace=namespace,
                plural="virtualservices"
            )
            
            vs_info = []
            
            for vs in virtualservices.get('items', []):
                vs_name = vs.get('metadata', {}).get('name', 'unknown')
                spec = vs.get('spec', {})
                hosts = spec.get('hosts', [])
                gateways = spec.get('gateways', [])
                
                if hosts:
                    for host in hosts:
                        vs_info.append({
                            'name': vs_name,
                            'host': host,
                            'gateways': ', '.join(gateways) if gateways else 'N/A'
                        })
            
            return vs_info
        except ApiException as e:
            if e.status == 404:
                logger.warning(f"No VirtualServices found in namespace {namespace}")
                return []
            logger.error(f"Failed to list VirtualServices in namespace {namespace}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing VirtualServices: {e}")
            return []

    async def list_namespace_pods(self, namespace: str) -> list[Dict]:
        """
        List all pods in a namespace
        
        Args:
            namespace: Namespace name
            
        Returns:
            list[Dict]: List of pod information
        """
        try:
            pods = self._core_v1.list_namespaced_pod(namespace=namespace)
            
            result = []
            for pod in pods.items:
                # Get container statuses
                containers = []
                for i, container_spec in enumerate(pod.spec.containers):
                    container_status = None
                    if pod.status.container_statuses:
                        for cs in pod.status.container_statuses:
                            if cs.name == container_spec.name:
                                container_status = cs
                                break
                    
                    containers.append({
                        "name": container_spec.name,
                        "image": container_spec.image,
                        "ready": container_status.ready if container_status else False,
                        "state": self._get_container_state(container_status) if container_status else "Unknown",
                        "restarts": container_status.restart_count if container_status else 0,
                    })
                
                ready_count = sum(1 for c in containers if c["ready"])
                total_count = len(containers)
                
                result.append({
                    "name": pod.metadata.name,
                    "status": pod.status.phase,
                    "ready_containers": ready_count,
                    "total_containers": total_count,
                    "containers": containers,
                    "restarts": sum(c["restarts"] for c in containers),
                    "node": pod.spec.node_name,
                    "created_at": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None,
                })
            
            return result
        except ApiException as e:
            if e.status == 404:
                logger.warning(f"Namespace {namespace} not found")
                return []
            logger.error(f"Failed to list pods in namespace {namespace}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing pods: {e}")
            return []
    
    def _get_container_state(self, container_status) -> str:
        """Get human-readable container state"""
        if container_status.state.running:
            return "Running"
        elif container_status.state.waiting:
            return f"Waiting: {container_status.state.waiting.reason or 'Unknown'}"
        elif container_status.state.terminated:
            return f"Terminated: {container_status.state.terminated.reason or 'Unknown'}"
        return "Unknown"
    
    async def get_pod_logs(
        self,
        pod_name: str,
        namespace: str,
        container: Optional[str] = None,
        tail_lines: int = 100
    ) -> str:
        """
        Get logs from a pod container
        
        Args:
            pod_name: Pod name
            namespace: Namespace name
            container: Container name (optional, uses first non-sidecar container if not specified)
            tail_lines: Number of lines to retrieve from the end
            
        Returns:
            str: Pod logs
        """
        try:
            # If no container specified, get the first non-istio container
            if not container:
                pod = self._core_v1.read_namespaced_pod(name=pod_name, namespace=namespace)
                containers = [c.name for c in pod.spec.containers if not c.name.startswith('istio-')]
                if containers:
                    container = containers[0]
                elif pod.spec.containers:
                    container = pod.spec.containers[0].name
            
            logs = self._core_v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                container=container,
                tail_lines=tail_lines
            )
            return logs if logs else "No logs available"
        except ApiException as e:
            logger.error(f"Failed to get logs for pod {pod_name}: {e}")
            if e.status == 400:
                return f"Error: {e.reason}"
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting pod logs: {e}")
            raise
    
    async def list_pod_containers(
        self,
        pod_name: str,
        namespace: str
    ) -> list[Dict]:
        """
        List containers in a pod
        
        Args:
            pod_name: Pod name
            namespace: Namespace name
            
        Returns:
            list: Container information
        """
        try:
            pod = self._core_v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            
            containers = []
            for container in pod.spec.containers:
                container_status = None
                if pod.status.container_statuses:
                    container_status = next(
                        (cs for cs in pod.status.container_statuses if cs.name == container.name),
                        None
                    )
                
                containers.append({
                    "name": container.name,
                    "image": container.image,
                    "ready": container_status.ready if container_status else False,
                    "restart_count": container_status.restart_count if container_status else 0,
                    "state": self._get_container_state(container_status) if container_status else "Unknown"
                })
            
            return containers
        except ApiException as e:
            logger.error(f"Failed to list containers for pod {pod_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error listing containers: {e}")
            raise
    
    def _get_container_state(self, container_status) -> str:
        """Get container state from status"""
        if container_status.state.running:
            return "Running"
        elif container_status.state.waiting:
            return f"Waiting: {container_status.state.waiting.reason}"
        elif container_status.state.terminated:
            return f"Terminated: {container_status.state.terminated.reason}"
        return "Unknown"
    
    async def exec_pod_command(
        self,
        pod_name: str,
        namespace: str,
        command: list[str],
        container: Optional[str] = None
    ) -> Dict:
        """
        Execute a command in a pod container
        
        Args:
            pod_name: Pod name
            namespace: Namespace name
            command: Command to execute (as list)
            container: Container name (optional, uses first non-sidecar container if not specified)
            
        Returns:
            Dict: Command output and errors
        """
        try:
            from kubernetes.stream import stream
            
            # If no container specified, get the first non-istio container
            if not container:
                pod = self._core_v1.read_namespaced_pod(name=pod_name, namespace=namespace)
                containers = [c.name for c in pod.spec.containers if not c.name.startswith('istio-')]
                if containers:
                    container = containers[0]
                elif pod.spec.containers:
                    container = pod.spec.containers[0].name
            
            resp = stream(
                self._core_v1.connect_get_namespaced_pod_exec,
                pod_name,
                namespace,
                container=container,
                command=command,
                stderr=True,
                stdin=False,
                stdout=True,
                tty=False
            )
            
            return {
                "output": resp,
                "pod": pod_name,
                "container": container,
                "command": " ".join(command)
            }
        except ApiException as e:
            logger.error(f"Failed to exec command in pod {pod_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error executing command: {e}")
            raise


@lru_cache()
def get_k8s_client() -> KubernetesClient:
    """
    Get singleton Kubernetes client instance
    
    Returns:
        KubernetesClient: Kubernetes client
    """
    return KubernetesClient()
