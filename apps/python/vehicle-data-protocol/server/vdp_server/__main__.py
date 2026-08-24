"""Runnable demo: exercises scenarios S1-S3 from the docs against a loopback transport.

Run with::

    python -m vdp_server
"""

from __future__ import annotations

from . import proxy
from .constants import MessageType, TimestampResolution
from .dca import DemoDcaRemote
from .server import ServerConfig, VdpServer
from .transport import CallbackTransport


def main() -> None:
    clock = {"ms": 0}
    received: list[bytes] = []

    transport = CallbackTransport(ServerConfig().max_message_size, received.append)
    server = VdpServer(transport, clock_ms=lambda: clock["ms"])
    server.register_dca(DemoDcaRemote(dca_rem_id=1))

    def describe(message: bytes) -> str:
        mt = MessageType(message[0] & 0x03)
        return f"{mt.name:8} {message.hex()}"

    def drain() -> None:
        while received:
            print("  S->P:", describe(received.pop(0)))

    print("S1: query protocol version")
    server.receive(proxy.version_request())
    drain()

    print("\nS2/S3: add a cyclic slot with initial activation ON")
    add = proxy.add_config(
        con_sq_ct=1,
        dca_rem_id=1,
        dps=[
            proxy.DpConfig(
                slot_id=1,
                cyclic=True,
                sct_ms=100,
                init_act=True,
                tres=TimestampResolution.MS_10,
            )
        ],
    )
    server.receive(add)
    drain()

    print("\nRun 500 ms of cyclic sampling, then pull the buffered data")
    for _ in range(5):
        clock["ms"] += 100
        server.tick()
    # Transmission trigger to flush the buffer (TX_TRIG=1, no slots).
    server.receive(proxy.trigger(con_sq_ct=2, tx_trigger=True, slot_ids=[]))
    drain()

    print("\nDeactivate slot 1")
    server.receive(proxy.activation(con_sq_ct=3, activate=False, slot_ids=[1]))
    drain()


if __name__ == "__main__":
    main()
