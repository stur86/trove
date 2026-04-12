"""
Shared network utility for Trove.

Used by both the setup and app routers to detect the machine's outbound
LAN IP address. Kept in a standalone module so neither router domain
needs to import from the other.
"""
import socket


def get_lan_ip() -> str | None:
    """
    Return the machine's outbound LAN IP address, or None if detection fails.

    Opens a UDP socket toward a public DNS server (8.8.8.8) to determine which
    local interface would handle outbound traffic. No packet is actually sent —
    the connect() call on a UDP socket merely selects the route.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return None
