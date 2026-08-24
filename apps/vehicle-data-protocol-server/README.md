# Vehicle Data Protocol (VDP) Server

Implementations of the AUTOSAR **Vehicle Data Protocol Server** — the **VDP-CM Remote**
role (Foundation R25-11). The server runs on a remote ECU, receives control commands
from the central data collection unit (the VDP-CM Proxy on an HPC), drives sampling of
data points through **DCA Remotes**, buffers the resulting samples, and streams them back
as time-stamped data messages.

The code is grounded in the repository documentation and requirements:

- Stakeholder requirements: [requirements/stakeholder-requirements.md](../../requirements/stakeholder-requirements.md)
- Architecture (4+1 views): [docs/](../../docs/README.md)
- AUTOSAR standards: [standards/](../../standards)

## Two implementations

| Folder | Language | Build | Tests |
|--------|----------|-------|-------|
| [python/](python/README.md) | Python 3.10+ | `pip install -e .[test]` | `pytest` (25 tests) |
| [c/](c/README.md) | C11 | CMake / MSVC | `ctest` |

Both follow the module structure of the
[development view](../../docs/development%20view/development-view.md) and share a single
wire format documented in [python/WIRE_FORMAT.md](python/WIRE_FORMAT.md). Their demos
produce byte-identical output, so a Proxy can talk to either.

## What is implemented

- Protocol version handshake (`MT=0`) — scenario S1.
- Control commands (`MT=1`): add / remove dynamic configuration, activation, trigger
  (`CT=0..3`) — scenarios S2–S10.
- Data messages (`MT=2`) with reference + chained relative timestamps, data sequence
  counter, and embedded asynchronous errors — scenarios S6–S9, S13.
- Error messages (`MT=3`) with protocol error codes and control-sequence-counter
  validation — scenarios S11, S12.
- Sampling modes (cyclic / on-change / on-request) decoupled from transmission modes
  (cyclic / on-sampling / on-request / default), with MTDT and MSDT rate limiting.
- DCA Remote adapter interface with a demo DCA.

See each subfolder's README for how to build, test and run the demo.
