# Scenarios — VDP Server

End-to-end scenarios that tie the [logical](../logical%20view/README.md),
[development](../development%20view/README.md), [process](../process%20view/README.md)
and [physical](../physical%20view/README.md) views together. Each scenario is grounded in
the AUTOSAR VDP specification sequences (chapter 6.4) in [standards/](../../standards).

Legend: **P** = VDP-CM Proxy (client, HPC) · **S** = VDP Server (VDP-CM Remote) ·
**D** = DCA Remote.

## S1. Query protocol version

```plantuml
@startuml
participant "VDP-CM Proxy (P)" as P
participant "VDP Server (S)" as S
P -> S : version request (MT=0, no payload)
S -> P : version response (MT=0, main=0x01, minor=0x01)
@enduml
```

Establishes protocol compatibility before configuration. `[FO_PRS_VDP_00020..00023]`

## S2. Add data-point dynamic configurations to one DCA

```plantuml
@startuml
participant "VDP-CM Proxy (P)" as P
participant "VDP Server (S)" as S
P -> S : control ADD (CT=0), CON_SQ_CT=n
note right of P
  payload:
  DCA_REM_DCFG(DCA_REM_ID)
  DP_DCFG(slot=1, SET, COL, [SCT], DCA_REM_DP_DCFG)
  DP_DCFG(slot=2, ...)
end note
S -> S : validate slot IDs, DCA IDs, lengths; store configuration
S -> P : ADD response, CON_SQ_CT=n, ACK=1 (empty payload)
@enduml
```

If any part fails (unknown DCA `0x76`, duplicate slot `0x79`, cyclic not supported
`0x07`, on-change not supported `0x08`, persistency limit `0x78`, …), the server applies
the valid parts and answers `ACK=0` with the affected IDs and error codes.
`[FO_PRS_VDP_00024..00069]`, `[FO_PRS_VDP_00066]`

## S3. Cyclic sampling with initial activation ON

```plantuml
@startuml
participant "VDP-CM Proxy (P)" as P
participant "VDP Server (S)" as S
participant "DCA Remote (D)" as D
P -> S : ADD (slot=1, SCYCLIC=1, SCT=100ms, INIT_ACT=1)
S -> D : activate cyclic sampling of slot 1
loop every SCT (>= MSDT)
  D -> S : sample(slot=1) [buffered]
end
P -> S : activation (CT=2, ACT=0, payload: slot 1)
S -> D : deactivate sampling of slot 1
S -> P : activation response ACK=1
@enduml
```

Cyclic sampling runs independently of incoming messages while the slot is active.
`[FO_PRS_VDP_00061]`, `[FO_PRS_VDP_00054]`, `[FO_PRS_VDP_00072]`

## S4. Cyclic sampling with initial activation OFF

```plantuml
@startuml
participant "VDP-CM Proxy (P)" as P
participant "VDP Server (S)" as S
participant "DCA Remote (D)" as D
P -> S : ADD (slot=1, SCYCLIC=1, SCT=100ms, INIT_ACT=0) [no sampling yet]
P -> S : activation (CT=2, ACT=1, payload: slot 1)
S -> D : start cyclic sampling of slot 1
S -> P : activation response ACK=1
@enduml
```

Sampling starts only after an activation request. `[FO_PRS_VDP_00055]`,
`[FO_PRS_VDP_00071]`

## S5. On-request sampling (pull)

```plantuml
@startuml
participant "VDP-CM Proxy (P)" as P
participant "VDP Server (S)" as S
participant "DCA Remote (D)" as D
P -> S : ADD (slot=5, SCYCLIC=0, SCHANGE=0) [no automatic sampling]
... later ...
P -> S : trigger (CT=3, TX_TRIG=0, payload: slot 5)
S -> P : trigger response ACK=1
S -> D : trigger sampling of slot 5
D -> S : sample(slot=5) [buffered for a later data message]
@enduml
```

With both sampling flags `0`, the data point is sampled only on trigger.
`[FO_PRS_VDP_00085]`, `[FO_PRS_VDP_00088]`

## S6. Transmission on request (pull of buffered data)

```plantuml
@startuml
participant "VDP-CM Proxy (P)" as P
participant "VDP Server (S)" as S
note over S : five samples already buffered
P -> S : trigger (CT=3, TX_TRIG=1) [no slot IDs => transmit only]
S -> P : trigger response ACK=1 [precedes data message]
S -> P : data message (MT=2, SQ_CT, REF_TS, DPI x5)
@enduml
```

The trigger response is always sent **before** the data message.
`[FO_PRS_VDP_00082]`, `[FO_PRS_VDP_00119]`

## S7. Combined transmission + sampling trigger

```plantuml
@startuml
participant "VDP-CM Proxy (P)" as P
participant "VDP Server (S)" as S
participant "DCA Remote (D)" as D
P -> S : trigger (CT=3, TX_TRIG=1, payload: slot 5)
S -> P : trigger response ACK=1
S -> P : data message with currently buffered samples
S -> D : trigger sampling of slot 5
D -> S : sample(slot=5) [may appear in a SUBSEQUENT data message]
@enduml
```

Samples acquired by the trigger need not be in the just-transmitted message; the server
may place them in a later data message (allowing it to split large results and avoid
buffer overflow). `[FO_PRS_VDP_00085]`, sequences 6.4.4.

## S8. Transmission on sampling (push)

```plantuml
@startuml
participant "VDP-CM Proxy (P)" as P
participant "VDP Server (S)" as S
participant "DCA Remote (D)" as D
P -> S : ADD (slot=7, TXMODE_ON_SAMPLING=1, SCYCLIC=1, SCT=...)
loop on each sample
  D -> S : sample(slot=7)
  S -> P : data message as soon as possible (>= MTDT)
end
@enduml
```

A data message is emitted as soon as possible after a marked slot is sampled.
`[FO_PRS_VDP_00053]`

## S9. Cyclic transmission

```plantuml
@startuml
participant "VDP-CM Proxy (P)" as P
participant "VDP Server (S)" as S
P -> S : ADD (TCYCLIC=1, TCT=500ms)
loop every TCT (>= MTDT)
  S -> P : data message aggregating all buffered samples
end
@enduml
```

If a cyclic `TCT` is already set, a second one is rejected with error `0x7C`; remove it
first, then add the new one. `[FO_PRS_VDP_00027..00029]`, `[FO_PRS_VDP_00145]`

## S10. Remove configurations

```plantuml
@startuml
participant "VDP-CM Proxy (P)" as P
participant "VDP Server (S)" as S
group per data point
  P -> S : remove (CT=1, GLOBAL=0, DCA_REM=0), payload: slot IDs
end
group per DCA
  P -> S : remove (CT=1, DCA_REM=1), payload: DCA_REM_IDs
end
group all
  P -> S : remove (CT=1, GLOBAL=1), empty payload
end
group stop cyclic transmission
  P -> S : remove (CT=1, T_CYCLIC=1)
end
S -> P : remove response (ACK=1, or ACK=0 with error codes)
@enduml
```

Empty payloads where content is required, or illegal flag combinations, produce protocol
error messages (`PEC=3` incorrect bytes, `PEC=5` invalid options).
`[FO_PRS_VDP_00026]`, `[FO_PRS_VDP_00069]`, `[FO_PRS_VDP_00139..00144]`

## S11. Lost control message detected

```plantuml
@startuml
participant "VDP-CM Proxy (P)" as P
participant "VDP Server (S)" as S
P -> S : control request with unexpected CON_SQ_CT
S -> P : error message (MT=3, PEC=0), P_ERR_INFO = expected CON_SQ_CT
note right of S : no control response is sent
@enduml
```

Also covers the case of an unexpected server restart. `[FO_PRS_VDP_00015]`,
`[FO_PRS_VDP_00123]`

## S12. Malformed request

```plantuml
@startuml
participant "VDP-CM Proxy (P)" as P
participant "VDP Server (S)" as S
P -> S : control request with wrong number of bytes / unknown MT / duplicate slot
S -> P : error message (MT=3, PEC=1..4), OMH = original header
@enduml
```

The server answers an incorrectly serialised request with an **error message**, not a
not-acknowledge. `[FO_PRS_VDP_00120..00126]`

## S13. Asynchronous sampling error

```plantuml
@startuml
participant "VDP-CM Proxy (P)" as P
participant "VDP Server (S)" as S
participant "DCA Remote (D)" as D
D -> S : sampling of slot 3 fails (SCYCLIC=1)
S -> P : data message containing ASYNC_ERR(EC=0x02, slot 3) in place of the sample
@enduml
```

Errors that occur independently of a request are reported inside the data message as
asynchronous error information; buffer-full loss is reported once via `0x74`.
`[FO_PRS_VDP_00105]`, `[FO_PRS_VDP_00111]`, `[FO_PRS_VDP_00118]`
