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
    GatewayInfo,
    LoginResponse,
    Neighbor,
    NetBrainResponse,
    PathHop,
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
            "configuration": "interface GigabitEthernet0/0\n ip address 10.1.1.1 255.255.255.0",
            "time": "2026-03-15T10:30:00Z",
        }
        config = DeviceConfig.model_validate(data)
        assert config.hostname == "core-rtr-01"
        assert "GigabitEthernet" in config.configuration
        assert config.time == "2026-03-15T10:30:00Z"

    def test_defaults(self) -> None:
        config = DeviceConfig.model_validate({})
        assert config.configuration == ""
        assert config.time == ""


class TestNeighbor:
    def test_from_api_payload(self) -> None:
        data = {
            "hostname": "sw-01",
            "interface": "Gi0/1",
        }
        neighbor = Neighbor.model_validate(data)
        assert neighbor.hostname == "sw-01"
        assert neighbor.interface == "Gi0/1"

    def test_defaults(self) -> None:
        neighbor = Neighbor.model_validate({})
        assert neighbor.hostname == ""
        assert neighbor.interface == ""


class TestGatewayInfo:
    def test_from_api_payload(self) -> None:
        data = {
            "gatewayName": "gw-01",
            "type": "static",
            "payload": '{"ip": "10.0.0.1"}',
        }
        gw = GatewayInfo.model_validate(data)
        assert gw.gateway_name == "gw-01"
        assert gw.type == "static"
        assert gw.payload == '{"ip": "10.0.0.1"}'

    def test_defaults(self) -> None:
        gw = GatewayInfo.model_validate({})
        assert gw.gateway_name == ""
        assert gw.type == ""


class TestPathHop:
    def test_from_api_payload(self) -> None:
        data = {
            "hopId": "hop-1",
            "srcDeviceName": "core-rtr-01",
            "inboundInterface": "Gi0/0",
            "mediaName": "10.1.1.0/24",
            "dstDeviceName": "dist-sw-01",
            "outboundInterface": "Gi0/1",
            "nextHopIdList": ["hop-2", "hop-3"],
        }
        hop = PathHop.model_validate(data)
        assert hop.hop_id == "hop-1"
        assert hop.src_device_name == "core-rtr-01"
        assert hop.dst_device_name == "dist-sw-01"
        assert hop.next_hop_id_list == ["hop-2", "hop-3"]


class TestPathResult:
    def test_with_hops(self) -> None:
        data = {
            "taskID": "task-001",
            "status": "Finished",
            "hopList": [
                {
                    "hopId": "hop-1",
                    "srcDeviceName": "core-rtr-01",
                    "inboundInterface": "Gi0/0",
                    "mediaName": "10.1.1.0/24",
                    "dstDeviceName": "dist-sw-01",
                    "outboundInterface": "Gi0/1",
                    "nextHopIdList": ["hop-2"],
                },
                {
                    "hopId": "hop-2",
                    "srcDeviceName": "dist-sw-01",
                    "inboundInterface": "Gi0/0",
                    "mediaName": "10.2.2.0/24",
                    "dstDeviceName": "access-sw-01",
                    "outboundInterface": "",
                    "nextHopIdList": [],
                },
            ],
        }
        result = PathResult.model_validate(data)
        assert result.task_id == "task-001"
        assert result.status == "Finished"
        assert len(result.hop_list) == 2
        assert result.hop_list[0].src_device_name == "core-rtr-01"
        assert result.hop_list[1].dst_device_name == "access-sw-01"

    def test_failed_path(self) -> None:
        data = {
            "taskID": "task-002",
            "status": "Failed",
            "hopList": [],
            "failureReason": "No route found",
        }
        result = PathResult.model_validate(data)
        assert result.failure_reason == "No route found"
        assert result.hop_list == []


class TestDiagnosisResult:
    def test_with_results(self) -> None:
        data = {
            "taskID": "diag-001",
            "status": "Completed",
            "results": [{"check": "BGP status", "output": "All peers established"}],
            "mapUrl": "https://netbrain.example.com/map/123",
        }
        result = DiagnosisResult.model_validate(data)
        assert result.task_id == "diag-001"
        assert result.status == "Completed"
        assert len(result.results) == 1
        assert result.map_url == "https://netbrain.example.com/map/123"


class TestEvent:
    def test_from_api_payload(self) -> None:
        data = {
            "device": "core-rtr-01",
            "event": "Interface Down",
            "firstTime": "2026-03-16T08:00:00Z",
            "lastTime": "2026-03-16T09:00:00Z",
            "count": 3,
            "acknowledged": False,
            "status": True,
            "executedBy": "admin",
            "fromTask": "task-001",
            "taskType": 1,
        }
        event = Event.model_validate(data)
        assert event.device == "core-rtr-01"
        assert event.event == "Interface Down"
        assert event.first_time == "2026-03-16T08:00:00Z"
        assert event.last_time == "2026-03-16T09:00:00Z"
        assert event.count == 3
        assert event.acknowledged is False
        assert event.task_type == 1

    def test_defaults(self) -> None:
        event = Event.model_validate({})
        assert event.device == ""
        assert event.count == 0
        assert event.acknowledged is False


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
