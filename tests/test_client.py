# Description: Unit tests for the NetBrain API client.
# Description: Tests auth lifecycle, error mapping, request handling, and poll logic.
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from netbrain_mcp.client import (
    STATUS_AUTH_FAIL,
    STATUS_NOT_FOUND,
    STATUS_NULL_PARAM,
    STATUS_SUCCESS,
    NetBrainClient,
    NetBrainError,
)
from netbrain_mcp.config import NetBrainSettings


@pytest.fixture
def settings() -> NetBrainSettings:
    return NetBrainSettings(
        url="https://netbrain.test.local",
        username="testuser",
        password="testpass",
        domain="test-domain",
    )


@pytest.fixture
def client(settings: NetBrainSettings) -> NetBrainClient:
    return NetBrainClient(settings)


class TestCheckStatus:
    def test_success_does_not_raise(self) -> None:
        NetBrainClient._check_status({"statusCode": STATUS_SUCCESS})

    def test_zero_does_not_raise(self) -> None:
        NetBrainClient._check_status({"statusCode": 0})

    def test_no_status_code_does_not_raise(self) -> None:
        NetBrainClient._check_status({})

    def test_auth_failure_raises(self) -> None:
        with pytest.raises(NetBrainError) as exc_info:
            NetBrainClient._check_status(
                {"statusCode": STATUS_AUTH_FAIL, "statusDescription": "Token expired"}
            )
        assert exc_info.value.status_code == STATUS_AUTH_FAIL
        assert "Authentication failed" in exc_info.value.message

    def test_null_param_raises(self) -> None:
        with pytest.raises(NetBrainError) as exc_info:
            NetBrainClient._check_status(
                {"statusCode": STATUS_NULL_PARAM, "statusDescription": "hostname is required"}
            )
        assert "Missing or null parameter" in exc_info.value.message

    def test_not_found_raises(self) -> None:
        with pytest.raises(NetBrainError) as exc_info:
            NetBrainClient._check_status(
                {"statusCode": STATUS_NOT_FOUND, "statusDescription": "Device not found"}
            )
        assert "Resource not found" in exc_info.value.message

    def test_unknown_error_raises(self) -> None:
        with pytest.raises(NetBrainError) as exc_info:
            NetBrainClient._check_status(
                {"statusCode": 799999, "statusDescription": "Something weird"}
            )
        assert exc_info.value.status_code == 799999


class TestNetBrainError:
    def test_str_representation(self) -> None:
        err = NetBrainError(791006, "Device not found")
        assert "791006" in str(err)
        assert "Device not found" in str(err)

    def test_attributes(self) -> None:
        err = NetBrainError(795000, "Token expired")
        assert err.status_code == 795000
        assert err.message == "Token expired"


class TestClientInit:
    def test_base_url_strips_trailing_slash(self, settings: NetBrainSettings) -> None:
        settings.url = "https://netbrain.test.local/"
        c = NetBrainClient(settings)
        assert c._base_url == "https://netbrain.test.local"

    def test_token_starts_none(self, client: NetBrainClient) -> None:
        assert client._token is None


class TestAuthHeaders:
    def test_with_token(self, client: NetBrainClient) -> None:
        client._token = "test-token-123"
        headers = client._auth_headers()
        assert headers["Token"] == "test-token-123"
        assert headers["Content-Type"] == "application/json"

    def test_without_token(self, client: NetBrainClient) -> None:
        headers = client._auth_headers()
        assert headers["Token"] == ""


class TestEnsureAuth:
    @pytest.mark.asyncio
    async def test_calls_login_when_no_token(self, client: NetBrainClient) -> None:
        client._login = AsyncMock()  # type: ignore[method-assign]
        await client._ensure_auth()
        client._login.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_login_when_token_exists(self, client: NetBrainClient) -> None:
        client._token = "existing-token"
        client._login = AsyncMock()  # type: ignore[method-assign]
        await client._ensure_auth()
        client._login.assert_not_called()


class TestLogout:
    @pytest.mark.asyncio
    async def test_clears_token(self, client: NetBrainClient) -> None:
        client._token = "old-token"
        mock_response = AsyncMock()
        mock_response.raise_for_status = lambda: None
        client._http.delete = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]
        await client._logout()
        assert client._token is None

    @pytest.mark.asyncio
    async def test_noop_when_no_token(self, client: NetBrainClient) -> None:
        client._http.delete = AsyncMock()  # type: ignore[method-assign]
        await client._logout()
        client._http.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_clears_token_on_failure(self, client: NetBrainClient) -> None:
        client._token = "old-token"
        client._http.delete = AsyncMock(side_effect=Exception("network error"))  # type: ignore[method-assign]
        await client._logout()
        assert client._token is None
