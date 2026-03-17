# Description: FastMCP server exposing NetBrain REST API as MCP tools.
# Description: 10 user-facing tools for network inventory, topology, path, diagnosis, and events.
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import Context, FastMCP

from netbrain_mcp.client import NetBrainClient, NetBrainError
from netbrain_mcp.config import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: Any) -> AsyncIterator[dict[str, Any]]:
    """Manage NetBrainClient lifecycle -- lazy auth, clean shutdown."""
    settings = get_settings()
    client = NetBrainClient(settings)
    try:
        yield {"client": client}
    finally:
        await client.close()


mcp = FastMCP(
    "NetBrain MCP Server",
    instructions=(
        "Network troubleshooting tools powered by NetBrain. "
        "Provides device inventory, topology discovery, path calculation, "
        "diagnosis, event monitoring, and change analysis."
    ),
    lifespan=lifespan,
)


def _get_client(ctx: Context) -> NetBrainClient:
    """Extract the NetBrainClient from the lifespan context."""
    return ctx.lifespan_context["client"]  # type: ignore[index]


def _error_response(e: NetBrainError) -> str:
    """Format a NetBrainError as a human-readable string for MCP."""
    return f"NetBrain API error ({e.status_code}): {e.message}"


# -- Tool 1: get_devices --


@mcp.tool()
async def get_devices(
    ctx: Context,
    limit: int = 50,
    skip: int = 0,
    device_type: str = "",
) -> str:
    """List devices in NetBrain inventory.

    Args:
        limit: Max devices to return (default 50, max 1000).
        skip: Number of devices to skip for pagination.
        device_type: Filter by device type name (e.g. "Cisco Router").

    Returns:
        Table of devices with hostname, type, management IP, site, vendor, and model.
    """
    client = _get_client(ctx)
    try:
        devices = await client.get_devices(limit=limit, skip=skip, device_type=device_type)
        if not devices:
            return "No devices found matching the criteria."
        header = (
            f"{'Hostname':<30} {'Type':<20} {'Mgmt IP':<16} "
            f"{'Site':<20} {'Vendor':<15} {'Model'}"
        )
        lines = [header]
        lines.append("-" * 120)
        for d in devices:
            lines.append(
                f"{d.hostname:<30} {d.device_type:<20} {d.mgmt_ip:<16} "
                f"{d.site:<20} {d.vendor:<15} {d.model}"
            )
        lines.append(f"\nShowing {len(devices)} devices (skip={skip}, limit={limit})")
        return "\n".join(lines)
    except NetBrainError as e:
        return _error_response(e)


# -- Tool 2: get_device_attributes --


@mcp.tool()
async def get_device_attributes(ctx: Context, hostname: str) -> str:
    """Get detailed attributes for a specific device.

    Args:
        hostname: Exact hostname of the device in NetBrain.

    Returns:
        Device attributes including type, IPs, serial, location, software version.
    """
    client = _get_client(ctx)
    try:
        attrs = await client.get_device_attributes(hostname)
        lines = [
            f"Hostname:         {attrs.hostname}",
            f"Device Type:      {attrs.device_type}",
            f"Management IP:    {attrs.mgmt_ip}",
            f"Site:             {attrs.site}",
            f"Vendor:           {attrs.vendor}",
            f"Model:            {attrs.model}",
            f"Software Version: {attrs.software_version}",
            f"Serial Number:    {attrs.serial_number}",
            f"Contact:          {attrs.contact}",
            f"Location:         {attrs.location}",
            f"Description:      {attrs.description}",
        ]
        if attrs.attributes:
            lines.append("\nCustom Attributes:")
            for k, v in attrs.attributes.items():
                lines.append(f"  {k}: {v}")
        return "\n".join(lines)
    except NetBrainError as e:
        return _error_response(e)


# -- Tool 3: get_device_config --


@mcp.tool()
async def get_device_config(
    ctx: Context,
    hostname: str,
    config_type: str = "running",
) -> str:
    """Get the running or startup configuration for a device.

    Args:
        hostname: Exact hostname of the device.
        config_type: "running" (default) or "startup".

    Returns:
        Device configuration text with metadata.
    """
    client = _get_client(ctx)
    try:
        config = await client.get_device_config(hostname, config_type=config_type)
        lines = [
            f"Device:       {config.hostname}",
            f"Config Type:  {config.config_type}",
            f"Last Updated: {config.last_updated}",
            "\n--- Configuration ---\n",
            config.content,
        ]
        return "\n".join(lines)
    except NetBrainError as e:
        return _error_response(e)


# -- Tool 4: get_neighbors --


@mcp.tool()
async def get_neighbors(ctx: Context, hostname: str) -> str:
    """Get adjacent/neighboring devices for a device (CDP/LLDP/topology).

    Args:
        hostname: Exact hostname of the device.

    Returns:
        Table of neighbors with interface mappings and protocols.
    """
    client = _get_client(ctx)
    try:
        neighbors = await client.get_neighbors(hostname)
        if not neighbors:
            return f"No neighbors found for {hostname}."
        lines = [
            f"Neighbors of {hostname}:",
            f"{'Interface':<20} {'Neighbor':<30} {'Neighbor Intf':<20} "
            f"{'Type':<20} {'Protocol'}",
            "-" * 110,
        ]
        for n in neighbors:
            lines.append(
                f"{n.interface:<20} {n.neighbor_hostname:<30} "
                f"{n.neighbor_interface:<20} {n.neighbor_device_type:<20} {n.protocol}"
            )
        return "\n".join(lines)
    except NetBrainError as e:
        return _error_response(e)


# -- Tool 5: calculate_path --


@mcp.tool()
async def calculate_path(
    ctx: Context,
    source_ip: str,
    destination_ip: str,
    protocol: int = 4,
    source_port: int = 0,
    destination_port: int = 0,
) -> str:
    """Calculate the network path between two IPs. Polls until complete (up to 30s).

    Args:
        source_ip: Source IP address.
        destination_ip: Destination IP address.
        protocol: IP protocol number (default 4 = IP-in-IP; use 6 for TCP, 17 for UDP).
        source_port: Source port (0 = any).
        destination_port: Destination port (0 = any).

    Returns:
        Hop-by-hop path with device names, interfaces, and status.
    """
    client = _get_client(ctx)
    try:
        result = await client.calculate_path(
            source_ip=source_ip,
            destination_ip=destination_ip,
            protocol=protocol,
            source_port=source_port,
            destination_port=destination_port,
        )
        if result.failure_reason:
            return f"Path calculation failed: {result.failure_reason}"
        if not result.hops:
            return f"Path calculated (status: {result.status}) but no hops returned."
        lines = [
            f"Path: {source_ip} -> {destination_ip} (status: {result.status})",
            f"{'Hop':<5} {'Device':<30} {'Ingress':<20} "
            f"{'Egress':<20} {'Type':<20} {'Status'}",
            "-" * 110,
        ]
        for hop in result.hops:
            lines.append(
                f"{hop.hop_number:<5} {hop.hostname:<30} {hop.ingress_interface:<20} "
                f"{hop.egress_interface:<20} {hop.device_type:<20} {hop.status}"
            )
        return "\n".join(lines)
    except NetBrainError as e:
        return _error_response(e)


# -- Tool 6: trigger_diagnosis --


@mcp.tool()
async def trigger_diagnosis(
    ctx: Context,
    device_hostname: str,
    runbook_name: str = "",
    runbook_id: str = "",
    map_create_mode: int = 0,
) -> str:
    """Trigger a NetBrain diagnosis on a device. Polls until complete (up to 30s).

    Args:
        device_hostname: Hostname of the device to diagnose.
        runbook_name: Name of a specific runbook to execute (optional).
        runbook_id: ID of a specific runbook (optional, alternative to name).
        map_create_mode: 0=no map, 1=new map, 2=existing map, 3=site map.

    Returns:
        Diagnosis results including any runbook output and optional map URL.
    """
    client = _get_client(ctx)
    try:
        result = await client.trigger_diagnosis(
            device_hostname=device_hostname,
            runbook_name=runbook_name,
            runbook_id=runbook_id,
            map_create_mode=map_create_mode,
        )
        if result.failure_reason:
            return f"Diagnosis failed: {result.failure_reason}"
        lines = [
            f"Diagnosis for {device_hostname} (status: {result.status})",
        ]
        if result.map_url:
            lines.append(f"Map URL: {result.map_url}")
        if result.results:
            lines.append("\n--- Results ---")
            for i, r in enumerate(result.results, 1):
                lines.append(f"\nResult {i}:")
                for k, v in r.items():
                    lines.append(f"  {k}: {v}")
        else:
            lines.append("No detailed results returned.")
        return "\n".join(lines)
    except NetBrainError as e:
        return _error_response(e)


# -- Tool 7: get_diagnosis_result --


@mcp.tool()
async def get_diagnosis_result(ctx: Context, task_id: str) -> str:
    """Get the result of a previously triggered diagnosis.

    Args:
        task_id: Task ID from a prior trigger_diagnosis call.

    Returns:
        Diagnosis results and status.
    """
    client = _get_client(ctx)
    try:
        result = await client.get_diagnosis_result(task_id)
        lines = [f"Diagnosis task {task_id} (status: {result.status})"]
        if result.failure_reason:
            lines.append(f"Failure: {result.failure_reason}")
        if result.map_url:
            lines.append(f"Map URL: {result.map_url}")
        if result.results:
            lines.append("\n--- Results ---")
            for i, r in enumerate(result.results, 1):
                lines.append(f"\nResult {i}:")
                for k, v in r.items():
                    lines.append(f"  {k}: {v}")
        return "\n".join(lines)
    except NetBrainError as e:
        return _error_response(e)


# -- Tool 8: get_events --


@mcp.tool()
async def get_events(
    ctx: Context,
    hostname: str = "",
    event_type: str = "",
    limit: int = 50,
) -> str:
    """Get recent network events from NetBrain.

    Args:
        hostname: Filter events by device hostname (optional).
        event_type: Filter by event type (optional).
        limit: Max events to return (default 50).

    Returns:
        Table of events with timestamp, device, type, severity, and message.
    """
    client = _get_client(ctx)
    try:
        events = await client.get_events(hostname=hostname, event_type=event_type, limit=limit)
        if not events:
            return "No events found matching the criteria."
        lines = [
            f"{'Timestamp':<22} {'Device':<25} {'Type':<15} {'Severity':<10} {'Message'}",
            "-" * 110,
        ]
        for e in events:
            lines.append(
                f"{e.timestamp:<22} {e.device_hostname:<25} "
                f"{e.event_type:<15} {e.severity:<10} {e.message}"
            )
        lines.append(f"\nShowing {len(events)} events")
        return "\n".join(lines)
    except NetBrainError as e:
        return _error_response(e)


# -- Tool 9: get_change_analysis --


@mcp.tool()
async def get_change_analysis(
    ctx: Context,
    hostname: str,
    config_type: str = "running",
) -> str:
    """Get configuration change analysis for a device (diff against golden baseline).

    Args:
        hostname: Exact hostname of the device.
        config_type: "running" (default) or "startup".

    Returns:
        Config diff showing what changed from the baseline.
    """
    client = _get_client(ctx)
    try:
        change = await client.get_change_analysis(hostname, config_type=config_type)
        lines = [
            f"Change Analysis for {change.hostname}",
            f"Config Type: {change.config_type}",
            f"Changed At:  {change.changed_at}",
            "\n--- Diff ---\n",
            change.diff if change.diff else "(no changes detected)",
        ]
        return "\n".join(lines)
    except NetBrainError as e:
        return _error_response(e)


# -- Tool 10: search_devices --


@mcp.tool()
async def search_devices(
    ctx: Context,
    keyword: str,
    limit: int = 20,
) -> str:
    """Search for devices by hostname keyword (fuzzy match).

    Use this to resolve partial or approximate device names before calling
    other tools that require an exact hostname.

    Args:
        keyword: Partial hostname or keyword to search for.
        limit: Max results (default 20).

    Returns:
        Matching devices with hostname, type, and management IP.
    """
    client = _get_client(ctx)
    try:
        devices = await client.search_devices(keyword=keyword, limit=limit)
        if not devices:
            return f"No devices found matching '{keyword}'."
        lines = [
            f"Search results for '{keyword}':",
            f"{'Hostname':<30} {'Type':<20} {'Mgmt IP':<16} {'Site'}",
            "-" * 90,
        ]
        for d in devices:
            lines.append(f"{d.hostname:<30} {d.device_type:<20} {d.mgmt_ip:<16} {d.site}")
        return "\n".join(lines)
    except NetBrainError as e:
        return _error_response(e)


def main() -> None:
    """Entry point for the NetBrain MCP server."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    mcp.run()


if __name__ == "__main__":
    main()
