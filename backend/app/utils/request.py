"""Request utility functions"""

from fastapi import Request


def get_client_ip(request: Request) -> str:
    """
    Get the real client IP address from the request.
    
    Checks X-Forwarded-For header first (set by ALB/Istio),
    then falls back to direct client connection.
    
    Args:
        request: FastAPI request object
        
    Returns:
        str: Client IP address
    """
    # Check X-Forwarded-For header (set by load balancers/proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs: "client, proxy1, proxy2"
        # The first IP is the original client
        client_ip = forwarded_for.split(",")[0].strip()
        return client_ip
    
    # Check X-Real-IP header (alternative header used by some proxies)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fall back to direct client connection
    if request.client:
        return request.client.host
    
    return "unknown"
