# NetBrain MCP Server

MCP server wrapping the NetBrain REST API (R11.1b) for network troubleshooting via natural language.

## Tools

| # | Tool | Category | Description |
|---|------|----------|-------------|
| 1 | `get_devices` | Inventory | List devices with optional type filter and pagination |
| 2 | `get_device_attributes` | Inventory | Full attribute set for a specific device |
| 3 | `get_device_config` | Inventory | Device configuration from the data engine |
| 4 | `get_neighbors` | Topology | Adjacent devices by topology type (L2/L3) |
| 5 | `calculate_path` | Path | A-to-B path calculation with gateway resolution and polling |
| 6 | `trigger_diagnosis` | Diagnosis | Fire-and-forget diagnosis trigger via `/Triggers/Run` |
| 7 | `get_events` | Events | Events from the NetBrain event console |
| 8 | `get_change_analysis` | Change | Config change analysis (Phase 2 -- stub) |
| 9 | `search_devices` | Inventory | Case-insensitive hostname search |

Auth (login, logout, domain selection) is handled transparently by the client. No auth tools are exposed.

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/ryanmat/netbrain-mcp.git
cd netbrain-mcp
uv sync
cp .env.example .env
# Edit .env with your NetBrain credentials
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NETBRAIN_URL` | Yes | Base URL of the NetBrain instance |
| `NETBRAIN_USERNAME` | Yes | API username |
| `NETBRAIN_PASSWORD` | Yes | API password |
| `NETBRAIN_DOMAIN` | Yes | NetBrain domain ID |
| `NETBRAIN_TENANT` | No | Tenant ID (for multi-tenant deployments) |
| `NETBRAIN_AUTH_TIMEOUT` | No | Auth request timeout in seconds (default: 30) |
| `NETBRAIN_POLL_INTERVAL` | No | Path calculation poll interval in seconds (default: 2.0) |
| `NETBRAIN_POLL_TIMEOUT` | No | Path calculation poll timeout in seconds (default: 30.0) |

## Running

```bash
uv run netbrain-mcp
```

Or add to your MCP client config:

```json
{
  "mcpServers": {
    "netbrain": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/netbrain-mcp", "netbrain-mcp"]
    }
  }
}
```

## Development

```bash
uv run pytest -v          # tests
uv run ruff check .       # lint
uv run ruff format .      # format
uv run mypy src/          # type check
```

## Project Structure

```
netbrain-mcp/
├── src/netbrain_mcp/
│   ├── server.py      -- FastMCP server + tool definitions
│   ├── client.py      -- NetBrain API client + auth lifecycle
│   ├── models.py      -- Pydantic request/response models
│   └── config.py      -- Settings from env/.env
├── tests/
│   ├── test_client.py
│   ├── test_models.py
│   └── test_server.py
├── docs/
│   ├── plan.md        -- Architecture and design
│   └── todo.md        -- Task tracking
├── .env.example
└── pyproject.toml
```

## Error Handling

NetBrain status codes are mapped to readable MCP error responses:

| NetBrain Code | Meaning | MCP Behavior |
|---------------|---------|--------------|
| 790200 | Success | Return data normally |
| 795000 | Auth failure | Re-auth once, retry, then error |
| 791000 | Null/missing param | Return validation error message |
| 791006 | Not found | Return "not found" message |
