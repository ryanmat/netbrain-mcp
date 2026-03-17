# NetBrain MCP Server -- Task Tracking

## Phase 1: POC Scaffold (complete)

- [x] Project init (uv, dependencies, folder structure)
- [x] CLAUDE.md, plan.md, todo.md, lessons.md
- [x] config.py -- pydantic-settings for env vars
- [x] models.py -- request/response pydantic models
- [x] client.py -- NetBrain API client with auth lifecycle
- [x] server.py -- FastMCP server with 10 tools (Context-based DI)
- [x] .env.example
- [x] Unit tests (test_models.py, test_client.py) -- 32 passing
- [x] Integration test stubs (test_server.py) -- 3 passing
- [x] pyproject.toml -- ruff/mypy config, hatchling build, entry point

## Phase 1.5: R11.1b API Alignment (complete)

- [x] Fix all endpoints/params to match NetBrain REST API R11.1b docs
- [x] Fix response parsing -- remove incorrect `data` wrapper (flat responses)
- [x] DeviceConfig: fields now `configuration` + `time` (not `config_type`/`content`/`lastUpdated`)
- [x] Neighbor: simplified to `hostname` + `interface` only
- [x] Event: rewritten for EventConsole API (`device`, `event`, `firstTime`, `lastTime`, etc.)
- [x] PathHop: new fields (`hopId`, `srcDeviceName`, `dstDeviceName`, `inboundInterface`, etc.)
- [x] PathResult/DiagnosisResult: `taskID` alias (capital D)
- [x] Added GatewayInfo model and `_resolve_gateway` method for path calculation
- [x] calculate_path: gateway resolve + POST to `/CMDB/Path/Calculation` + poll result
- [x] trigger_diagnosis: rewritten for `/Triggers/Run` with domain/basic/map settings payload
- [x] get_events: new endpoint `/CMDB/EventConsole` with event_type/event_level/time params
- [x] get_device_config: endpoint changed to `/CMDB/DataEngine/DeviceData/Configuration`
- [x] get_neighbors: hostname + topoType as query params
- [x] get_devices: filter_json param, version=1, limit clamped 10-100
- [x] search_devices: hostname param (not keyword), ignoreCase
- [x] Removed `get_diagnosis_result` tool (no backing API endpoint)
- [x] Stubbed `get_change_analysis` for Phase 2 (3-step export workflow)
- [x] Tool count: 10 -> 9
- [x] All tests updated and passing (43 tests)

## Phase 2: Validation

- [ ] Point at real NetBrain instance (customer provides credentials)
- [ ] Validate auth flow against live API
- [ ] Test pagination on real device inventory
- [ ] Confirm diagnosis workflow end-to-end
- [ ] Rate limiting / session limit testing
- [ ] Implement change_analysis export workflow (create task, poll, download)

## Phase 3: Enhancements

- [ ] Additional tools (site mgmt, write ops)
- [ ] LM MCP integration demo (alert -> diagnosis pipeline)
- [ ] Documentation for customer handoff
