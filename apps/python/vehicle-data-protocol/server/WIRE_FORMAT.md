# VDP wire format (as implemented)

This document describes the concrete byte layout used by **both** the Python and C
server implementations in this folder. The AUTOSAR `PRS_VDP` specification in
[standards/](../../../standards) is the normative source; the in-repo documentation
summarises the fields but not every exact bit position. Where the docs are silent, the
choices below are made so that the codec, the handlers, the tests and the two language
implementations all agree. Assumptions are marked **[assumption]**.

All multi-byte VDP fields are **little-endian**; reserved bits are `0`
(`FO_PRS_VDP_00001`, `FO_PRS_VDP_00138`).

## DDLE[UINT]

Dynamic-length unsigned integer (`FO_PRS_VDP_00003`): 7 data bits per byte, LSB group
first; the MSB (`0x80`) of each byte flags a following byte; leading zero bytes are
omitted (the value `0` is a single `0x00`). The reserved slot ID `16383` therefore
encodes as the bytes `0xFF 0x7F`, matching the async-error marker in the docs.

## Base header (1 byte) **[assumption on bit positions]**

| bits | field | meaning |
|------|-------|---------|
| `[1:0]` | `MT` | message type: 0 version, 1 control, 2 data, 3 error |
| `[6:2]` | `ADD` | 5-bit context: `CON_SQ_CT` (control) / `SQ_CT` (data) / `0` |
| `[7]` | reserved | `0` |

## Version message (`MT=0`)

- Request: base header only, no payload.
- Response: base header, then `main` (u8), `minor` (u8). Defaults `0x01`, `0x01`
  (`FO_PRS_VDP_00020..00023`).

## Control message (`MT=1`)

Base header (`ADD = CON_SQ_CT`), then an **extended header** byte:

| bits | field |
|------|-------|
| `[1:0]` | `CT` (0 add, 1 remove, 2 activation, 3 trigger) |
| `[2]` | command flag: `ACT` (activation) / `TX_TRIG` (trigger) / `GLOBAL` (remove) / `ACK` (response) |
| `[3]` | `ACK` (response) / `DCA_REM` (remove) |
| `[4]` | `T_CYCLIC` (remove) |
| others | reserved `0` |

`CON_SQ_CT` is a 5-bit counter `1..31`, init `1`, incremented per accepted request,
wrapping `31→1`, mirrored in the response (`FO_PRS_VDP_00010..00015`).

### Add configuration (`CT=0`) payload

One or more DCA groups until the end of the message:

```
DCA_REM_ID   : DDLE
DP_COUNT     : DDLE
DP_DCFG[DP_COUNT]:
    VDP_SLOT_ID : DDLE
    SET         : u8   bits: [1:0]=TRES, 2=SEC, 3=PERSIST, 4=TXMODE_ON_SAMPLING, 5=INIT_ACT
    COL         : u8   bits: 0=SCHANGE, 1=SCYCLIC, 2=TCYCLIC
    SCT         : DDLE (present iff SCYCLIC)   sampling cycle time (ms)
    TCT         : DDLE (present iff TCYCLIC)   transmission cycle time (ms)
    DCA_CFG_LEN : DDLE
    DCA_CFG     : DCA_CFG_LEN bytes (DCA-specific, opaque to the server)
```

### Remove configuration (`CT=1`) payload

- `T_CYCLIC=1`: no payload — stop cyclic transmission.
- `GLOBAL=1`: no payload — remove everything.
- `DCA_REM=1`: a list of `DCA_REM_ID` (DDLE).
- otherwise: a list of `VDP_SLOT_ID` (DDLE).

### Activation (`CT=2`) payload

A non-empty list of `VDP_SLOT_ID` (DDLE). `ACT=1` activates, `ACT=0` deactivates.

### Trigger (`CT=3`) payload

A list of `VDP_SLOT_ID` (DDLE), possibly empty when `TX_TRIG=1` (transmit only).

### Control response

Base header (mirrored `CON_SQ_CT`) + extended header (mirrored `CT`, `ACK` bit).
When `ACK=0`, the payload is a list of `(REF_ID : DDLE, ERROR_CODE : u8)` pairs, where
`REF_ID` is the affected slot or DCA Remote ID (`FO_PRS_VDP_00017`).

## Data message (`MT=2`, server → client only)

```
base header (ADD = SQ_CT)
REF_TS      : u32   reference timestamp, seconds  (FO_PRS_VDP_00097)
DPI ... (repeated until end of message):
    VDP_SLOT_ID : DDLE
    if VDP_SLOT_ID == 16383 (0xFF 0x7F):   # Asynchronous Error
        ERROR_CODE : u8
        LEN        : DDLE
        REF_SLOT   : u16   the slot the error refers to
        INFO       : LEN-2 bytes
    else:                                   # Data Point Sample
        REL_TS   : DDLE   relative timestamp delta at slot resolution TRES
        LEN      : DDLE
        DATA     : LEN bytes
```

Relative timestamps chain: the first sample is relative to `REF_TS`; each subsequent
sample is relative to the reconstructed time of the previous one, at that slot's `TRES`
(`FO_PRS_VDP_00101`, `FO_PRS_VDP_00042`). `SQ_CT` is a 5-bit counter `1..31`, init `1`,
wrapping `31→1` (`FO_PRS_VDP_00092..00095`).

## Error message (`MT=3`, server → client only)

```
base header (ADD = 0)
ERR_HDR : u8    bits [4:0] = PEC (protocol error code)
P_ERR_INFO :    PEC=0 -> expected CON_SQ_CT (u8)
                PEC=1..4 -> original message header / additional info
```

Protocol error codes (`FO_PRS_VDP_00006`): `0` control sequence counter, `1` invalid
options, `2` duplicated VDP Slot ID, `3` incorrect number of bytes, `4` unknown message
type, `5..31` reserved.

## TCP transport framing (transport concern only)

The optional TCP transport prefixes each VDP message with a **2-byte little-endian
length**. This prefix is a transport detail and is **not** part of the VDP message; VDP
itself performs no segmentation (`FO_PRS_VDP_00040`).
