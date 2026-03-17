# Description: Unit tests for NetBrain pydantic models.
# Description: Validates serialization, deserialization, and default handling.
from __future__ import annotations

from netbrain_mcp.models import (
    ChangeAnalysis,
    DeviceAttributes,
    DeviceConfig,
    DeviceSummary,
    DiagnosisResult,
    Event,
    LoginResponse,
    Neighbor,
    NetBrainResponse,
    PathResult,
)


class TestLoginResponse:
    def test_from_api_payload(self) -> None:
        data = {"token": "abc123", "statusCode": 790200, "statusDescription": "Success"}
        resp = LoginResponse.model_validate(data)
        assert resp.token == "abc123"
        assert resp.status_code == 790200

    def test_defaults(self) -> None:
        resp = LoginResponse.model_validate({})
        assert resp.token == ""
        assert resp.status_code == 0


class TestNetBrainResponse:
    def test_success_response(self) -> None:
        data = {"statusCode": 790200, "statusDescription": "Success", "data": {"key": "value"}}
        resp = NetBrainResponse.model_validate(data)
        assert resp.status_code == 790200
        assert resp.data == {"key": "value"}

    def test_error_response(self) -> None:
        data = {"statusCode": 791006, "statusDescription": "Not found"}
        resp = NetBrainResponse.model_validate(data)
        assert resp.status_code == 791006
        assert resp.data is None


class TestDeviceSummary:
    def test_from_api_payload(self) -> None:
        data = {
            "hostname": "core-rtr-01",
            "deviceTypeName": "Cisco Router",
            "mgmtIP": "10.1.1.1",
            "site": "HQ",
            "vendor": "Cisco",
            "model": "ISR4451",
            "softwareVersion": "16.12.4",
        }
        device = DeviceSummary.model_validate(data)
        assert device.hostname == "core-rtr-01"
        assert device.device_type == "Cisco Router"
        assert device.mgmt_ip == "10.1.1.1"
        assert device.software_version == "16.12.4"

    def test_defaults(self) -> None:
        device = DeviceSummary.model_validate({})
        assert device.hostname == ""
        assert device.device_type == ""


class TestDeviceAttributes:
    def test_with_custom_attributes(self) -> None:
        data = {
            "hostname": "sw-01",
            "deviceTypeName": "Cisco Switch",
            "mgmtIP": "10.2.2.2",
            "serialNumber": "FOC12345",
            "attributes": {"rack": "A3", "floor": "2"},
        }
        attrs = DeviceAttributes.model_validate(data)
        assert attrs.serial_number == "FOC12345"
        assert attrs.attributes["rack"] == "A3"


class TestDeviceConfig:
    def test_from_api_payload(self) -> None:
        data = {
            "hostname": "core-rtr-01",
            "configType": "running",
            "content": "interface GigabitEthernet0/0\n ip address 10.1.1.1 255.255.255.0",
            "lastUpdated": "2026-03-15T10:30:00Z",
        }
        config = DeviceConfig.model_validate(data)
        assert config.config_type == "running"
        assert "GigabitEthernet" in config.content
        assert config.last_updated == "2026-03-15T10:30:00Z"


class TestNeighbor:
    def test_from_api_payload(self) -> None:
        data = {
            "hostname": "sw-01",
            "interface": "Gi0/1",
            "neighborHostname": "core-rtr-01",
            "neighborInterface": "Gi0/0",
            "neighborDeviceType": "Cisco Router",
            "protocol": "CDP",
        }
        neighbor = Neighbor.model_validate(data)
        assert neighbor.neighbor_hostname == "core-rtr-01"
        assert neighbor.protocol == "CDP"


class TestPathResult:
    def test_with_hops(self) -> None:
        data = {
            "taskId": "task-001",
            "status": "Finished",
            "hops": [
                {
                    "hostname": "core-rtr-01",
                    "ingressInterface": "Gi0/0",
                    "egressInterface": "Gi0/1",
                    "hopNumber": 1,
                    "deviceType": "Router",
                    "status": "forwarding",
                },
                {
                    "hostname": "dist-sw-01",
                    "ingressInterface": "Gi0/0",
                    "egressInterface": "",
                    "hopNumber": 2,
                    "deviceType": "Switch",
                    "status": "destination",
                },
            ],
        }
        result = PathResult.model_validate(data)
        assert result.status == "Finished"
        assert len(result.hops) == 2
        assert result.hops[0].hostname == "core-rtr-01"
        assert result.hops[1].hop_number == 2

    def test_failed_path(self) -> None:
        data = {
            "taskId": "task-002",
            "status": "Failed",
            "hops": [],
            "failureReason": "No route found",
        }
        result = PathResult.model_validate(data)
        assert result.failure_reason == "No route found"
        assert result.hops == []


class TestDiagnosisResult:
    def test_with_results(self) -> None:
        data = {
            "taskId": "diag-001",
            "status": "Completed",
            "results": [{"check": "BGP status", "output": "All peers established"}],
            "mapUrl": "https://netbrain.example.com/map/123",
        }
        result = DiagnosisResult.model_validate(data)
        assert result.status == "Completed"
        assert len(result.results) == 1
        assert result.map_url == "https://netbrain.example.com/map/123"


class TestEvent:
    def test_from_api_payload(self) -> None:
        data = {
            "eventId": "evt-001",
            "eventType": "ConfigChange",
            "deviceHostname": "core-rtr-01",
            "message": "Running config changed",
            "timestamp": "2026-03-16T08:00:00Z",
            "severity": "Warning",
        }
        event = Event.model_validate(data)
        assert event.event_type == "ConfigChange"
        assert event.severity == "Warning"


class TestChangeAnalysis:
    def test_with_diff(self) -> None:
        data = {
            "hostname": "core-rtr-01",
            "configType": "running",
            "baseline": "interface Gi0/0\n shutdown",
            "current": "interface Gi0/0\n no shutdown",
            "diff": "- shutdown\n+ no shutdown",
            "changedAt": "2026-03-16T09:00:00Z",
        }
        change = ChangeAnalysis.model_validate(data)
        assert "no shutdown" in change.diff
        assert change.changed_at == "2026-03-16T09:00:00Z"
