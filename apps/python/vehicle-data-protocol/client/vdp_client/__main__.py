"""Runnable demo: drives the real VDP Server over an in-process loopback.

Wires this client to the server under ``apps/python/vehicle-data-protocol/server`` and runs
scenarios S1-S3 from ``docs/scenarios``. If the server package cannot be located it
falls back to an encode/decode self-demo.

Run with::

    python -m vdp_client
"""

from __future__ import annotations

import os
import sys

from . import DpConfig, VdpClient
from .constants import TimestampResolution
from .decode import ControlResponse, DataMessage, ErrorMessage, VersionResponse
from .transport import CallbackTransport


def _locate_server() -> bool:
    """Add the sibling server's package folder to ``sys.path`` if present."""
    here = os.path.dirname(os.path.abspath(__file__))
    vdp_root = os.path.abspath(os.path.join(here, "..", ".."))
    server_python = os.path.join(vdp_root, "server")
    if os.path.isdir(os.path.join(server_python, "vdp_server")):
        sys.path.insert(0, server_python)
        return True
    return False


def _print_decoded(decoded) -> None:
    if isinstance(decoded, VersionResponse):
        print(f"  version: main={decoded.main:#04x} minor={decoded.minor:#04x}")
    elif isinstance(decoded, ControlResponse):
        status = "ACK" if decoded.ack else f"NACK {decoded.errors}"
        print(f"  control response CT={decoded.command.name} CON_SQ_CT={decoded.con_sq_ct} {status}")
    elif isinstance(decoded, DataMessage):
        print(f"  data SQ_CT={decoded.seq_ct} REF_TS={decoded.ref_ts_s}s "
              f"samples={len(decoded.samples)} async_errors={len(decoded.async_errors)}")
        for s in decoded.samples:
            print(f"    slot {s.slot_id} @ {s.timestamp_ms} ms = {s.data.hex()}")
    elif isinstance(decoded, ErrorMessage):
        print(f"  error PEC={decoded.pec.name} info={decoded.info.hex()}")


def main() -> None:
    if not _locate_server():
        print("Server package not found; run the client tests for a self-contained demo.")
        return

    from vdp_server.dca import DemoDcaRemote  # type: ignore
    from vdp_server.server import ServerConfig, VdpServer  # type: ignore
    from vdp_server.transport import CallbackTransport as ServerCallbackTransport  # type: ignore

    clock = {"ms": 0}

    # Client -> Server and Server -> Client loopbacks.
    client_holder: dict[str, VdpClient] = {}

    def server_to_client(message: bytes) -> None:
        _print_decoded(client_holder["client"].handle(message))

    server_transport = ServerCallbackTransport(ServerConfig().max_message_size, server_to_client)
    server = VdpServer(server_transport, clock_ms=lambda: clock["ms"])
    server.register_dca(DemoDcaRemote(dca_rem_id=1))

    client = VdpClient(CallbackTransport(lambda msg: server.receive(msg)))
    client_holder["client"] = client

    print("S1: query protocol version")
    client.request_version()

    print("\nS2/S3: add a cyclic slot with initial activation ON")
    client.add_config(
        dca_rem_id=1,
        dps=[DpConfig(slot_id=1, cyclic=True, sct_ms=100, init_act=True,
                      tres=TimestampResolution.MS_10)],
    )

    print("\nRun 500 ms of cyclic sampling, then pull the buffered data")
    for _ in range(5):
        clock["ms"] += 100
        server.tick()
    client.trigger_transmission()

    print("\nDeactivate slot 1")
    client.deactivate([1])


if __name__ == "__main__":
    main()
