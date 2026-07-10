"""
Finds a Samsung Frame TV on the local network via SSDP (UPnP discovery),
so a fixed/reserved IP isn't strictly required. Falls back to whatever
IP is passed in if discovery doesn't find anything.
"""

import re
import socket

SSDP_ADDR = "239.255.255.250"
SSDP_PORT = 1900
SSDP_MSEARCH = (
    "M-SEARCH * HTTP/1.1\r\n"
    "HOST: 239.255.255.250:1900\r\n"
    'MAN: "ssdp:discover"\r\n'
    "MX: 3\r\n"
    "ST: urn:dial-multiscreen-org:service:dial:1\r\n"
    "\r\n"
).encode()


def discover_frame_tv(timeout: float = 4.0) -> str | None:
    """
    Sends an SSDP M-SEARCH broadcast and returns the IP of the first
    device that looks like a Samsung TV, or None if nothing was found.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(timeout)

    try:
        sock.sendto(SSDP_MSEARCH, (SSDP_ADDR, SSDP_PORT))
        while True:
            try:
                data, addr = sock.recvfrom(4096)
            except socket.timeout:
                return None

            text = data.decode(errors="ignore")
            if "samsung" in text.lower():
                return addr[0]
    finally:
        sock.close()


if __name__ == "__main__":
    ip = discover_frame_tv()
    print(f"Found: {ip}" if ip else "No Samsung TV found on the network.")
