# VDP Server — Python implementation

A Python implementation of the AUTOSAR **Vehicle Data Protocol (VDP) Server**, i.e. the
**VDP-CM Remote** role (Foundation R25-11). It is grounded in the repository
documentation and requirements:

- Stakeholder requirements: [requirements/stakeholder-requirements.md](../../../requirements/stakeholder-requirements.md)
- Architecture (4+1 views): [docs/](../../../docs/README.md)
- AUTOSAR standards: [standards/](../../../standards)

The module layout deliberately mirrors the
[development view](../../../docs/development%20view/development-view.md).

## Layout

| Module | Logical component | Responsibility |
|--------|-------------------|----------------|
| [vdp_server/codec.py](vdp_server/codec.py) | Message Codec | Little-endian readers/writers, `DDLE[UINT]`, relative timestamps |
| [vdp_server/header.py](vdp_server/header.py) | Message Codec | Base header (`MT` + `ADD`) encode/decode |
| [vdp_server/dispatch.py](vdp_server/dispatch.py) | Message Dispatcher | `MT`/`CT` routing, control sequence counter, error messages |
| [vdp_server/commands/version.py](vdp_server/commands/version.py) | Protocol Version Handler | Version request/response |
| [vdp_server/commands/config.py](vdp_server/commands/config.py) | Configuration Manager | Add/remove dynamic configuration, persistency |
| [vdp_server/commands/activation.py](vdp_server/commands/activation.py) | Activation Controller | Activate/deactivate slots |
| [vdp_server/commands/trigger.py](vdp_server/commands/trigger.py) | Trigger Handler | Sampling & transmission triggers |
| [vdp_server/core/slots.py](vdp_server/core/slots.py) | domain model | Slot table, VDP/collection settings |
| [vdp_server/core/buffer.py](vdp_server/core/buffer.py) | Sample Buffer | Sample aggregation, overflow detection |
| [vdp_server/core/scheduler.py](vdp_server/core/scheduler.py) | Transmission Scheduler | Transmission modes, MTDT, data sequence counter |
| [vdp_server/core/datamsg.py](vdp_server/core/datamsg.py) | Data Message Builder | `REF_TS` + repeated DPI + async errors |
| [vdp_server/error_report.py](vdp_server/error_report.py) | Error Reporter | Error messages (`MT=3`, `PEC`) |
| [vdp_server/dca.py](vdp_server/dca.py) | DCA Remote Adapter | Sampling driver interface + demo stub |
| [vdp_server/transport.py](vdp_server/transport.py) | (infrastructure) | Loopback / TCP transport, `maxMessageSize` |
| [vdp_server/server.py](vdp_server/server.py) | assembly | Wires everything; sampling & tick loop |

`vdp_server/proxy.py` is a small client-side request builder used by the demo and tests
(the full client lives under `apps/vehicle-data-protocol-client`).

## Run the demo

```powershell
cd apps/vehicle-data-protocol-server/python
python -m vdp_server
```

The demo exercises scenarios S1–S5 from
[docs/scenarios](../../../docs/scenarios/scenarios.md) against a loopback transport.

## Run the tests

```powershell
cd apps/vehicle-data-protocol-server/python
python -m pip install -e .[test]
python -m pytest
```

## Design notes

- **Single-threaded and deterministic.** Call `receive(message)` to process an inbound
  control/version message and `tick(now_ms)` to advance time. This mirrors the Classic
  Platform "main function period" model and keeps the whole server unit-testable
  without real concurrency.
- **Decoupled sampling and transmission** (the central principle of the standard):
  DCA Remotes sample into the `SampleBuffer`; the `TransmissionScheduler` decides when
  to emit data messages.
- **Wire format:** the AUTOSAR PDFs are the normative source. Where their exact *bit*
  layout is not reproduced in the in-repo docs, this implementation defines a single
  self-consistent encoding — see [WIRE_FORMAT.md](WIRE_FORMAT.md). The C implementation
  under [../c](../c) uses the **same** wire format so the two are interoperable.
