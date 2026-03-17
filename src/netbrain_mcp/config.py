# Description: Configuration for the NetBrain MCP server.
# Description: Loads settings from environment variables or .env file.
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class NetBrainSettings(BaseSettings):
    """NetBrain connection settings loaded from environment or .env file."""

    model_config = SettingsConfigDict(env_prefix="NETBRAIN_", env_file=".env")

    url: str
    username: str
    password: str
    domain: str
    tenant: str = ""
    auth_timeout: int = 30
    poll_interval: float = 2.0
    poll_timeout: float = 30.0


def get_settings() -> NetBrainSettings:
    """Load and return NetBrain settings."""
    return NetBrainSettings()  # type: ignore[call-arg]
