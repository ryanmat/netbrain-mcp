# Description: Pydantic models for NetBrain API request and response payloads.
# Description: Covers auth, devices, topology, path, diagnosis, events, and change analysis.
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# -- Auth --


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str = ""
    status_code: int = Field(alias="statusCode", default=0)
    status_description: str = Field(alias="statusDescription", default="")


class SetDomainRequest(BaseModel):
    domain_id: str = Field(alias="domainId")
    tenant_id: str = Field(alias="tenantId", default="")


# -- Common --


class NetBrainResponse(BaseModel):
    """Standard NetBrain API response wrapper."""

    status_code: int = Field(alias="statusCode", default=0)
    status_description: str = Field(alias="statusDescription", default="")
    data: Any = None

    model_config = {"populate_by_name": True}


# -- Devices --


class DeviceSummary(BaseModel):
    hostname: str = ""
    device_type: str = Field(alias="deviceTypeName", default="")
    mgmt_ip: str = Field(alias="mgmtIP", default="")
    site: str = ""
    vendor: str = ""
    model: str = ""
    software_version: str = Field(alias="softwareVersion", default="")

    model_config = {"populate_by_name": True}


class DeviceAttributes(BaseModel):
    hostname: str = ""
    device_type: str = Field(alias="deviceTypeName", default="")
    mgmt_ip: str = Field(alias="mgmtIP", default="")
    site: str = ""
    vendor: str = ""
    model: str = ""
    software_version: str = Field(alias="softwareVersion", default="")
    serial_number: str = Field(alias="serialNumber", default="")
    contact: str = ""
    location: str = ""
    description: str = ""
    attributes: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class DeviceConfig(BaseModel):
    hostname: str = ""
    config_type: str = Field(alias="configType", default="")
    content: str = ""
    last_updated: str = Field(alias="lastUpdated", default="")

    model_config = {"populate_by_name": True}


# -- Topology --


class Neighbor(BaseModel):
    hostname: str = ""
    interface: str = ""
    neighbor_hostname: str = Field(alias="neighborHostname", default="")
    neighbor_interface: str = Field(alias="neighborInterface", default="")
    neighbor_device_type: str = Field(alias="neighborDeviceType", default="")
    protocol: str = ""

    model_config = {"populate_by_name": True}


# -- Path --


class PathRequest(BaseModel):
    source_ip: str = Field(alias="sourceIP")
    destination_ip: str = Field(alias="destinationIP")
    source_port: int = Field(alias="sourcePort", default=0)
    destination_port: int = Field(alias="destinationPort", default=0)
    protocol: int = 4

    model_config = {"populate_by_name": True}


class PathHop(BaseModel):
    hostname: str = ""
    ingress_interface: str = Field(alias="ingressInterface", default="")
    egress_interface: str = Field(alias="egressInterface", default="")
    hop_number: int = Field(alias="hopNumber", default=0)
    device_type: str = Field(alias="deviceType", default="")
    status: str = ""

    model_config = {"populate_by_name": True}


class PathResult(BaseModel):
    task_id: str = Field(alias="taskId", default="")
    status: str = ""
    hops: list[PathHop] = Field(default_factory=list)
    failure_reason: str = Field(alias="failureReason", default="")

    model_config = {"populate_by_name": True}


# -- Diagnosis --


class DiagnosisRequest(BaseModel):
    device_hostname: str = Field(alias="deviceHostname")
    map_create_mode: int = Field(alias="mapCreateMode", default=0)
    runbook_id: str = Field(alias="runbookId", default="")
    runbook_name: str = Field(alias="runbookName", default="")

    model_config = {"populate_by_name": True}


class DiagnosisResult(BaseModel):
    task_id: str = Field(alias="taskId", default="")
    status: str = ""
    results: list[dict[str, Any]] = Field(default_factory=list)
    map_url: str = Field(alias="mapUrl", default="")
    failure_reason: str = Field(alias="failureReason", default="")

    model_config = {"populate_by_name": True}


# -- Events --


class Event(BaseModel):
    event_id: str = Field(alias="eventId", default="")
    event_type: str = Field(alias="eventType", default="")
    device_hostname: str = Field(alias="deviceHostname", default="")
    message: str = ""
    timestamp: str = ""
    severity: str = ""

    model_config = {"populate_by_name": True}


# -- Change Analysis --


class ChangeAnalysis(BaseModel):
    hostname: str = ""
    config_type: str = Field(alias="configType", default="")
    baseline: str = ""
    current: str = ""
    diff: str = ""
    changed_at: str = Field(alias="changedAt", default="")

    model_config = {"populate_by_name": True}
