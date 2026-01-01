"""Application configuration management"""

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Kubernetes Tenant Management Portal"
    app_env: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # API
    api_prefix: str = "/api/v1"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/tenant_management"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Keycloak
    keycloak_url: str = "https://keycloak.example.com"
    keycloak_realm: str = "saas-management"
    keycloak_client_id: str = "tenant-management-portal"
    keycloak_client_secret: str = ""
    keycloak_admin_username: str = ""
    keycloak_admin_password: str = ""

    # JWT
    jwt_algorithm: str = "RS256"
    jwt_audience: str = "tenant-management-portal"

    # Kubernetes
    kubeconfig_path: str = ""
    in_cluster: bool = False

    # Scheduler
    scheduler_enabled: bool = True
    scheduler_timezone: str = "UTC"
    default_stop_schedule: str = "0 18 * * 1-5"  # 6 PM Mon-Fri
    default_start_schedule: str = "0 8 * * 1-5"  # 8 AM Mon-Fri

    # AWS
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090

    # Audit Logging
    audit_log_retention_days: int = 90

    # Rate Limiting
    rate_limit_per_minute: int = 60

    @field_validator("cors_origins")
    @classmethod
    def parse_cors_origins(cls, v: str) -> List[str]:
        """Parse comma-separated CORS origins"""
        return [origin.strip() for origin in v.split(",")]

    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.app_env == "development"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
