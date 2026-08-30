from __future__ import annotations

import ipaddress
from collections import Counter
from typing import Any

from .models import RuleFinding
from .parsers import (
    parse_show_interfaces_trunk,
    parse_show_ip_interface_brief,
    parse_show_ip_route,
    parse_show_running_config,
    parse_show_vlan_brief,
    split_show_command_outputs,
)


def _normalize_network(value: str) -> str | None:
    try:
        return str(ipaddress.ip_network(value, strict=False))
    except (ValueError, TypeError):
        return None


def _normalize_ip_list(raw_values: Any) -> list[str]:
    if raw_values is None:
        return []

    values = raw_values if isinstance(raw_values, list) else [raw_values]
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        value = value.strip()
        if not value or value.lower() in {"unassigned", "n/a", "none"}:
            continue
        normalized.append(value)

    return normalized


def _normalize_interfaces(raw_interfaces: Any) -> list[dict[str, str]]:
    if raw_interfaces is None:
        return []

    if isinstance(raw_interfaces, dict):
        return [
            {"interface": name, "status": str(status)}
            for name, status in raw_interfaces.items()
            if isinstance(name, str)
        ]

    if isinstance(raw_interfaces, list):
        interfaces: list[dict[str, str]] = []
        for item in raw_interfaces:
            if not isinstance(item, dict):
                continue
            interface = str(item.get("interface", "")).strip()
            status = str(item.get("status", "")).strip()
            if interface:
                interfaces.append({"interface": interface, "status": status or "unknown"})
        return interfaces

    return []


def _normalize_vlan_set(raw_values: Any) -> set[int]:
    values = raw_values if isinstance(raw_values, list) else [raw_values]
    normalized: set[int] = set()
    for value in values:
        if isinstance(value, int):
            normalized.add(value)
            continue
        if isinstance(value, str) and value.strip().isdigit():
            normalized.add(int(value.strip()))
    return normalized


def _normalize_routes(raw_values: Any) -> set[str]:
    if raw_values is None:
        return set()

    values = raw_values if isinstance(raw_values, list) else [raw_values]
    normalized: set[str] = set()

    for value in values:
        if isinstance(value, dict):
            candidate = value.get("prefix") or value.get("network")
            network = _normalize_network(candidate) if isinstance(candidate, str) else None
            if network:
                normalized.add(network)
            continue

        if isinstance(value, str):
            network = _normalize_network(value)
            if network:
                normalized.add(network)

    return normalized


def normalize_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    """Normalize heterogeneous evidence into deterministic checker inputs."""

    normalized: dict[str, Any] = dict(evidence) if isinstance(evidence, dict) else {}

    show_outputs = normalized.get("show_outputs")
    show_map: dict[str, str] = {}

    if isinstance(show_outputs, str):
        show_map = split_show_command_outputs(show_outputs)
    elif isinstance(show_outputs, dict):
        show_map = {
            str(command).strip().lower(): str(output)
            for command, output in show_outputs.items()
            if isinstance(command, str) and isinstance(output, str)
        }

    parsed_interfaces: list[dict[str, str]] = []
    parsed_ip_addresses: list[str] = []
    parsed_vlans: set[int] = set()
    parsed_routes: set[str] = set()
    parsed_trunk_vlans: set[int] = set()

    if "show ip interface brief" in show_map:
        brief = parse_show_ip_interface_brief(show_map["show ip interface brief"])
        parsed_interfaces.extend(
            {"interface": item["interface"], "status": item["status"]}
            for item in brief
            if "interface" in item
        )
        parsed_ip_addresses.extend(item["ip_address"] for item in brief if item.get("ip_address"))

    if "show vlan brief" in show_map:
        parsed_vlans.update(parse_show_vlan_brief(show_map["show vlan brief"]))

    if "show interfaces trunk" in show_map:
        trunk_data = parse_show_interfaces_trunk(show_map["show interfaces trunk"])
        for vlan_list in trunk_data.get("allowed_vlans_by_port", {}).values():
            parsed_trunk_vlans.update(vlan_list)

    if "show ip route" in show_map:
        parsed_routes.update(parse_show_ip_route(show_map["show ip route"]))

    if "show running-config" in show_map:
        running = parse_show_running_config(show_map["show running-config"])
        parsed_vlans.update(running.get("existing_vlans", []))
        parsed_routes.update(running.get("routes", []))
        parsed_interfaces.extend(running.get("interfaces", []))
        parsed_trunk_vlans.update(running.get("trunk_allowed_vlans", []))
        if running.get("default_gateway") and not normalized.get("default_gateway"):
            normalized["default_gateway"] = running["default_gateway"]

    normalized["ip_addresses"] = _normalize_ip_list(normalized.get("ip_addresses")) + _normalize_ip_list(parsed_ip_addresses)
    normalized["interfaces"] = _normalize_interfaces(normalized.get("interfaces")) + _normalize_interfaces(parsed_interfaces)

    existing_vlans = _normalize_vlan_set(normalized.get("existing_vlans"))
    existing_vlans.update(parsed_vlans)
    normalized["existing_vlans"] = sorted(existing_vlans)

    trunk_allowed_vlans = _normalize_vlan_set(normalized.get("trunk_allowed_vlans"))
    trunk_allowed_vlans.update(parsed_trunk_vlans)
    normalized["trunk_allowed_vlans"] = sorted(trunk_allowed_vlans)

    normalized["required_vlans"] = sorted(_normalize_vlan_set(normalized.get("required_vlans")))
    normalized["required_trunk_vlans"] = sorted(_normalize_vlan_set(normalized.get("required_trunk_vlans")))

    routes = _normalize_routes(normalized.get("routes"))
    routes.update(parsed_routes)
    routes.update(_normalize_routes(normalized.get("routing_table")))
    normalized["routes"] = sorted(routes)

    normalized["required_routes"] = sorted(_normalize_routes(normalized.get("required_routes")))

    if "interface_status" in normalized and not normalized.get("interfaces"):
        normalized["interfaces"] = _normalize_interfaces(normalized.get("interface_status"))

    return normalized


def check_duplicate_ip_addresses(evidence: dict[str, Any]) -> RuleFinding:
    """Detect duplicate IP addresses in provided host/interface evidence."""

    raw_ips = evidence.get("ip_addresses", [])
    ips = []
    invalid = []
    for value in raw_ips:
        try:
            ips.append(str(ipaddress.ip_address(value)))
        except ValueError:
            invalid.append(value)

    if not raw_ips:
        return RuleFinding(
            rule="duplicate_ip_check",
            status="INSUFFICIENT_DATA",
            severity="LOW",
            message="No IP address inventory was provided.",
            evidence={"ip_addresses": raw_ips},
            recommendation="Provide host/interface IP address evidence to run duplicate IP checks.",
        )

    if not ips:
        return RuleFinding(
            rule="duplicate_ip_check",
            status="WARNING",
            severity="MEDIUM",
            message="Provided IP address evidence is malformed.",
            evidence={"invalid_ip_values": invalid},
            recommendation="Correct malformed IP values before using duplicate IP checks.",
        )

    counts = Counter(ips)
    duplicates = {ip: count for ip, count in counts.items() if count > 1}

    if duplicates:
        return RuleFinding(
            rule="duplicate_ip_check",
            status="FAIL",
            severity="HIGH",
            message="Duplicate IP addresses were detected.",
            evidence={"duplicates": duplicates},
            recommendation="Assign unique IP addresses to each host/interface.",
        )

    return RuleFinding(
        rule="duplicate_ip_check",
        status="PASS",
        severity="LOW",
        message="No duplicate IP addresses were found in provided evidence.",
        evidence={"checked_ip_count": len(ips), "invalid_ip_values": invalid},
        recommendation="Continue monitoring for address conflicts when adding new hosts.",
    )


def check_subnet_mask_and_host_relationship(evidence: dict[str, Any]) -> RuleFinding:
    """Validate host IP/subnet mask consistency and host-network relationship."""

    host_ip = evidence.get("host_ip")
    subnet_mask = evidence.get("subnet_mask")
    gateway = evidence.get("default_gateway")

    if not host_ip or not subnet_mask:
        return RuleFinding(
            rule="subnet_mask_host_check",
            status="INSUFFICIENT_DATA",
            severity="LOW",
            message="Host IP or subnet mask is missing.",
            evidence={"host_ip": host_ip, "subnet_mask": subnet_mask},
            recommendation="Provide both host IP and subnet mask to validate subnet relationships.",
        )

    try:
        network = ipaddress.ip_network(f"{host_ip}/{subnet_mask}", strict=False)
        host_address = ipaddress.ip_address(host_ip)
    except ValueError:
        return RuleFinding(
            rule="subnet_mask_host_check",
            status="WARNING",
            severity="MEDIUM",
            message="Host IP or subnet mask is malformed.",
            evidence={"host_ip": host_ip, "subnet_mask": subnet_mask},
            recommendation="Correct host IP and subnet mask formatting.",
        )

    if host_address == network.network_address or host_address == network.broadcast_address:
        return RuleFinding(
            rule="subnet_mask_host_check",
            status="FAIL",
            severity="HIGH",
            message="Host IP is not a valid usable host address for the configured subnet.",
            evidence={"host_ip": host_ip, "subnet": str(network)},
            recommendation="Assign a valid host IP within the subnet range.",
        )

    if gateway:
        try:
            gateway_ip = ipaddress.ip_address(gateway)
        except ValueError:
            return RuleFinding(
                rule="subnet_mask_host_check",
                status="WARNING",
                severity="MEDIUM",
                message="Default gateway value is malformed.",
                evidence={"default_gateway": gateway},
                recommendation="Correct default gateway formatting.",
            )

        if gateway_ip not in network:
            return RuleFinding(
                rule="subnet_mask_host_check",
                status="FAIL",
                severity="HIGH",
                message="Default gateway does not belong to the host subnet.",
                evidence={"host_subnet": str(network), "default_gateway": gateway},
                recommendation="Configure a default gateway inside the host subnet.",
            )

    return RuleFinding(
        rule="subnet_mask_host_check",
        status="PASS",
        severity="LOW",
        message="Host IP/subnet mask relationship is valid.",
        evidence={"host_subnet": str(network), "host_ip": host_ip},
        recommendation="No subnet mask correction required based on provided data.",
    )


def check_default_gateway_mismatch(evidence: dict[str, Any]) -> RuleFinding:
    """Check if default gateway belongs to the host subnet."""

    host_ip = evidence.get("host_ip")
    subnet_mask = evidence.get("subnet_mask")
    gateway = evidence.get("default_gateway")

    if not gateway:
        return RuleFinding(
            rule="gateway_subnet_check",
            status="INSUFFICIENT_DATA",
            severity="LOW",
            message="Default gateway was not provided.",
            evidence={"default_gateway": gateway},
            recommendation="Provide a host default gateway for deterministic validation.",
        )

    if not host_ip or not subnet_mask:
        return RuleFinding(
            rule="gateway_subnet_check",
            status="INSUFFICIENT_DATA",
            severity="LOW",
            message="Host IP or subnet mask is missing for gateway validation.",
            evidence={"host_ip": host_ip, "subnet_mask": subnet_mask},
            recommendation="Provide host IP and subnet mask along with default gateway.",
        )

    try:
        network = ipaddress.ip_network(f"{host_ip}/{subnet_mask}", strict=False)
        gateway_ip = ipaddress.ip_address(gateway)
    except ValueError:
        return RuleFinding(
            rule="gateway_subnet_check",
            status="WARNING",
            severity="MEDIUM",
            message="Gateway, host IP, or subnet mask format is invalid.",
            evidence={"host_ip": host_ip, "subnet_mask": subnet_mask, "default_gateway": gateway},
            recommendation="Fix malformed addressing values before gateway checks.",
        )

    if gateway_ip not in network:
        return RuleFinding(
            rule="gateway_subnet_check",
            status="FAIL",
            severity="HIGH",
            message="Default gateway is outside the host subnet.",
            evidence={"host_subnet": str(network), "default_gateway": gateway},
            recommendation="Set the host default gateway to an IP in the same subnet.",
        )

    return RuleFinding(
        rule="gateway_subnet_check",
        status="PASS",
        severity="LOW",
        message="Default gateway is in the host subnet.",
        evidence={"host_subnet": str(network), "default_gateway": gateway},
        recommendation="No gateway subnet correction required.",
    )


def check_interface_administrative_state(evidence: dict[str, Any]) -> RuleFinding:
    """Detect administratively down interfaces in supplied evidence."""

    interfaces = evidence.get("interfaces", [])
    required_interfaces = evidence.get("required_interfaces")
    required_set = set(required_interfaces or [])

    if not interfaces:
        return RuleFinding(
            rule="interface_admin_down_check",
            status="INSUFFICIENT_DATA",
            severity="LOW",
            message="Interface status evidence is missing.",
            evidence={"interfaces": interfaces},
            recommendation="Provide interface status details to run this check.",
        )

    down_interfaces: list[str] = []
    unknown_interfaces: list[str] = []

    filtered_interfaces = [
        interface
        for interface in interfaces
        if not required_set or interface.get("interface") in required_set
    ]

    if required_set and not filtered_interfaces:
        return RuleFinding(
            rule="interface_admin_down_check",
            status="INSUFFICIENT_DATA",
            severity="LOW",
            message="Required interfaces were not found in interface status evidence.",
            evidence={"required_interfaces": sorted(required_set)},
            recommendation="Provide status output for required interfaces.",
        )

    for interface in filtered_interfaces:
        name = interface.get("interface", "unknown")
        status = str(interface.get("status", "")).strip().lower()

        if "administratively down" in status:
            down_interfaces.append(name)
            continue

        if "up" in status or status == "connected":
            continue

        unknown_interfaces.append(name)

    if down_interfaces:
        return RuleFinding(
            rule="interface_admin_down_check",
            status="FAIL",
            severity="MEDIUM",
            message="One or more interfaces are administratively down.",
            evidence={"administratively_down": sorted(down_interfaces)},
            recommendation="Enable required interfaces using 'no shutdown'.",
        )

    if unknown_interfaces:
        return RuleFinding(
            rule="interface_admin_down_check",
            status="WARNING",
            severity="LOW",
            message="One or more interface states are unknown.",
            evidence={"unknown_status_interfaces": sorted(unknown_interfaces)},
            recommendation="Collect complete interface state output.",
        )

    return RuleFinding(
        rule="interface_admin_down_check",
        status="PASS",
        severity="LOW",
        message="No administratively down interfaces detected in provided evidence.",
        evidence={"checked_interfaces": [i.get("interface") for i in filtered_interfaces]},
        recommendation="No interface administrative changes are required.",
    )


def check_missing_vlan(evidence: dict[str, Any]) -> RuleFinding:
    """Check required VLANs against observed VLAN evidence."""

    required_vlans = set(evidence.get("required_vlans", []))
    existing_vlans = set(evidence.get("existing_vlans", []))

    if not required_vlans:
        return RuleFinding(
            rule="missing_vlan_check",
            status="INSUFFICIENT_DATA",
            severity="LOW",
            message="No required VLAN list was provided.",
            evidence={"required_vlans": sorted(required_vlans)},
            recommendation="Specify required VLAN IDs to run VLAN presence checks.",
        )

    if not existing_vlans:
        return RuleFinding(
            rule="missing_vlan_check",
            status="INSUFFICIENT_DATA",
            severity="LOW",
            message="No VLAN evidence is available from structured data or CLI output.",
            evidence={"existing_vlans": sorted(existing_vlans)},
            recommendation="Provide VLAN evidence from 'show vlan brief' or running-config.",
        )

    missing_vlans = sorted(required_vlans - existing_vlans)
    if missing_vlans:
        return RuleFinding(
            rule="missing_vlan_check",
            status="FAIL",
            severity="MEDIUM",
            message="Required VLANs are missing from observed VLAN configuration.",
            evidence={"missing_vlans": missing_vlans, "existing_vlans": sorted(existing_vlans)},
            recommendation="Create and propagate the missing VLANs where required.",
        )

    required_trunk_vlans = set(evidence.get("required_trunk_vlans", []))
    trunk_allowed_vlans = set(evidence.get("trunk_allowed_vlans", []))
    if required_trunk_vlans and trunk_allowed_vlans:
        trunk_missing = sorted(required_trunk_vlans - trunk_allowed_vlans)
        if trunk_missing:
            return RuleFinding(
                rule="missing_vlan_check",
                status="FAIL",
                severity="MEDIUM",
                message="Required VLANs are not allowed on the observed trunk links.",
                evidence={
                    "missing_trunk_vlans": trunk_missing,
                    "trunk_allowed_vlans": sorted(trunk_allowed_vlans),
                },
                recommendation="Allow required VLANs on relevant trunk interfaces.",
            )

    return RuleFinding(
        rule="missing_vlan_check",
        status="PASS",
        severity="LOW",
        message="All required VLANs are present in provided evidence.",
        evidence={"required_vlans": sorted(required_vlans)},
        recommendation="No VLAN additions required for listed VLANs.",
    )


def check_missing_route(evidence: dict[str, Any]) -> RuleFinding:
    """Check required routes against observed routing evidence."""

    required_routes = set(evidence.get("required_routes", []))
    routes = set(evidence.get("routes", []))

    if not required_routes:
        return RuleFinding(
            rule="missing_route_check",
            status="INSUFFICIENT_DATA",
            severity="LOW",
            message="No required route list was provided.",
            evidence={"required_routes": sorted(required_routes)},
            recommendation="Specify required route prefixes to run route checks.",
        )

    if not routes:
        return RuleFinding(
            rule="missing_route_check",
            status="INSUFFICIENT_DATA",
            severity="LOW",
            message="Routing table evidence is missing.",
            evidence={"routes": sorted(routes)},
            recommendation="Provide routing evidence from 'show ip route' or structured route data.",
        )

    missing_routes = sorted(required_routes - routes)
    if missing_routes:
        return RuleFinding(
            rule="missing_route_check",
            status="FAIL",
            severity="HIGH",
            message="Required routes are missing from routing evidence.",
            evidence={"missing_routes": missing_routes, "observed_routes": sorted(routes)},
            recommendation="Add or advertise missing routes toward target networks.",
        )

    return RuleFinding(
        rule="missing_route_check",
        status="PASS",
        severity="LOW",
        message="All required routes are present in provided routing evidence.",
        evidence={"required_routes": sorted(required_routes)},
        recommendation="No route additions required for listed prefixes.",
    )
