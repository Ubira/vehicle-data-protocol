# VDP Server — C implementation

A C11 implementation of the AUTOSAR **Vehicle Data Protocol (VDP) Server**
(**VDP-CM Remote**), grounded in the repository documentation:

- Stakeholder requirements: [requirements/stakeholder-requirements.md](../../../requirements/stakeholder-requirements.md)
- Architecture (4+1 views): [docs/](../../../docs/README.md)
- AUTOSAR standards: [standards/](../../../standards)

It uses the **same wire format** as the Python implementation
([../python/WIRE_FORMAT.md](../python/WIRE_FORMAT.md)), so the two are interoperable —
the demos of both produce byte-identical output.

## Layout

The modules mirror the [development view](../../../docs/development%20view/development-view.md):

| File | Logical component |
|------|-------------------|
| [include/vdp/vdp_types.h](include/vdp/vdp_types.h) | Constants, enums, domain structs |
| [src/vdp_codec.c](src/vdp_codec.c) | Message Codec (LE reader/writer, `DDLE[UINT]`, timestamps) |
| [src/vdp_core.c](src/vdp_core.c) | Slot table, Sample Buffer, Transmission Scheduler, Data Message Builder |
| [src/vdp_dca.c](src/vdp_dca.c) | DCA Remote Adapter interface + demo DCA |
| [src/vdp_server.c](src/vdp_server.c) | Message Dispatcher, command handlers, Error Reporter, assembly |
| [src/vdp_proxy.c](src/vdp_proxy.c) | Client-side request builder (test/demo helper) |
| [app/main.c](app/main.c) | Runnable demo (scenarios S1–S5) |
| [tests/test_vdp.c](tests/test_vdp.c) | Unit / scenario tests |

## Design

- **No dynamic allocation.** All state lives in fixed-size arrays sized by the
  `VDP_MAX_*` macros in [vdp_types.h](include/vdp/vdp_types.h); suitable for an embedded
  Classic Platform ECU.
- **Bounds-checked codec.** The reader latches an `error` flag on any out-of-bounds
  read, which the dispatcher turns into a protocol error message (`PEC=3`).
- **Single-threaded / deterministic.** `vdp_server_receive()` handles an inbound
  message; `vdp_server_tick(now_ms)` advances time. Output is delivered through a send
  callback and time is read through a clock callback (see
  [vdp_server.h](include/vdp/vdp_server.h)).

## Build & test (CMake)

```powershell
cd apps/vehicle-data-protocol-server/c
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

Run the demo:

```powershell
./build/vdp_demo        # or build/Debug/vdp_demo.exe with the MSVC generator
```

### Building without CMake (MSVC)

```powershell
cl /nologo /W4 /I include app/main.c src/*.c /Fe:vdp_demo.exe
```
