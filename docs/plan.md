# NetBrain MCP Server -- Implementation Plan

## Overview

MCP server POC wrapping NetBrain's REST API. Enables natural-language network
troubleshooting for a customer (Lily) who has both NetBrain and LogicMonitor.

## Tool Inventory (10 user-facing)

| # | Tool | Category | Purpose |
|---|------|----------|---------|
| 1 | get_devices | Inventory | List devices with optional filters, pagination |
| 2 | get_device_attributes | Inventory | Full attribute set for a specific device |
| 3 | get_device_config | Inventory | Running/startup config for a device |
| 4 | get_neighbors | Topology | Adjacent devices (CDP/LLDP neighbors) |
| 5 | calculate_path | Path | A-to-B path calculation, block+poll, 30s timeout |
| 6 | trigger_diagnosis | Diagnosis | Run NetBrain diagnosis on a device or path |
| 7 | get_diagnosis_result | Diagnosis | Fetch completed diagnosis output |
| 8 | get_events | Events | Recent network events and changes |
| 9 | get_change_analysis | Change | Config diff / golden baseline comparison |
| 10 | search_devices | Inventory | Fuzzy device name lookup for LLM resolution |

## Internal (not tools)

- `_login()` -- lazy auth on first real tool call
- `_logout()` -- cleanup on server shutdown
- `_set_domain()` -- from env var or auto-resolve
- `_ensure_auth()` -- decorator/wrapper, re-auth on 795000
- `_handle_response()` -- maps NetBrain status codes to MCP responses

## Error Code Mapping

| NetBrain Code | Meaning | MCP Behavior |
|---------------|---------|--------------|
| 790200 | Success | Return data normally |
| 795000 | Auth failure | Re-auth once, retry, then error |
| 791000 | Null/missing param | Return validation error message |
| 791006 | Not found | Return "not found" message |
| Other | Unknown | Return raw error with status code |

## Auth Flow

1. Server starts, no auth performed yet
2. First tool call triggers `_ensure_auth()`
3. `_login()` -> POST /ServicesAPI/API/V1/Session
4. `_set_domain()` -> PUT /ServicesAPI/API/V1/Session/CurrentDomain
5. Token stored in client, sent as header on all subsequent calls
6. On 795000, re-auth once and retry the failed call
7. On server shutdown, `_logout()` -> DELETE /ServicesAPI/API/V1/Session

## Config

Environment variables (via .env):
- NETBRAIN_URL -- base URL of NetBrain instance
- NETBRAIN_USERNAME -- API user
- NETBRAIN_PASSWORD -- API user password
- NETBRAIN_DOMAIN -- domain name (required for multi-tenant)
- NETBRAIN_TENANT -- tenant name (optional, defaults to first)

## File Structure

```
netbrain-mcp/
├── src/netbrain_mcp/
│   ├── __init__.py
│   ├── server.py      -- FastMCP server + tool definitions
│   ├── client.py      -- NetBrain API client + auth lifecycle
│   ├── models.py      -- Pydantic request/response models
│   └── config.py      -- Settings from env/.env
├── tests/
│   ├── __init__.py
│   ├── test_client.py
│   ├── test_models.py
│   └── test_server.py
├── docs/
│   ├── plan.md
│   ├── todo.md
│   └── lessons.md
├── .env.example
├── pyproject.toml
└── CLAUDE.md
```

## Demo Narrative

> "We have a high-latency alert on the link between core-rtr-01 and dist-sw-03.
> What's going on?"
>
> LLM: search_devices("core-rtr-01") -> get_device_attributes(hostname)
> -> calculate_path(src, dst) -> sees hops -> get_device_config(suspect_hop)
> -> trigger_diagnosis(device) -> returns coherent story with evidence.

## Phase 2 (deferred)

- set_device_attribute (write op)
- build_l2/l3_topology (rebuild ops)
- get_connected_switch_port
- Site management tools
- Event acknowledgment (write op)
- Dashboard/map generation
