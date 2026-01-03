"""WebSocket terminal endpoint for interactive pod exec"""

import asyncio
import logging
from typing import Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from kubernetes import client
from kubernetes.stream import stream

from app.auth.keycloak import get_current_user_ws
from app.services.k8s_client import get_k8s_client

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws/{namespace}/pods/{pod_name}/shell")
async def pod_shell_websocket(
    websocket: WebSocket,
    namespace: str,
    pod_name: str,
    container: str = Query(None),
):
    """
    Interactive shell via WebSocket
    
    Args:
        websocket: WebSocket connection
        namespace: Kubernetes namespace
        pod_name: Pod name
        container: Container name (optional)
    """
    await websocket.accept()
    
    try:
        # Note: For production, implement proper auth token validation
        # For now, accepting connection (auth bypass is enabled)
        
        k8s_client = get_k8s_client()
        core_v1 = client.CoreV1Api()
        
        # If no container specified, get the first non-istio container
        if not container:
            pod = core_v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            containers = [c.name for c in pod.spec.containers if not c.name.startswith('istio-')]
            if containers:
                container = containers[0]
            elif pod.spec.containers:
                container = pod.spec.containers[0].name
        
        logger.info(f"Starting shell session for pod {pod_name} in namespace {namespace}, container {container}")
        
        # Try sh first (most compatible), then bash as fallback
        resp = None
        shell_attempted = None
        last_error = None
        
        for shell in ['/bin/sh', '/bin/bash']:
            try:
                shell_attempted = shell
                exec_command = [shell]
                
                # Create exec stream with websocket protocol
                resp = stream(
                    core_v1.connect_get_namespaced_pod_exec,
                    pod_name,
                    namespace,
                    container=container,
                    command=exec_command,
                    stderr=True,
                    stdin=True,
                    stdout=True,
                    tty=True,
                    _preload_content=False
                )
                
                # If we got here, connection succeeded
                logger.info(f"Successfully connected to pod {pod_name} using {shell}")
                await websocket.send_text(f"\x1b[32m✓ Connected ({shell})\x1b[0m\r\n\r\n")
                break
                
            except Exception as e:
                last_error = e
                logger.warning(f"Failed to connect with {shell}: {str(e)[:100]}")
                resp = None
                continue
        
        if not resp:
            error_msg = f"Failed to connect with /bin/sh and /bin/bash. Last error: {last_error}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        async def read_from_k8s():
            """Read from Kubernetes and send to WebSocket"""
            try:
                while resp.is_open():
                    resp.update(timeout=0.1)
                    if resp.peek_stdout():
                        data = resp.read_stdout()
                        await websocket.send_text(data)
                    if resp.peek_stderr():
                        data = resp.read_stderr()
                        await websocket.send_text(data)
                    await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"Error reading from k8s: {e}")
                await websocket.send_text(f"\r\nConnection to pod closed: {e}\r\n")
        
        async def write_to_k8s():
            """Read from WebSocket and write to Kubernetes"""
            try:
                while True:
                    data = await websocket.receive_text()
                    if data:
                        resp.write_stdin(data)
                    await asyncio.sleep(0.01)
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected")
            except Exception as e:
                logger.error(f"Error writing to k8s: {e}")
        
        # Run both tasks concurrently
        await asyncio.gather(
            read_from_k8s(),
            write_to_k8s(),
            return_exceptions=True
        )
        
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_text(f"\r\nError: {str(e)}\r\n")
        except:
            pass
    finally:
        try:
            if 'resp' in locals():
                resp.close()
        except:
            pass
        try:
            await websocket.close()
        except:
            pass
