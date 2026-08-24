"""Shared test fixtures: a deterministic server driven by a fake clock."""

import pytest

from vdp_server.dca import DemoDcaRemote
from vdp_server.server import ServerConfig, VdpServer
from vdp_server.transport import CallbackTransport


class Harness:
    def __init__(self, server, received, clock):
        self.server = server
        self.received = received
        self._clock = clock

    def advance(self, ms: int) -> None:
        self._clock["ms"] += ms
        self.server.tick()

    def now(self) -> int:
        return self._clock["ms"]

    def pop_all(self) -> list:
        out = list(self.received)
        self.received.clear()
        return out


@pytest.fixture
def harness():
    clock = {"ms": 0}
    received: list = []
    config = ServerConfig(mtdt_ms=0, msdt_ms=0)  # disable rate limits for determinism
    transport = CallbackTransport(config.max_message_size, received.append)
    server = VdpServer(transport, config=config, clock_ms=lambda: clock["ms"])
    server.register_dca(DemoDcaRemote(dca_rem_id=1))
    return Harness(server, received, clock)
