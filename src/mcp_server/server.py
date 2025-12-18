"""
RotoTV Debug MCP Server

Provides debugging and administrative tools for RotoTV backend.
All secrets (auth tokens, AWS credentials) are read from environment variables.
"""
import json
import logging
import time
import uuid
import csv
import os
from datetime import datetime, timedelta, timezone
from io import StringIO
from typing import Optional

import httpx

from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create the MCP server object
mcp = FastMCP(
    host="127.0.0.1", port="8081",
    # `host` and `port` will not work for stdio transport
)

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


@mcp.tool()
def generate_uuid(count: int = 1) -> str:
    """Generate UUID strings.

    Args:
        count: Number of UUIDs to generate (default: 1)

    Returns:
        UUIDs as newline-separated string
    """
    uuids = [str(uuid.uuid4()) for _ in range(max(count, 0))]
    return "\n".join(uuids)


@mcp.tool()
def create_session(env: str, project_id: str, token: Optional[str] = None) -> str:
    """Create a new play session from a project.

    Args:
        env: Environment (prod, stage, dev)
        project_id: Project UUID
        token: Optional auth token (reads from ROTO_AUTH_TOKEN_<ENV> env var if not provided)

    Returns:
        JSON response with session details
    """
    try:
        base_url = get_backend_url(env)
        url = f"{base_url}/api/play/"

        auth_token = token if token else get_auth_token(env)
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = httpx.post(url, json={"project_id": project_id}, headers=headers, timeout=30)
        response.raise_for_status()
        session = response.json()

        result = {
            "success": True,
            "session": session,
            "next_steps": {
                "get_m3u8": f"Use get_m3u8 tool with session_id={session['id']}",
                "get_session_state": f"Use get_session_state tool with session_id={session['id']}"
            }
        }
        return json.dumps(result, indent=2, ensure_ascii=False)

    except ValueError as exc:
        return json.dumps({
            "success": False,
            "error": str(exc)
        }, indent=2)
    except httpx.HTTPStatusError as exc:
        return json.dumps({
            "success": False,
            "error": f"Request failed ({exc.response.status_code})",
            "details": exc.response.text
        }, indent=2)
    except Exception as exc:
        return json.dumps({
            "success": False,
            "error": str(exc)
        }, indent=2)


@mcp.tool()
def create_interaction(
    env: str,
    session_id: str,
    node_id: str,
    message: str,
    token: Optional[str] = None
) -> str:
    """Submit user interaction to a session.

    Args:
        env: Environment (prod, stage, dev)
        session_id: Session UUID
        node_id: Interaction node UUID
        message: User input message
        token: Optional auth token (reads from ROTO_AUTH_TOKEN_<ENV> env var if not provided)

    Returns:
        JSON response with interaction result
    """
    try:
        base_url = get_backend_url(env)
        url = f"{base_url}/api/play/{session_id}/{node_id}/interactions"

        auth_token = token if token else get_auth_token(env)
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = httpx.post(url, json={"message": message}, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()

        return json.dumps({
            "success": True,
            "result": result,
            "next_steps": {
                "get_session_state": f"Use get_session_state tool with session_id={session_id}"
            }
        }, indent=2, ensure_ascii=False)

    except ValueError as exc:
        return json.dumps({
            "success": False,
            "error": str(exc)
        }, indent=2)
    except httpx.HTTPStatusError as exc:
        return json.dumps({
            "success": False,
            "error": f"Request failed ({exc.response.status_code})",
            "details": exc.response.text
        }, indent=2)
    except Exception as exc:
        return json.dumps({
            "success": False,
            "error": str(exc)
        }, indent=2)


@mcp.tool()
def get_m3u8(
    env: str,
    session_id: str,
    play_index: Optional[int] = None,
    token: Optional[str] = None
) -> str:
    """Fetch m3u8 playlist from the session API.

    Args:
        env: Environment (prod, stage, dev)
        session_id: Session UUID
        play_index: Optional play index (x-play-index header)
        token: Optional auth token (reads from ROTO_AUTH_TOKEN_<ENV> env var if not provided)

    Returns:
        M3U8 playlist content
    """
    try:
        base_url = get_backend_url(env)
        url = f"{base_url}/api/play/{session_id}/m3u8"

        auth_token = token if token else get_auth_token(env)
        headers = {"Authorization": f"Bearer {auth_token}"}

        if play_index is not None:
            headers["x-play-index"] = str(play_index)
        response = httpx.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        return response.text

    except ValueError as exc:
        return f"Error: {exc}"
    except httpx.HTTPStatusError as exc:
        return f"Error: Request failed ({exc.response.status_code}): {exc.response.text}"
    except Exception as exc:
        return f"Error: {exc}"


@mcp.tool()
def get_session_state(env: str, session_id: str, token: Optional[str] = None) -> str:
    """Fetch SessionState from the session API.

    Args:
        env: Environment (prod, stage, dev)
        session_id: Session UUID
        token: Optional auth token (reads from ROTO_AUTH_TOKEN_<ENV> env var if not provided)

    Returns:
        JSON session state
    """
    try:
        base_url = get_backend_url(env)
        url = f"{base_url}/api/play/{session_id}/state"

        auth_token = token if token else get_auth_token(env)
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = httpx.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        return json.dumps(response.json(), indent=2, ensure_ascii=False)

    except ValueError as exc:
        return json.dumps({
            "success": False,
            "error": str(exc)
        }, indent=2)
    except httpx.HTTPStatusError as exc:
        return json.dumps({
            "success": False,
            "error": f"Request failed ({exc.response.status_code})",
            "details": exc.response.text
        }, indent=2)
    except Exception as exc:
        return json.dumps({
            "success": False,
            "error": str(exc)
        }, indent=2)


@mcp.tool()
def get_project_state(env: str, project_id: str, token: Optional[str] = None) -> str:
    """Fetch ProjectState from the API.

    Note: Returns basic project info (metadata, edges) but not the full edit-time state
    with all nodes, variables, and tasks.

    Args:
        env: Environment (prod, stage, dev)
        project_id: Project UUID
        token: Optional auth token (reads from ROTO_AUTH_TOKEN_<ENV> env var if not provided)

    Returns:
        JSON project state
    """
    try:
        base_url = get_backend_url(env)
        url = f"{base_url}/api/projects/{project_id}"

        auth_token = token if token else get_auth_token(env)
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = httpx.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        return json.dumps(response.json(), indent=2, ensure_ascii=False)

    except ValueError as exc:
        return json.dumps({
            "success": False,
            "error": str(exc)
        }, indent=2)
    except httpx.HTTPStatusError as exc:
        return json.dumps({
            "success": False,
            "error": f"Request failed ({exc.response.status_code})",
            "details": exc.response.text
        }, indent=2)
    except Exception as exc:
        return json.dumps({
            "success": False,
            "error": str(exc)
        }, indent=2)


@mcp.tool()
def query_cloudwatch_logs(
    env: str,
    query: Optional[str] = None,
    session_id: Optional[str] = None,
    hours: Optional[int] = None,
    days: Optional[int] = None,
    weeks: Optional[int] = None,
    limit: int = 100
) -> str:
    """Query CloudWatch Logs and return results as CSV format.

    Prerequisites:
        AWS credentials must be set in environment variables:
        - AWS_ACCESS_KEY_ID
        - AWS_SECRET_ACCESS_KEY
        - AWS_DEFAULT_REGION

    Args:
        env: Environment (stage or prod)
        query: CloudWatch Logs Insights query string (optional if session_id provided)
        session_id: Session ID to search for (auto-generates query)
        hours: Query logs from last N hours
        days: Query logs from last N days (default: 1 if no time range specified)
        weeks: Query logs from last N weeks
        limit: Max number of results (default: 100)

    Returns:
        CSV formatted log results
    """
    try:
        # Lazy import boto3 to avoid requiring it if not used
        import boto3
    except ImportError:
        return "Error: boto3 not installed. Install with: uv add boto3"

    # Validate AWS credentials
    try:
        credentials = get_aws_credentials()
    except ValueError as e:
        return f"Error: {e}"

    # Temporarily set AWS env vars if not already set
    for key, value in credentials.items():
        if not os.getenv(key):
            os.environ[key] = value

    # Unset AWS_PROFILE to avoid conflicts
    os.environ.pop("AWS_PROFILE", None)
    os.environ.pop("AWS_DEFAULT_PROFILE", None)

    # Determine query string
    if session_id:
        query = (
            f"fields @timestamp, record.message | "
            f"filter @message like /{session_id}/ | "
            f"sort @timestamp desc | "
            f"limit {limit}"
        )
    elif not query:
        return "Error: Must provide either query or session_id"

    # Get log group
    try:
        log_group = get_log_group(env)
    except ValueError as e:
        return f"Error: {e}"

    # Calculate time range
    if hours:
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        time_desc = f"{hours} hour{'s' if hours != 1 else ''}"
    elif days:
        start_time = datetime.now(timezone.utc) - timedelta(days=days)
        time_desc = f"{days} day{'s' if days != 1 else ''}"
    elif weeks:
        start_time = datetime.now(timezone.utc) - timedelta(weeks=weeks)
        time_desc = f"{weeks} week{'s' if weeks != 1 else ''}"
    else:
        start_time = datetime.now(timezone.utc) - timedelta(days=1)
        time_desc = "1 day"

    end_time = datetime.now(timezone.utc)

    # Create CloudWatch Logs client
    try:
        client = boto3.client('logs')
    except Exception as e:
        return f"Error creating AWS client: {e}"

    # Start query
    try:
        response = client.start_query(
            logGroupName=log_group,
            startTime=int(start_time.timestamp()),
            endTime=int(end_time.timestamp()),
            queryString=query,
        )
    except Exception as e:
        return f"Error starting query: {e}"

    query_id = response['queryId']

    # Poll for results (max 60 seconds)
    for _ in range(30):
        time.sleep(2)

        try:
            result = client.get_query_results(queryId=query_id)
        except Exception as e:
            return f"Error getting query results: {e}"

        status = result['status']

        if status == 'Complete':
            # Convert results to CSV
            log_entries = []
            for result_row in result['results']:
                entry = {}
                for field in result_row:
                    # Skip @ptr field
                    if field['field'] != '@ptr':
                        entry[field['field']] = field['value']
                if entry:
                    log_entries.append(entry)

            if not log_entries:
                return f"Query completed successfully but returned no results.\nQuery: {query}\nTime range: Last {time_desc}"

            # Convert to CSV
            output = StringIO()
            all_fields = set()
            for entry in log_entries:
                all_fields.update(entry.keys())
            fields = sorted(all_fields)

            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            writer.writerows(log_entries)

            csv_result = output.getvalue()
            return f"Query completed successfully. Found {len(log_entries)} results.\n\n{csv_result}"

        elif status == 'Failed':
            return "Error: Query failed"

    return f"Error: Query timed out. Query ID: {query_id}"


# This is the main entry point for your server
def main():
    logger.info('Starting roto-debug MCP server')
    mcp.run(transport="stdio")
    # mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()

