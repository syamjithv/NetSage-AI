from __future__ import annotations

import ipaddress
import re
from typing import Any


def split_show_command_outputs(raw_output: str) -> dict[str, str]:
    """Split combined Cisco CLI text into command -> output blocks."""

    if not isinstance(raw_output, str) or not raw_output.strip():
        return {}

    blocks: dict[str, list[str]] = {}
    current_command: str | None = None

    for line in raw_output.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("show "):
            current_command = stripped.lower()
            blocks.setdefault(current_command, [])
            continue

        if current_command is not None:
            blocks[current_command].append(line)

    return {command: "\n".join(lines).strip() for command, lines in blocks.items() if lines}


def parse_show_ip_interface_brief(output: str) -> list[dict[str, str]]:
    """Parse 'show ip interface brief' for interface state and IP values."""

    interfaces: list[dict[str, str]] = []
    if not isinstance(output, str) or not output.strip():
        return interfaces

    for line in output.splitlines():
        stripped = line.strip()
        if not stripped or stripped.lower().startswith("interface"):
            continue

        parts = stripped.split()
        if len(parts) < 6:
            continue

        interface = parts[0]
        ip_address = parts[1]
        protocol = parts[-1]
        status = " ".join(parts[4:-1])

        interfaces.append(
            {
                "interface": interface,
                "ip_address": ip_address,
                "status": status,
                "protocol": protocol,
            }
        )

    return interfaces


def parse_show_vlan_brief(output: str) -> list[int]:
    """Parse 'show vlan brief' for VLAN IDs."""

    vlan_ids: list[int] = []
    if not isinstance(output, str) or not output.strip():
        return vlan_ids

    for line in output.splitlines():
        match = re.match(r"^\s*(\d+)\s+\S+\s+\S+", line)
        if not match:
            continue

        try:
            vlan_ids.append(int(match.group(1)))
        except ValueError:
            continue

    return vlan_ids


def parse_vlan_list(vlan_expr: str) -> list[int]:
    """Parse Cisco VLAN list expression such as '1,10,20-22'."""

    vlan_ids: set[int] = set()
    if not isinstance(vlan_expr, str) or not vlan_expr.strip():
        return []

    for token in vlan_expr.split(","):
        token = token.strip()
        if not token:
            continue

        if "-" in token:
            start_str, _, end_str = token.partition("-")
            if not start_str.isdigit() or not end_str.isdigit():
                continue
            start, end = int(start_str), int(end_str)
            if start > end:
                start, end = end, start
            vlan_ids.update(range(start, end + 1))
            continue

        if token.isdigit():
            vlan_ids.add(int(token))

    return sorted(vlan_ids)


def parse_show_interfaces_trunk(output: str) -> dict[str, Any]:
    """Parse trunk output for native and allowed VLAN details."""

    if not isinstance(output, str) or not output.strip():
        return {"native_vlans_by_port": {}, "allowed_vlans_by_port": {}}

    native_vlans_by_port: dict[str, int] = {}
    allowed_vlans_by_port: dict[str, list[int]] = {}

    lines = output.splitlines()
    in_allowed_section = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            in_allowed_section = False
            continue

        if stripped.lower().startswith("port mode"):
            continue

        if stripped.lower().startswith("port vlans allowed on trunk"):
            in_allowed_section = True
            continue

        if in_allowed_section:
            parts = stripped.split(None, 1)
            if len(parts) != 2:
                continue
            port, vlan_expr = parts
            allowed_vlans_by_port[port] = parse_vlan_list(vlan_expr)
            continue

        parts = stripped.split()
        if len(parts) >= 5 and parts[0].lower().startswith(("gi", "fa", "te", "po", "eth", "vlan")):
            if parts[-1].isdigit():
                native_vlans_by_port[parts[0]] = int(parts[-1])

    return {
        "native_vlans_by_port": native_vlans_by_port,
        "allowed_vlans_by_port": allowed_vlans_by_port,
    }


def parse_show_ip_route(output: str) -> list[str]:
    """Parse 'show ip route' and return CIDR prefixes."""

    routes: set[str] = set()
    if not isinstance(output, str) or not output.strip():
        return []

    for prefix in re.findall(r"\b(\d{1,3}(?:\.\d{1,3}){3}/\d{1,2})\b", output):
        try:
            routes.add(str(ipaddress.ip_network(prefix, strict=False)))
        except ValueError:
            continue

    return sorted(routes)


def parse_show_running_config(output: str) -> dict[str, Any]:
    """Parse selected running-config fields used by deterministic checks."""

    if not isinstance(output, str) or not output.strip():
        return {
            "existing_vlans": [],
            "routes": [],
            "default_gateway": None,
            "interfaces": [],
            "trunk_allowed_vlans": [],
        }

    existing_vlans: set[int] = set()
    routes: set[str] = set()
    default_gateway: str | None = None
    interfaces: list[dict[str, str]] = []
    trunk_allowed_vlans: set[int] = set()

    current_interface: dict[str, str] | None = None

    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        vlan_match = re.match(r"^vlan\s+(\d+)$", stripped)
        if vlan_match:
            try:
                existing_vlans.add(int(vlan_match.group(1)))
            except ValueError:
                pass
            continue

        route_match = re.match(r"^ip route\s+(\S+)\s+(\S+)\s+(\S+)", stripped)
        if route_match:
            network, mask, _next_hop = route_match.groups()
            try:
                routes.add(str(ipaddress.ip_network(f"{network}/{mask}", strict=False)))
            except ValueError:
                pass
            continue

        default_gateway_match = re.match(r"^ip default-gateway\s+(\S+)", stripped)
        if default_gateway_match:
            default_gateway = default_gateway_match.group(1)
            continue

        interface_match = re.match(r"^interface\s+(\S+)", stripped)
        if interface_match:
            if current_interface:
                interfaces.append(current_interface)
            current_interface = {"interface": interface_match.group(1), "status": "unknown"}
            continue

        if current_interface is None:
            continue

        if stripped == "shutdown":
            current_interface["status"] = "administratively down"
            continue

        if stripped == "no shutdown":
            if current_interface.get("status") == "unknown":
                current_interface["status"] = "up"
            continue

        access_vlan_match = re.match(r"^switchport access vlan\s+(\d+)$", stripped)
        if access_vlan_match:
            try:
                existing_vlans.add(int(access_vlan_match.group(1)))
            except ValueError:
                pass
            continue

        allowed_vlan_match = re.match(r"^switchport trunk allowed vlan\s+(.+)$", stripped)
        if allowed_vlan_match:
            trunk_allowed_vlans.update(parse_vlan_list(allowed_vlan_match.group(1)))

    if current_interface:
        interfaces.append(current_interface)

    return {
        "existing_vlans": sorted(existing_vlans),
        "routes": sorted(routes),
        "default_gateway": default_gateway,
        "interfaces": interfaces,
        "trunk_allowed_vlans": sorted(trunk_allowed_vlans),
    }
