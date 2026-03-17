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
    configuration: str = ""
    time: str = ""

    model_config = {"populate_by_name": True}


# -- Topology --


class Neighbor(BaseModel):
    hostname: str = ""
    interface: str = ""

    model_config = {"populate_by_name": True}


# -- Path --


class GatewayInfo(BaseModel):
    gateway_name: str = Field(alias="gatewayName", default="")
    type: str = ""
    payload: str = ""

    model_config = {"populate_by_name": True}


class PathRequest(BaseModel):
    source_ip: str = Field(alias="sourceIP")
    destination_ip: str = Field(alias="destinationIP")
    source_port: int = Field(alias="sourcePort", default=0)
    destination_port: int = Field(alias="destinationPort", default=0)
    protocol: int = 4

    model_config = {"populate_by_name": True}


class PathHop(BaseModel):
    hop_id: str = Field(alias="hopId", default="")
    src_device_name: str = Field(alias="srcDeviceName", default="")
    inbound_interface: str = Field(alias="inboundInterface", default="")
    media_name: str = Field(alias="mediaName", default="")
    dst_device_name: str = Field(alias="dstDeviceName", default="")
    outbound_interface: str = Field(alias="outboundInterface", default="")
    next_hop_id_list: list[str] = Field(alias="nextHopIdList", default_factory=list)

    model_config = {"populate_by_name": True}


class PathResult(BaseModel):
    task_id: str = Field(alias="taskID", default="")
    status: str = ""
    hop_list: list[PathHop] = Field(alias="hopList", default_factory=list)
    failure_reason: str = Field(alias="failureReason", default="")

    model_config = {"populate_by_name": True}


# -- Diagnosis --


class DiagnosisRequest(BaseModel):
    device_hostname: str = Field(alias="deviceHostname")
    map_create_mode: int = Field(alias="mapCreateMode", default=0)
    stub_name: str = Field(alias="stubName", default="")

    model_config = {"populate_by_name": True}


class DiagnosisResult(BaseModel):
    task_id: str = Field(alias="taskID", default="")
    status: str = ""
    results: list[dict[str, Any]] = Field(default_factory=list)
    map_url: str = Field(alias="mapUrl", default="")
    failure_reason: str = Field(alias="failureReason", default="")

    model_config = {"populate_by_name": True}


# -- Events --


class Event(BaseModel):
    device: str = ""
    event: str = ""
    first_time: str = Field(alias="firstTime", default="")
    last_time: str = Field(alias="lastTime", default="")
    count: int = 0
    acknowledged: bool = False
    status: bool = False
    executed_by: str = Field(alias="executedBy", default="")
    from_task: str = Field(alias="fromTask", default="")
    task_type: int = Field(alias="taskType", default=0)

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
