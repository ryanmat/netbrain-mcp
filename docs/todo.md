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

## Phase 2: Validation

- [ ] Point at real NetBrain instance (customer provides credentials)
- [ ] Validate auth flow against live API
- [ ] Test pagination on real device inventory
- [ ] Confirm diagnosis workflow end-to-end
- [ ] Rate limiting / session limit testing
- [ ] Verify API endpoint paths match customer's NetBrain version

## Phase 3: Enhancements

- [ ] Additional tools (site mgmt, write ops)
- [ ] LM MCP integration demo (alert -> diagnosis pipeline)
- [ ] Documentation for customer handoff
