# Description: NetBrain REST API client with transparent auth lifecycle.
# Description: Handles login, token refresh, domain selection, error mapping, and polling.
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from netbrain_mcp.config import NetBrainSettings
from netbrain_mcp.models import (
    ChangeAnalysis,
    DeviceAttributes,
    DeviceConfig,
    DeviceSummary,
    DiagnosisResult,
    Event,
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
        json: dict[str, Any] | None = None,
        retry_auth: bool = True,
    ) -> dict[str, Any]:
        """Make an authenticated API request with auto-retry on auth failure."""
        await self._ensure_auth()
        resp = await self._http.request(
            method,
            path,
            headers=self._auth_headers(),
            params=params,
            json=json,
        )
        resp.raise_for_status()
        body: dict[str, Any] = resp.json()

        if body.get("statusCode") == STATUS_AUTH_FAIL and retry_auth:
            logger.info("Auth expired, re-authenticating")
            self._token = None
            await self._login()
            return await self._request(method, path, params=params, json=json, retry_auth=False)

        self._check_status(body)
        return body

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request("GET", path, params=params)

    async def _post(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request("POST", path, json=json)

    async def _poll_task(self, result_path: str, task_id: str) -> dict[str, Any]:
        """Poll an async task until completion or timeout."""
        elapsed = 0.0
        while elapsed < self._settings.poll_timeout:
            resp = await self._get(f"{result_path}/{task_id}")
            data = resp.get("data", {})
            status = data.get("status", "")
            if status in ("Finished", "Failed", "Error", "Completed"):
                return data
            await asyncio.sleep(self._settings.poll_interval)
            elapsed += self._settings.poll_interval
        raise NetBrainError(0, f"Task {task_id} timed out after {self._settings.poll_timeout}s")

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
        self, limit: int = 50, skip: int = 0, device_type: str = ""
    ) -> list[DeviceSummary]:
        """List devices with optional pagination and type filter."""
        params: dict[str, Any] = {"limit": limit, "skip": skip}
        if device_type:
            params["deviceTypeName"] = device_type
        resp = await self._get("/ServicesAPI/API/V1/CMDB/Devices", params=params)
        raw_devices = resp.get("data", {}).get("devices", [])
        return [DeviceSummary.model_validate(d) for d in raw_devices]

    async def search_devices(self, keyword: str, limit: int = 20) -> list[DeviceSummary]:
        """Search devices by hostname keyword."""
        params: dict[str, Any] = {"keyword": keyword, "limit": limit}
        resp = await self._get("/ServicesAPI/API/V1/CMDB/Devices", params=params)
        raw_devices = resp.get("data", {}).get("devices", [])
        return [DeviceSummary.model_validate(d) for d in raw_devices]

    async def get_device_attributes(self, hostname: str) -> DeviceAttributes:
        """Get full attribute set for a specific device."""
        resp = await self._get(
            "/ServicesAPI/API/V1/CMDB/Devices/Attributes",
            params={"hostname": hostname},
        )
        return DeviceAttributes.model_validate(resp.get("data", {}))

    async def get_device_config(self, hostname: str, config_type: str = "running") -> DeviceConfig:
        """Get device configuration (running or startup)."""
        resp = await self._get(
            f"/ServicesAPI/API/V1/CMDB/Devices/{hostname}/Configs",
            params={"configType": config_type},
        )
        return DeviceConfig.model_validate(resp.get("data", {}))

    async def get_neighbors(self, hostname: str) -> list[Neighbor]:
        """Get neighboring devices (CDP/LLDP)."""
        resp = await self._get(f"/ServicesAPI/API/V1/CMDB/Topology/Devices/{hostname}/Neighbors")
        raw_neighbors = resp.get("data", [])
        return [Neighbor.model_validate(n) for n in raw_neighbors]

    async def calculate_path(
        self,
        source_ip: str,
        destination_ip: str,
        protocol: int = 4,
        source_port: int = 0,
        destination_port: int = 0,
    ) -> PathResult:
        """Calculate network path from source to destination. Blocks until result."""
        resp = await self._post(
            "/ServicesAPI/API/V1/Topology/Path",
            json={
                "sourceIP": source_ip,
                "destinationIP": destination_ip,
                "protocol": protocol,
                "sourcePort": source_port,
                "destinationPort": destination_port,
            },
        )
        task_id = resp.get("data", {}).get("taskId", "")
        if not task_id:
            return PathResult.model_validate(resp.get("data", {}))
        data = await self._poll_task("/ServicesAPI/API/V1/Topology/Path/Result", task_id)
        return PathResult.model_validate(data)

    async def trigger_diagnosis(
        self,
        device_hostname: str,
        runbook_name: str = "",
        runbook_id: str = "",
        map_create_mode: int = 0,
    ) -> DiagnosisResult:
        """Trigger a diagnosis on a device. Blocks until result."""
        payload: dict[str, Any] = {"deviceHostname": device_hostname}
        if runbook_name:
            payload["runbookName"] = runbook_name
        if runbook_id:
            payload["runbookId"] = runbook_id
        if map_create_mode:
            payload["mapCreateMode"] = map_create_mode
        resp = await self._post("/ServicesAPI/API/V1/Triggered/Diagnosis", json=payload)
        task_id = resp.get("data", {}).get("taskId", "")
        if not task_id:
            return DiagnosisResult.model_validate(resp.get("data", {}))
        data = await self._poll_task("/ServicesAPI/API/V1/Triggered/Diagnosis/Result", task_id)
        return DiagnosisResult.model_validate(data)

    async def get_diagnosis_result(self, task_id: str) -> DiagnosisResult:
        """Get the result of a previously triggered diagnosis by task ID."""
        resp = await self._get(f"/ServicesAPI/API/V1/Triggered/Diagnosis/Result/{task_id}")
        return DiagnosisResult.model_validate(resp.get("data", {}))

    async def get_events(
        self,
        hostname: str = "",
        event_type: str = "",
        limit: int = 50,
    ) -> list[Event]:
        """Get recent network events, optionally filtered by device or type."""
        params: dict[str, Any] = {"limit": limit}
        if hostname:
            params["hostname"] = hostname
        if event_type:
            params["eventType"] = event_type
        resp = await self._get("/ServicesAPI/API/V1/Events", params=params)
        raw_events = resp.get("data", {}).get("events", [])
        return [Event.model_validate(e) for e in raw_events]

    async def get_change_analysis(
        self, hostname: str, config_type: str = "running"
    ) -> ChangeAnalysis:
        """Get config change analysis (diff against baseline) for a device."""
        resp = await self._get(
            f"/ServicesAPI/API/V1/CMDB/Devices/{hostname}/ChangeAnalysis",
            params={"configType": config_type},
        )
        return ChangeAnalysis.model_validate(resp.get("data", {}))

    # -- Lifecycle --

    async def close(self) -> None:
        """Logout and close the HTTP client."""
        await self._logout()
        await self._http.aclose()
