import socket

import pytest

from app.speech import guard


@pytest.mark.parametrize("host", ["127.0.0.1", "::1", "localhost", "::ffff:127.0.0.1"])
def test_loopback_addresses_are_local(host):
    assert guard.is_loopback((host, 11434))
    assert guard.is_loopback("/tmp/some.sock")


@pytest.mark.parametrize("host", ["api.openai.com", "1.1.1.1", "192.168.1.1", "0.0.0.0", "::"])
def test_external_addresses_are_not_local(host):
    assert not guard.is_loopback((host, 443))


@pytest.mark.parametrize("operation", ["create_connection", "connect", "connect_ex"])
def test_install_blocks_and_counts_external_connect(operation):
    guard.install()
    before = guard.status()["blocked_external_connections"]
    with socket.socket() as sock, pytest.raises(guard.ExternalConnectionBlocked):
        if operation == "create_connection":
            socket.create_connection(("1.1.1.1", 53), timeout=0.2)
        else:
            getattr(sock, operation)(("1.1.1.1", 53))
    assert guard.status()["blocked_external_connections"] == before + 1


def test_guard_allows_actual_loopback_connection():
    guard.install()
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        with socket.create_connection(server.getsockname(), timeout=1):
            conn, _ = server.accept()
            conn.close()
