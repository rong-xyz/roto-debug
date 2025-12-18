"""
Configuration module for reading secrets and settings from environment variables.
"""
import os
from typing import Dict

# Backend URLs for different environments
BACKENDS: Dict[str, str] = {
    "prod": "https://api.rotopus.ai",
    "stage": "https://api-stage.rotopus.ai",
    "dev": "http://localhost:8000",
}

# CloudWatch log groups for different environments
LOG_GROUPS: Dict[str, str] = {
    "stage": "/ecs/rototv-stage-backend",
    "prod": "/ecs/rototv-prod-backend",
}


def get_auth_token(env: str) -> str:
    """
    Get authentication token from environment variable.

    Reads from ROTO_AUTH_TOKEN environment variable.

    Args:
        env: Environment name (prod, stage, dev) - not used, kept for API compatibility

    Returns:
        Authentication token

    Raises:
        ValueError: If token is not set in environment
    """
    token = os.getenv("ROTO_AUTH_TOKEN")

    if not token:
        raise ValueError(
            "Missing required authentication token. "
            "Please set environment variable ROTO_AUTH_TOKEN"
        )

    return token


def get_aws_credentials() -> Dict[str, str]:
    """
    Get AWS credentials from environment variables.

    Returns:
        Dictionary with AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION

    Raises:
        ValueError: If required credentials are missing
    """
    required = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION"]
    credentials = {}

    for key in required:
        value = os.getenv(key)
        if not value:
            raise ValueError(
                f"Missing required AWS credential: {key}. "
                f"Please set environment variables: {', '.join(required)}"
            )
        credentials[key] = value

    return credentials


def get_backend_url(env: str) -> str:
    """
    Get backend URL for environment.

    Args:
        env: Environment name (prod, stage, dev)

    Returns:
        Backend URL

    Raises:
        ValueError: If environment is invalid
    """
    if env not in BACKENDS:
        raise ValueError(f"Invalid environment: {env}. Must be one of: {', '.join(BACKENDS.keys())}")
    return BACKENDS[env]


def get_log_group(env: str) -> str:
    """
    Get CloudWatch log group for environment.

    Args:
        env: Environment name (stage, prod)

    Returns:
        Log group name

    Raises:
        ValueError: If environment is invalid
    """
    if env not in LOG_GROUPS:
        raise ValueError(f"Invalid environment: {env}. Must be one of: {', '.join(LOG_GROUPS.keys())}")
    return LOG_GROUPS[env]
