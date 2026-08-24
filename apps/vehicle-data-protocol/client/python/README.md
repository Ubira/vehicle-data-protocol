# VDP Client — Python implementation

A Python implementation of the AUTOSAR **Vehicle Data Protocol (VDP) Client**, i.e. the
**VDP-CM Proxy** role (Foundation R25-11) — the requesting side that runs on the HPC /
central ECU. It sends control commands to the [VDP Server](../../server/README.md)
and consumes the time-stamped data it streams back.

It is grounded in the repository documentation:

- Stakeholder requirements: [requirements/stakeholder-requirements.md](../../../../requirements/stakeholder-requirements.md)
- Architecture (4+1 views): [docs/](../../../../docs/README.md)
- AUTOSAR standards: [standards/](../../../../standards)

The client **shares the wire format** of the server (see the server's
[WIRE_FORMAT.md](../../server/python/WIRE_FORMAT.md)), so the two
interoperate — the interop tests drive the real server end-to-end. The shared protocol
core lives in the [vdp_common](../../common/python/README.md)
package, which both the client and the server depend on so they cannot drift apart.

## Layout

| Module | Responsibility |
|--------|----------------|
| [vdp_client/codec.py](vdp_client/codec.py) | Re-exports the shared codec (`vdp_common.codec`) |
| [vdp_client/constants.py](vdp_client/constants.py) | Re-exports the shared protocol constants (`vdp_common.constants`) |
| [vdp_client/header.py](vdp_client/header.py) | Re-exports the shared base header (`vdp_common.header`) |
| [vdp_client/messages.py](vdp_client/messages.py) | Re-exports the shared request builders (`vdp_common.builders`) |
| [vdp_client/decode.py](vdp_client/decode.py) | Decoders: version/control responses, data messages, error messages |
| [vdp_client/client.py](vdp_client/client.py) | `VdpClient` — sequence-counter management, slot registry, high-level API |
| [vdp_client/transport.py](vdp_client/transport.py) | Loopback / TCP client transports (on the shared `vdp_common.transport` base) |
| [vdp_client/__main__.py](vdp_client/__main__.py) | Runnable demo driving the real server over a loopback |

The protocol-level modules (codec, constants, header, request builders) are thin
re-exports of [vdp_common](../../common/python/README.md); the
files that are genuinely client-specific are `decode.py`, `client.py` and the
client-side `transport.py`.

## Quick start

```python
from vdp_client import VdpClient, DpConfig
from vdp_client.constants import TimestampResolution
from vdp_client.transport import CallbackTransport

client = VdpClient(CallbackTransport(send_to_server))   # your transport
client.on_data = lambda dm: print(dm.samples)

client.request_version()
client.add_config(dca_rem_id=1, dps=[
    DpConfig(slot_id=1, cyclic=True, sct_ms=100, init_act=True,
             tres=TimestampResolution.MS_10),
])
client.trigger_transmission()          # pull buffered data

# Feed every message the server sends you back into the client:
client.handle(incoming_bytes)
```

The client manages the 5-bit control sequence counter (`CON_SQ_CT`), records each
slot's timestamp resolution from the add requests it sends, and uses it to reconstruct
absolute sample times when decoding data messages. On a sequence-counter error message
it automatically resynchronises to the server's expected value.

## Run the demo

```powershell
cd apps/vehicle-data-protocol/client/python
python -m vdp_client
```

The demo locates the sibling server package and runs scenarios S1–S3 across both apps.

## Run the tests

```powershell
cd apps/vehicle-data-protocol/client/python
python -m pip install -e ../../common/python
python -m pip install -e .[test]
python -m pytest
```

Unit tests cover codec round-trips, request building and response decoding. The
interop tests ([tests/test_interop.py](tests/test_interop.py)) wire the client to the
real VDP Server and exercise scenarios S1–S13; they are skipped automatically if the
server package is not present.
