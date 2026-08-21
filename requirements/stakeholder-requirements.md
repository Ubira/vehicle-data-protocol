# Stakeholder Requirements — Vehicle Data Protocol Server

## 1. Purpose and Scope

This document captures the stakeholder requirements for the **Vehicle Data Protocol
(VDP) Server** implemented in this repository ([apps/vehicle-data-protocol-server](../apps/vehicle-data-protocol-server)).

The VDP Server realises the **VDP-CM Remote** role of the AUTOSAR *Vehicle Data
Protocol* as defined in the standards under [standards/](../standards):

- `AUTOSAR_FO_RS_VDP.pdf` — Requirements on Vehicle Data Protocol (Document ID 1118).
- `AUTOSAR_FO_PRS_VDP.pdf` — Vehicle Data Protocol Specification (Document ID 1119).

The server runs on a **remote ECU** that owns or has local access to vehicle data
resources. It receives control commands from, and streams collected data to, a
central data collection unit (the **VDP-CM Proxy**) located on a High Performance
Computer (HPC). The Proxy/client side is out of scope for this document except where
interaction is required.

> Traceability: requirement identifiers in square brackets (e.g. `[FO_RS_VDP_00003]`,
> `[FO_PRS_VDP_00007]`) refer to the AUTOSAR source documents so that each
> stakeholder need can be traced to the standard it originates from.

## 2. Stakeholders

| Stakeholder | Interest in the VDP Server |
|-------------|----------------------------|
| Central data collection unit (HPC / VDP-CM Proxy) | Dynamically configure, activate and trigger data collection; receive complete, time-stamped data. |
| Remote ECU integrator | Integrate the server with existing ECU software, buses and data sources (DCA Remotes). |
| DCA Remote developers | Provide data-point sampling implementations that the server drives. |
| Vehicle / fleet data engineers | Collect the right data points after production without re-flashing ECUs. |
| Safety & network architects | Ensure the server does not flood the bus or block the ECU CPU. |

## 3. Use Case

| ID | Name | Description |
|----|------|-------------|
| UC_VDP_00001 | Dynamic In-Vehicle Data Collection | Dynamically collect data from ECUs in the vehicle, supporting both push semantics (event/notification based) and pull semantics (get-style). Transmission may happen immediately after sampling or be deferred until a transmission trigger condition is met. |

## 4. Stakeholder Requirements

### 4.1 Protocol conformance and versioning

- **STR-01 — Standard conformance.** The server shall implement the VDP-CM Remote
  behaviour of the AUTOSAR VDP specification (Foundation R25-11).
- **STR-02 — Multi-version support.** The server shall support multiple protocol
  versions so network message versions can be distinguished, and shall answer a
  protocol version request with its main and minor version. `[FO_RS_VDP_00001]`,
  `[FO_PRS_VDP_00023]`
- **STR-03 — Little-endian encoding.** All VDP-specific fields shall be encoded in
  little-endian byte order and reserved bits set to `0`. `[FO_PRS_VDP_00001]`,
  `[FO_PRS_VDP_00138]`

### 4.2 Dynamic configuration of data points

- **STR-04 — Dynamic configuration.** The server shall accept dynamic configuration of
  data points at runtime, assigning each configured data point a dynamic identifier
  (**VDP Slot ID**) supplied by the client. `[FO_RS_VDP_00002]`, `[FO_PRS_VDP_00020..00024]`
- **STR-05 — Add / remove configuration.** The server shall support adding and removing
  data-point dynamic configurations, per data point, per DCA Remote, or globally.
  `[FO_PRS_VDP_00025]`, `[FO_PRS_VDP_00026]`, `[FO_PRS_VDP_00069]`, `[FO_PRS_VDP_00142]`
- **STR-06 — Optional persistency.** The server shall persist configurations in
  non-volatile memory when requested (`PERSIST = 1`) and otherwise keep them in
  volatile memory only. `[FO_PRS_VDP_00051]`, `[FO_PRS_VDP_00052]`

### 4.3 Sampling modes

- **STR-07 — Multiple sampling modes.** The server shall support, per configured data
  point: **cyclic**, **on-change**, **cyclic and on-change**, and **on-request**
  sampling. `[FO_RS_VDP_00003]`, `[FO_PRS_VDP_00056..00062]`
- **STR-08 — Activation control.** The server shall support an initial activation state
  and shall activate or deactivate sampling of individual data points on request.
  `[FO_RS_VDP_00006]`, `[FO_PRS_VDP_00054]`, `[FO_PRS_VDP_00071]`, `[FO_PRS_VDP_00072]`
- **STR-09 — Temporary interruption.** The server shall allow the central ECU to
  temporarily interrupt and resume sampling to minimise impact in irrelevant driving
  situations. `[FO_RS_VDP_00006]`

### 4.4 Transmission modes

- **STR-10 — Multiple transmission modes.** Independently of the sampling mode, the
  server shall support **cyclic**, **on-sampling**, **on-request**, and **default**
  (buffer-condition) transmission of buffered samples. `[FO_RS_VDP_00004]`,
  `[FO_PRS_VDP_00027]`, `[FO_PRS_VDP_00053]`, `[FO_PRS_VDP_00082]`
- **STR-11 — Sampling/transmission decoupling.** The server shall buffer samples and
  decouple sampling in time from transmission. `[FO_PRS_VDP_00096]`

### 4.5 Data integrity and meta data

- **STR-12 — Missing-data detection.** The server shall enable the central ECU to
  detect missing data-point samples, using a per-data-message sequence counter and
  explicit asynchronous error reporting. `[FO_RS_VDP_00005]`, `[FO_PRS_VDP_00092..00095]`
- **STR-13 — Efficient meta data.** The server shall use an efficient representation of
  meta data such as timestamps, using dynamic-length encoded integers (DDLE[UINT]) and
  relative timestamps. `[FO_RS_VDP_00009]`, `[FO_PRS_VDP_00003]`, `[FO_PRS_VDP_00004]`

### 4.6 Control-sequence integrity

- **STR-14 — Control sequence enforcement.** The server shall detect lost control
  messages by validating a 5-bit control message sequence counter and mirroring it in
  responses. `[FO_RS_VDP_00011]`, `[FO_PRS_VDP_00010..00015]`

### 4.7 Error handling

- **STR-15 — Synchronous errors.** The server shall report processing failures to the
  client via not-acknowledge (`ACK = 0`) control responses carrying error codes, and
  via protocol error messages for malformed requests. `[FO_RS_VDP_00010]`,
  `[FO_PRS_VDP_00017]`, `[FO_PRS_VDP_00120]`
- **STR-16 — Asynchronous errors.** The server shall report sampling and buffering
  errors that occur independently of a request inside the data message as asynchronous
  error information. `[FO_PRS_VDP_00105..00118]`

### 4.8 Non-functional constraints

- **STR-17 — Message size limit.** The server shall not emit VDP messages larger than
  the configured maximum message size derived from the underlying transport
  protocol/frame size, and shall not implement its own segmentation. `[FO_PRS_VDP_00040]`
- **STR-18 — Bus protection.** The server shall honour a **Minimum Transmission
  Distance Time (MTDT)** so data messages cannot flood the bus. `[FO_PRS_VDP_00029]`
  (see [standards](../standards) chapter 7)
- **STR-19 — CPU protection.** Sampling shall honour a **Minimum Sampling Distance
  Time (MSDT)** so excessive sampling cannot block the ECU CPU. `[FO_PRS_VDP_00061]`
- **STR-20 — Secured channel (optional).** The server should support transmitting data
  requiring a secured channel (`SEC = 1`) and shall always support unsecured
  transmission (`SEC = 0`). `[FO_PRS_VDP_00043..00046]`

## 5. Assumptions and Constraints

- The remote ECU has local access to the required data resources via DCA Remotes.
- A transport protocol is used when VDP messages exceed the underlying bus frame size;
  VDP itself performs no segmentation. `[FO_PRS_VDP_00040]`
- The protocol is **stateful**; the server maintains per-connection control sequence
  state and per-slot configuration/activation state.

## 6. References

- AUTOSAR_FO_RS_VDP — Requirements on Vehicle Data Protocol, Foundation R25-11.
- AUTOSAR_FO_PRS_VDP — Vehicle Data Protocol Specification, Foundation R25-11.
- Architecture documentation: [docs/](../docs/README.md).
