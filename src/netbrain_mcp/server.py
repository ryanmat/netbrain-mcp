# Description: FastMCP server exposing NetBrain REST API as MCP tools.
# Description: 9 user-facing tools for network inventory, topology, path, diagnosis, and events.
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
    return ctx.lifespan_context["client"]  # type: ignore[no-any-return]


def _error_response(e: NetBrainError) -> str:
    """Format a NetBrainError as a human-readable string for MCP."""
    return f"NetBrain API error ({e.status_code}): {e.message}"


# -- Tool 1: get_devices --


@mcp.tool()
async def get_devices(
    ctx: Context,
    limit: int = 50,
    skip: int = 0,
    device_type_filter: str = "",
) -> str:
    """List devices in NetBrain inventory.

    Args:
        limit: Max devices to return (default 50, clamped to 10-100).
        skip: Number of devices to skip for pagination.
        device_type_filter: Filter by sub-type name (e.g. "Cisco Router").

    Returns:
        Table of devices with hostname, type, management IP, site, vendor, and model.
    """
    client = _get_client(ctx)
    try:
        filter_json = {"subTypeName": device_type_filter} if device_type_filter else None
        devices = await client.get_devices(limit=limit, skip=skip, filter_json=filter_json)
        if not devices:
            return "No devices found matching the criteria."
        header = (
            f"{'Hostname':<30} {'Type':<20} {'Mgmt IP':<16} {'Site':<20} {'Vendor':<15} {'Model'}"
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
async def get_device_config(ctx: Context, hostname: str) -> str:
    """Get the device configuration from the NetBrain data engine.

    Args:
        hostname: Exact hostname of the device.

    Returns:
        Device configuration text with metadata.
    """
    client = _get_client(ctx)
    try:
        config = await client.get_device_config(hostname)
        lines = [
            f"Device:       {config.hostname}",
            f"Retrieved:    {config.time}",
            "\n--- Configuration ---\n",
            config.configuration,
        ]
        return "\n".join(lines)
    except NetBrainError as e:
        return _error_response(e)


# -- Tool 4: get_neighbors --


@mcp.tool()
async def get_neighbors(ctx: Context, hostname: str, topo_type: int = 1) -> str:
    """Get adjacent/neighboring devices for a device.

    Args:
        hostname: Exact hostname of the device.
        topo_type: Topology type (1=L3, 2=L2, 10=L3+L2, 11=IPv6).

    Returns:
        Table of neighbors with hostname and interface.
    """
    client = _get_client(ctx)
    try:
        neighbors = await client.get_neighbors(hostname, topo_type=topo_type)
        if not neighbors:
            return f"No neighbors found for {hostname}."
        lines = [
            f"Neighbors of {hostname}:",
            f"{'Hostname':<30} {'Interface'}",
            "-" * 50,
        ]
        for n in neighbors:
            lines.append(f"{n.hostname:<30} {n.interface}")
        return "\n".join(lines)
    except NetBrainError as e:
        return _error_response(e)


# -- Tool 5: calculate_path --


@mcp.tool()
async def calculate_path(
    ctx: Context,
    source_ip: str,
    dest_ip: str,
    protocol: int = 4,
    source_port: int = 0,
    dest_port: int = 0,
    is_live: bool = False,
) -> str:
    """Calculate the network path between two IPs. Polls until complete (up to 30s).

    Args:
        source_ip: Source IP address.
        dest_ip: Destination IP address.
        protocol: IP protocol number (default 4 = IP-in-IP; use 6 for TCP, 17 for UDP).
        source_port: Source port (0 = any).
        dest_port: Destination port (0 = any).
        is_live: True to use live network data, False for cached data.

    Returns:
        Hop-by-hop path with device names, interfaces, and media.
    """
    client = _get_client(ctx)
    try:
        result = await client.calculate_path(
            source_ip=source_ip,
            dest_ip=dest_ip,
            protocol=protocol,
            source_port=source_port,
            dest_port=dest_port,
            is_live=is_live,
        )
        if result.failure_reason:
            return f"Path calculation failed: {result.failure_reason}"
        if not result.hop_list:
            return f"Path calculated (status: {result.status}) but no hops returned."
        lines = [
            f"Path: {source_ip} -> {dest_ip} (status: {result.status})",
            f"{'HopID':<8} {'Source':<25} {'Inbound':<20} "
            f"{'Media':<20} {'Destination':<25} {'Outbound'}",
            "-" * 130,
        ]
        for hop in result.hop_list:
            lines.append(
                f"{hop.hop_id:<8} {hop.src_device_name:<25} "
                f"{hop.inbound_interface:<20} {hop.media_name:<20} "
                f"{hop.dst_device_name:<25} {hop.outbound_interface}"
            )
        return "\n".join(lines)
    except NetBrainError as e:
        return _error_response(e)


# -- Tool 6: trigger_diagnosis --


@mcp.tool()
async def trigger_diagnosis(
    ctx: Context,
    device_hostname: str,
    map_create_mode: int = 0,
    stub_name: str = "",
) -> str:
    """Trigger a NetBrain diagnosis on a device. Fire-and-forget.

    Args:
        device_hostname: Hostname of the device to diagnose.
        map_create_mode: 0=no map, 1=new map, 2=existing map, 3=site map.
        stub_name: Name of a specific diagnostic stub to run (optional).

    Returns:
        Diagnosis trigger result with task status and optional map URL.
    """
    client = _get_client(ctx)
    try:
        result = await client.trigger_diagnosis(
            device_hostname=device_hostname,
            map_create_mode=map_create_mode,
            stub_name=stub_name,
        )
        if result.failure_reason:
            return f"Diagnosis failed: {result.failure_reason}"
        lines = [
            f"Diagnosis triggered for {device_hostname} (status: {result.status})",
        ]
        if result.task_id:
            lines.append(f"Task ID: {result.task_id}")
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


# -- Tool 7: get_events --


@mcp.tool()
async def get_events(
    ctx: Context,
    event_type: str = "1,2,3",
    event_level: str = "0,1,2",
    start_time: str = "",
    end_time: str = "",
) -> str:
    """Get events from the NetBrain event console.

    Args:
        event_type: Comma-separated event type IDs (default "1,2,3").
        event_level: Comma-separated severity levels (default "0,1,2").
        start_time: Start time filter (ISO format, optional).
        end_time: End time filter (ISO format, optional).

    Returns:
        Table of events with device, event, timestamps, count, and status.
    """
    client = _get_client(ctx)
    try:
        events = await client.get_events(
            event_type=event_type,
            event_level=event_level,
            start_time=start_time,
            end_time=end_time,
        )
        if not events:
            return "No events found matching the criteria."
        lines = [
            f"{'Device':<25} {'Event':<30} {'First Time':<22} "
            f"{'Last Time':<22} {'Count':<6} {'Ack'}",
            "-" * 130,
        ]
        for e in events:
            ack = "Yes" if e.acknowledged else "No"
            lines.append(
                f"{e.device:<25} {e.event:<30} {e.first_time:<22} "
                f"{e.last_time:<22} {e.count:<6} {ack}"
            )
        lines.append(f"\nShowing {len(events)} events")
        return "\n".join(lines)
    except NetBrainError as e:
        return _error_response(e)


# -- Tool 8: get_change_analysis --


@mcp.tool()
async def get_change_analysis(ctx: Context) -> str:
    """Get configuration change analysis for devices.

    Returns:
        Phase 2 status message. The full export workflow is not yet implemented.
    """
    return "Change analysis export workflow planned for Phase 2."


# -- Tool 9: search_devices --


@mcp.tool()
async def search_devices(ctx: Context, hostname: str) -> str:
    """Search for devices by hostname (case-insensitive match).

    Use this to resolve partial or approximate device names before calling
    other tools that require an exact hostname.

    Args:
        hostname: Hostname to search for (case-insensitive).

    Returns:
        Matching devices with hostname, type, and management IP.
    """
    client = _get_client(ctx)
    try:
        devices = await client.search_devices(hostname=hostname)
        if not devices:
            return f"No devices found matching '{hostname}'."
        lines = [
            f"Search results for '{hostname}':",
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
