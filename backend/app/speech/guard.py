"""Block outbound connections outside loopback and count rejected attempts."""

import ipaddress
import os
import socket
import threading

_LOCAL_NAMES = {"localhost", "localhost.localdomain", "ip6-localhost", "ip6-loopback"}
_lock = threading.Lock()
_blocked = 0
_installed = False


class ExternalConnectionBlocked(OSError):
    pass


def is_loopback(address) -> bool:
    if isinstance(address, (str, bytes)):
        return True  # Unix domain socket path.
    if not isinstance(address, tuple) or not address:
        return False
    host = address[0]
    if host in _LOCAL_NAMES:
        return True
    try:
        ip = ipaddress.ip_address(str(host).split("%")[0])
    except ValueError:
        return False
    if ip.version == 6 and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_loopback


def _count_and_raise(address) -> None:
    global _blocked
    with _lock:
        _blocked += 1
    raise ExternalConnectionBlocked(f"outbound connection to {address!r} blocked by provenance guard")


def install() -> None:
    global _installed
    if _installed or os.getenv("PROVENANCE_GUARD", "1") == "0":
        return
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_create = socket.create_connection

    def connect(self, address):
        if not is_loopback(address):
            _count_and_raise(address)
        return original_connect(self, address)

    def connect_ex(self, address):
        if not is_loopback(address):
            _count_and_raise(address)
        return original_connect_ex(self, address)

    def create_connection(address, *args, **kwargs):
        if not is_loopback(address):
            _count_and_raise(address)
        return original_create(address, *args, **kwargs)

    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex
    socket.create_connection = create_connection
    _installed = True


def status() -> dict:
    with _lock:
        return {"enabled": _installed, "blocked_external_connections": _blocked}
