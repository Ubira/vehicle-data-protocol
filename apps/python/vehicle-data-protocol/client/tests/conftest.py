"""Test fixtures for the VDP client.

Provides:
* ``client_loopback`` — a client whose sent messages are captured (no server).
* ``wired`` — a client wired to the real VDP Server over an in-process loopback, used
  for interoperability tests. Skipped automatically if the server package cannot be
  located under ``apps/python/vehicle-data-protocol/server``.
"""

import os
import sys

import pytest

from vdp_client import VdpClient
from vdp_client.transport import CallbackTransport


def _add_server_to_path() -> bool:
    here = os.path.dirname(os.path.abspath(__file__))
    vdp_root = os.path.abspath(os.path.join(here, "..", ".."))
    server_python = os.path.join(vdp_root, "server")
    if os.path.isdir(os.path.join(server_python, "vdp_server")):
        if server_python not in sys.path:
            sys.path.insert(0, server_python)
        return True
    return False


_HAS_SERVER = _add_server_to_path()


class LoopbackClient:
    """A client plus the list of raw messages it has sent."""

    def __init__(self):
        self.sent: list[bytes] = []
        self.client = VdpClient(CallbackTransport(self.sent.append))


@pytest.fixture
def client_loopback() -> LoopbackClient:
    return LoopbackClient()


class Wired:
    """A client and server connected by two in-process loopbacks."""

    def __init__(self):
        from vdp_server.dca import DemoDcaRemote
        from vdp_server.server import ServerConfig, VdpServer
        from vdp_server.transport import CallbackTransport as ServerTransport

        self.clock = {"ms": 0}
        self.received = []  # decoded messages the client got

        server_transport = ServerTransport(
            ServerConfig().max_message_size, self._server_to_client
        )
        cfg = ServerConfig(mtdt_ms=0, msdt_ms=0)
        self.server = VdpServer(server_transport, config=cfg, clock_ms=lambda: self.clock["ms"])
        self.server.register_dca(DemoDcaRemote(dca_rem_id=1))

        self.client = VdpClient(CallbackTransport(self.server.receive))
        self.client.on_version = self.received.append
        self.client.on_control_response = self.received.append
        self.client.on_data = self.received.append
        self.client.on_error = self.received.append

    def _server_to_client(self, message: bytes) -> None:
        self.client.handle(message)

    def advance(self, ms: int) -> None:
        self.clock["ms"] += ms
        self.server.tick()

    def pop_all(self) -> list:
        out = list(self.received)
        self.received.clear()
        return out


@pytest.fixture
def wired() -> "Wired":
    if not _HAS_SERVER:
        pytest.skip("VDP server package not available for interop tests")
    return Wired()
