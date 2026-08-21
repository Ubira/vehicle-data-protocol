# Vehicle Data Protocol Server — Documentation

This folder documents the **Vehicle Data Protocol (VDP) Server**
([apps/vehicle-data-protocol-server](../apps/vehicle-data-protocol-server)), the
component that implements the **VDP-CM Remote** role of the AUTOSAR *Vehicle Data
Protocol* (Foundation R25-11).

The server runs on a **remote ECU** that owns or has local access to vehicle data. It
receives control commands from a central data collection unit (the **VDP-CM Proxy** /
client on an HPC), drives sampling of data points through **DCA Remotes**, buffers the
resulting samples, and streams them back as time-stamped **data messages**.

## Source material

| Source | Location | Content |
|--------|----------|---------|
| Stakeholder requirements | [requirements/stakeholder-requirements.md](../requirements/stakeholder-requirements.md) | What the server must do and why. |
| AUTOSAR RS_VDP | [standards/](../standards) | Requirements on Vehicle Data Protocol (ID 1118). |
| AUTOSAR PRS_VDP | [standards/](../standards) | Vehicle Data Protocol Specification (ID 1119). |

## Architecture views (4+1)

The documentation follows the 4+1 view model. Start with the view that matches your
question:

| View | Read when you want to understand… | Document |
|------|-----------------------------------|----------|
| Logical | Components, responsibilities and their relationships | [logical view/README.md](logical%20view/README.md) |
| Development | Code organisation, modules and build structure | [development view/README.md](development%20view/README.md) |
| Process | Runtime behaviour: concurrency, data flow, sampling/transmission timing | [process view/README.md](process%20view/README.md) |
| Physical | Deployment onto ECUs, HPC and the vehicle bus | [physical view/README.md](physical%20view/README.md) |
| Scenarios | End-to-end command and data-collection flows | [scenarios/README.md](scenarios/README.md) |

## Key concepts at a glance

- **VDP-CM Remote (the server):** implements the protocol, owns the sample buffer, and
  handles the transmission modes.
- **DCA Remote (Data Class Adapter):** attached to the server, accesses data resources
  and implements the sampling modes for its data points.
- **VDP-CM Proxy (the client):** on the HPC; sends control requests and consumes data.
- **VDP Slot ID:** dynamically assigned identifier associating an abstract data point
  with a collection task for its lifetime.
- **Message types:** protocol version (`MT=0`), control (`MT=1`), data (`MT=2`), error
  (`MT=3`).
- **Commands (control):** add configuration (`CT=0`), remove configuration (`CT=1`),
  activation (`CT=2`), trigger (`CT=3`).

> Requirement identifiers such as `[FO_PRS_VDP_00007]` throughout these documents refer
> to the AUTOSAR source specifications for traceability.
