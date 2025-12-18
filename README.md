# RotoTV Debug MCP Server

A Model Context Protocol (MCP) server providing debugging and administrative tools for RotoTV backend. This server wraps all CLI functions from the RotoTV backend console as MCP tools that can be used with Claude and other MCP clients.

## Features

The server provides the following MCP tools:

- **generate_uuid** - Generate UUID strings
- **create_session** - Create a new play session from a project
- **create_interaction** - Submit user interaction to a session
- **get_m3u8** - Fetch m3u8 playlist from session API
- **get_session_state** - Fetch session state from API
- **get_project_state** - Fetch project information from API
- **query_cloudwatch_logs** - Query CloudWatch Logs and return CSV results

All secrets (auth tokens, AWS credentials) are read from environment variables for security.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager (recommended)

## Installation

1. Clone or navigate to the repository:
```bash
cd /home/trsjtu17/roto-debug
```

2. Create and activate virtual environment:
```bash
uv venv
source .venv/bin/activate  # on Unix-like systems
# .venv\Scripts\activate  # on Windows
```

3. Install dependencies:
```bash
uv sync
```

4. Install for development:
```bash
uv pip install -e .
```

## Environment Variables Setup

### Authentication Token (Required)

The authentication token **must** be set in an environment variable. All environments (prod, stage, dev) use the same token:

```bash
export ROTO_AUTH_TOKEN="your_auth_token"
```

**Note**: This is required. If not set, tools will return an error asking you to set the ROTO_AUTH_TOKEN environment variable

### AWS Credentials (for CloudWatch Logs)

Required only if you plan to use the `query_cloudwatch_logs` tool:

```bash
export AWS_ACCESS_KEY_ID="your_access_key"
export AWS_SECRET_ACCESS_KEY="your_secret_key"
export AWS_DEFAULT_REGION="your_region"
```

**Note**: The server will validate these credentials only when you use the CloudWatch tool.

**Important**: The MCP server reads directly from environment variables. It does NOT load `.env` files. Set environment variables in your shell or in your MCP client configuration.

## Running the Server

### Method 1: Using the configured script (recommended)
```bash
uv run roto-debug
```

### Method 2: Direct execution
```bash
uv run python src/mcp_server/server.py
```

The server runs in stdio mode by default for MCP communication.

## MCP Tool Usage

Once the server is running and connected to an MCP client (like Claude Desktop), you can use the following tools:

### generate_uuid
```python
# Generate one UUID
generate_uuid()

# Generate multiple UUIDs
generate_uuid(count=5)
```

### create_session
```python
# Create a session (uses env var token)
create_session(env="stage", project_id="PROJECT_UUID")

# Create a session with custom token
create_session(env="prod", project_id="PROJECT_UUID", token="custom_token")
```

### create_interaction
```python
# Submit interaction
create_interaction(
    env="stage",
    session_id="SESSION_UUID",
    node_id="NODE_UUID",
    message="Your input message"
)
```

### get_m3u8
```python
# Get m3u8 playlist
get_m3u8(env="stage", session_id="SESSION_UUID")

# Get m3u8 with play index
get_m3u8(env="stage", session_id="SESSION_UUID", play_index=5)
```

### get_session_state
```python
# Get session state
get_session_state(env="stage", session_id="SESSION_UUID")
```

### get_project_state
```python
# Get project state
get_project_state(env="stage", project_id="PROJECT_UUID")
```

### query_cloudwatch_logs
```python
# Query logs by session ID (last 24 hours)
query_cloudwatch_logs(env="stage", session_id="SESSION_UUID")

# Custom CloudWatch query
query_cloudwatch_logs(
    env="prod",
    query="fields @timestamp, record.message | filter @message like /ERROR/",
    hours=6
)

# Query with time ranges
query_cloudwatch_logs(env="stage", session_id="SESSION_UUID", hours=2)
query_cloudwatch_logs(env="stage", session_id="SESSION_UUID", days=7)
query_cloudwatch_logs(env="stage", session_id="SESSION_UUID", weeks=1)
```

## Configuring MCP Clients

### Claude Desktop

Add to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "roto-debug": {
      "command": "uv",
      "args": [
        "--directory",
        "/home/trsjtu17/roto-debug",
        "run",
        "roto-debug"
      ],
      "env": {
        "ROTO_AUTH_TOKEN": "your_auth_token",
        "AWS_ACCESS_KEY_ID": "your_aws_key",
        "AWS_SECRET_ACCESS_KEY": "your_aws_secret",
        "AWS_DEFAULT_REGION": "your_region"
      }
    }
  }
}
```

### Other MCP Clients

For other MCP clients, use the following command:
```bash
cd /home/trsjtu17/roto-debug && uv run roto-debug
```

Ensure environment variables are set in the client's environment or configuration.

## Development

### Project Structure
```
roto-debug/
├── src/mcp_server/
│   ├── __init__.py
│   ├── server.py      # Main MCP server with all tools
│   └── config.py      # Configuration and environment variable handling
├── pyproject.toml     # Project configuration & dependencies
├── uv.lock           # Locked dependency versions
└── README.md         # This file
```

### Adding New Tools

To add new tools, edit `src/mcp_server/server.py` and add functions decorated with `@mcp.tool()`:

```python
@mcp.tool()
def your_new_tool(param1: str, param2: int) -> str:
    """Description of your tool.

    Args:
        param1: Description
        param2: Description

    Returns:
        Description of return value
    """
    # Implementation
    return "result"
```

### Testing

Use the [MCP Inspector](https://modelcontextprotocol.io/legacy/tools/inspector) to test and debug:

```bash
npx @modelcontextprotocol/inspector uv --directory /home/trsjtu17/roto-debug run roto-debug
```

## Security Notes

- **Never hardcode secrets** - All sensitive data (tokens, AWS credentials) must be in environment variables
- **Default tokens** - The fallback tokens are for development/testing only
- **AWS credentials** - Keep your AWS credentials secure and never commit them to version control
- **Token override** - Each tool accepts an optional `token` parameter to override the environment variable

## Troubleshooting

### AWS Credentials Error
If you see "Missing required AWS credential", ensure you've set:
```bash
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_DEFAULT_REGION="..."
```

### Authentication Errors
If requests fail with 401/403:
1. Check your auth token is correct
2. Set the `ROTO_AUTH_TOKEN` environment variable
3. Or pass the `token` parameter explicitly to override

### Connection Errors
If you can't connect to the API:
1. Verify the environment (prod/stage/dev) is correct
2. Check network connectivity
3. Ensure the backend URLs in `config.py` are up to date

## License

MIT License
