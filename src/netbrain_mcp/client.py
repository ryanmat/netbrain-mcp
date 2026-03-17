# Description: NetBrain REST API client with transparent auth lifecycle.
# Description: Handles login, token refresh, domain selection, error mapping, and polling.
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx

from netbrain_mcp.config import NetBrainSettings
from netbrain_mcp.models import (
    DeviceAttributes,
    DeviceConfig,
    DeviceSummary,
    DiagnosisResult,
    Event,
    GatewayInfo,
    Neighbor,
    PathResult,
)

logger = logging.getLogger(__name__)

# NetBrain custom status codes
STATUS_SUCCESS = 790200
STATUS_AUTH_FAIL = 795000
STATUS_NULL_PARAM = 791000
STATUS_NOT_FOUND = 791006


class NetBrainError(Exception):
    """Raised when a NetBrain API call returns a non-success status."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"NetBrain error {status_code}: {message}")


class NetBrainClient:
    """Async client for the NetBrain REST API.

    Auth is handled internally -- callers never need to login/logout.
    Token refresh happens automatically on auth failure (795000).
    """

    def __init__(self, settings: NetBrainSettings) -> None:
        self._settings = settings
        self._base_url = settings.url.rstrip("/")
        self._token: str | None = None
        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(settings.auth_timeout, read=60.0),
        )

    # -- Auth lifecycle (internal) --

    async def _login(self) -> None:
        """Authenticate and store token."""
        resp = await self._http.post(
            "/ServicesAPI/API/V1/Session",
            json={
                "username": self._settings.username,
                "password": self._settings.password,
            },
        )
        resp.raise_for_status()
        body = resp.json()
        self._check_status(body)
        self._token = body.get("token", "")
        logger.info("NetBrain auth successful")
        await self._set_domain()

    async def _set_domain(self) -> None:
        """Set the working domain (and optionally tenant)."""
        payload: dict[str, str] = {"domainId": self._settings.domain}
        if self._settings.tenant:
            payload["tenantId"] = self._settings.tenant
        resp = await self._http.put(
            "/ServicesAPI/API/V1/Session/CurrentDomain",
            headers=self._auth_headers(),
            json=payload,
        )
        resp.raise_for_status()
        self._check_status(resp.json())
        logger.info("NetBrain domain set to %s", self._settings.domain)

    async def _logout(self) -> None:
        """Release the API session."""
        if not self._token:
            return
        try:
            await self._http.delete(
                "/ServicesAPI/API/V1/Session",
                headers=self._auth_headers(),
            )
            logger.info("NetBrain session released")
        except Exception:
            logger.warning("Failed to release NetBrain session", exc_info=True)
        finally:
            self._token = None

    async def _ensure_auth(self) -> None:
        """Login if no active token."""
        if not self._token:
            await self._login()

    def _auth_headers(self) -> dict[str, str]:
        return {"Token": self._token or "", "Content-Type": "application/json"}

    # -- Request helpers --

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        retry_auth: bool = True,
    ) -> dict[str, Any]:
        """Make an authenticated API request with auto-retry on auth failure."""
        await self._ensure_auth()
        resp = await self._http.request(
            method,
            path,
            headers=self._auth_headers(),
            params=params,
            json=json_body,
        )
        resp.raise_for_status()
        body: dict[str, Any] = resp.json()

        if body.get("statusCode") == STATUS_AUTH_FAIL and retry_auth:
            logger.info("Auth expired, re-authenticating")
            self._token = None
            await self._login()
            return await self._request(
                method, path, params=params, json_body=json_body, retry_auth=False
            )

        self._check_status(body)
        return body

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request("GET", path, params=params)

    async def _post(self, path: str, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request("POST", path, json_body=json_body)

    async def _poll_path_result(self, task_id: str) -> dict[str, Any]:
        """Poll path calculation result until completion or timeout."""
        elapsed = 0.0
        result_path = f"/ServicesAPI/API/V1/CMDB/Path/Calculation/{task_id}/Result"
        while elapsed < self._settings.poll_timeout:
            try:
                resp = await self._get(result_path)
                return resp
            except NetBrainError:
                await asyncio.sleep(self._settings.poll_interval)
                elapsed += self._settings.poll_interval
        raise NetBrainError(
            0, f"Path calculation {task_id} timed out after {self._settings.poll_timeout}s"
        )

    @staticmethod
    def _check_status(body: dict[str, Any]) -> None:
        """Raise NetBrainError if the response indicates failure."""
        code = body.get("statusCode", 0)
        if code and code != STATUS_SUCCESS:
            desc = body.get("statusDescription", "Unknown error")
            if code == STATUS_NULL_PARAM:
                raise NetBrainError(code, f"Missing or null parameter: {desc}")
            if code == STATUS_NOT_FOUND:
                raise NetBrainError(code, f"Resource not found: {desc}")
            if code == STATUS_AUTH_FAIL:
                raise NetBrainError(code, f"Authentication failed: {desc}")
            raise NetBrainError(code, desc)

    # -- Public API methods (called by MCP tools) --

    async def get_devices(
        self,
        limit: int = 50,
        skip: int = 0,
        filter_json: dict[str, Any] | None = None,
    ) -> list[DeviceSummary]:
        """List devices with optional pagination and filter."""
        clamped_limit = max(10, min(limit, 100))
        params: dict[str, Any] = {"limit": clamped_limit, "skip": skip, "version": 1}
        if filter_json:
            params["filter"] = json.dumps(filter_json)
        resp = await self._get("/ServicesAPI/API/V1/CMDB/Devices", params=params)
        raw_devices = resp.get("devices", [])
        return [DeviceSummary.model_validate(d) for d in raw_devices]

    async def search_devices(self, hostname: str) -> list[DeviceSummary]:
        """Search devices by hostname (case-insensitive match)."""
        params: dict[str, Any] = {"hostname": hostname, "ignoreCase": True, "version": 1}
        resp = await self._get("/ServicesAPI/API/V1/CMDB/Devices", params=params)
        raw_devices = resp.get("devices", [])
        return [DeviceSummary.model_validate(d) for d in raw_devices]

    async def get_device_attributes(self, hostname: str) -> DeviceAttributes:
        """Get full attribute set for a specific device."""
        resp = await self._get(
            "/ServicesAPI/API/V1/CMDB/Devices/Attributes",
            params={"hostname": hostname},
        )
        return DeviceAttributes.model_validate(resp)

    async def get_device_config(self, hostname: str) -> DeviceConfig:
        """Get device configuration from the data engine."""
        resp = await self._get(
            "/ServicesAPI/API/V1/CMDB/DataEngine/DeviceData/Configuration",
            params={"hostname": hostname},
        )
        return DeviceConfig.model_validate(resp)

    async def get_neighbors(self, hostname: str, topo_type: int = 1) -> list[Neighbor]:
        """Get neighboring devices."""
        resp = await self._get(
            "/ServicesAPI/API/V1/CMDB/Topology/Devices/Neighbors",
            params={"hostname": hostname, "topoType": topo_type},
        )
        raw_neighbors = resp.get("neighbors", [])
        return [Neighbor.model_validate(n) for n in raw_neighbors]

    async def _resolve_gateway(self, ip_or_host: str) -> GatewayInfo:
        """Resolve the gateway for a given IP or hostname (path calc prerequisite)."""
        resp = await self._get(
            "/ServicesAPI/API/V1/CMDB/Path/Gateways",
            params={"ipOrHost": ip_or_host},
        )
        gateways = resp.get("gatewayList", [])
        if not gateways:
            raise NetBrainError(0, f"No gateway found for {ip_or_host}")
        return GatewayInfo.model_validate(gateways[0])

    async def calculate_path(
        self,
        source_ip: str,
        dest_ip: str,
        protocol: int = 4,
        source_port: int = 0,
        dest_port: int = 0,
        is_live: bool = False,
    ) -> PathResult:
        """Calculate network path from source to destination. Blocks until result."""
        gateway = await self._resolve_gateway(source_ip)
        resp = await self._post(
            "/ServicesAPI/API/V1/CMDB/Path/Calculation",
            json_body={
                "sourceIP": source_ip,
                "sourcePort": source_port,
                "sourceGateway": {
                    "type": gateway.type,
                    "gatewayName": gateway.gateway_name,
                    "payload": gateway.payload,
                },
                "destIP": dest_ip,
                "destPort": dest_port,
                "protocol": protocol,
                "isLive": is_live,
            },
        )
        task_id = resp.get("taskID", "")
        if not task_id:
            return PathResult.model_validate(resp)
        data = await self._poll_path_result(task_id)
        return PathResult.model_validate(data)

    async def trigger_diagnosis(
        self,
        device_hostname: str,
        map_create_mode: int = 0,
        stub_name: str = "",
    ) -> DiagnosisResult:
        """Trigger a diagnosis on a device. Fire-and-forget."""
        payload: dict[str, Any] = {
            "domain_setting": {
                "tenant_id": self._settings.tenant,
                "domain_id": self._settings.domain,
            },
            "basic_setting": {
                "triggered_by": "netbrain-mcp",
                "user": self._settings.username,
                "device": device_hostname,
                "stub_name": stub_name,
                "stub_setting": {"mode": 0},
            },
            "map_setting": {
                "map_create_mode": map_create_mode,
            },
        }
        resp = await self._post("/ServicesAPI/API/V1/Triggers/Run", json_body=payload)
        return DiagnosisResult.model_validate(resp)

    async def get_events(
        self,
        event_type: str = "1,2,3",
        event_level: str = "0,1,2",
        start_time: str = "",
        end_time: str = "",
    ) -> list[Event]:
        """Get events from the NetBrain event console."""
        params: dict[str, Any] = {
            "eventType": event_type,
            "eventLevel": event_level,
        }
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        resp = await self._get("/ServicesAPI/API/V1/CMDB/EventConsole", params=params)
        raw_events = resp.get("content", [])
        return [Event.model_validate(e) for e in raw_events]

    # -- Lifecycle --

    async def close(self) -> None:
        """Logout and close the HTTP client."""
        await self._logout()
        await self._http.aclose()
