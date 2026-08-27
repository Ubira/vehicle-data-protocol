# VDP wire format (as implemented)

This document describes the concrete byte layout used by the Python server
implementation in this folder. The AUTOSAR `PRS_VDP` specification in
[standards/](../../../standards) is the normative source, and the bit positions below
are taken directly from it (the referenced `FO_PRS_VDP_*` requirements). Where the
specification genuinely leaves a choice open, the assumption is marked **[assumption]**.

All multi-byte VDP fields are **little-endian**; reserved bits are `0`
(`FO_PRS_VDP_00001`, `FO_PRS_VDP_00138`).

## DDLE[UINT]

Dynamic-length unsigned integer (`FO_PRS_VDP_00003`): 7 data bits per byte, LSB group
first; the MSB (`0x80`) of each byte flags a following byte; leading zero bytes are
omitted (the value `0` is a single `0x00`). The reserved slot ID `16383` therefore
encodes as the bytes `0xFF 0x7F`, matching the async-error marker in the docs.

## Base header (1 byte) — `FO_PRS_VDP_00002`

| bits | field | meaning |
|------|-------|---------|
| `[7:5]` | `MT` | message type (3 bits): 0 version, 1 control, 2 data, 3 error |
| `[4:0]` | `ADD` | 5-bit context: `CON_SQ_CT` (control) / `SQ_CT` (data) / `0` |

## Version message (`MT=0`)

- Request: base header only, no payload.
- Response: base header, then `main` (u8), `minor` (u8). Defaults `0x01`, `0x01`
  (`FO_PRS_VDP_00020..00023`).

## Control message (`MT=1`)

Base header (`ADD = CON_SQ_CT`), then an **extended header** whose first byte is
(`FO_PRS_VDP_00009`):

| bits | field |
|------|-------|
| `[7:5]` | `CT` (0 add, 1 remove, 2 activation, 3 trigger) |
| `[4:0]` | `ADD_EXT` command-specific flags (see each command below) |

`CON_SQ_CT` is a 5-bit counter `1..31`, init `1`, incremented per accepted request,
wrapping `31→1`, mirrored in the response (`FO_PRS_VDP_00010..00015`).

### Add configuration (`CT=0`) — `FO_PRS_VDP_00024`, `00030`, `00035`

Extended header:

```
Byte 0 : [7:5]=CT(=0)  [4:1]=reserved  [0]=TCYCLIC
Byte 1-2 : TCT : u16   transmission cycle time (ms), present iff TCYCLIC (FO_PRS_VDP_00028)
```

Then one or more DCA groups until the end of the message:

```
DCA_REM_ID       : DDLE
DCA_REM_DCFG_CT  : DDLE   number of DP_DCFG following
DP_DCFG[DCA_REM_DCFG_CT]:
    VDP_SLOT_ID : DDLE
    SET         : u8   bits: [7]=reserved [6:4]=TRES [3]=SEC [2]=PERSIST [1]=TXMODE_ON_SAMPLING [0]=INIT_ACT  (FO_PRS_VDP_00041)
    COL         : u8   bits: [7:2]=reserved [1]=SCHANGE [0]=SCYCLIC  (FO_PRS_VDP_00056)
    SCT         : u16   sampling cycle time (ms), present iff SCYCLIC  (FO_PRS_VDP_00060)
    DCA_CFG_LEN : DDLE
    DCA_CFG     : DCA_CFG_LEN bytes (DCA-specific, opaque to the server)
```

`TRES` encodes the timestamp resolution (`FO_PRS_VDP_00042`): `0`=1 µs, `1`=10 µs,
`2`=100 µs, `3`=1 ms, `4`=10 ms, `5`=100 ms, `6`=1 s, `7` reserved. This reference
implementation models time in whole milliseconds and therefore uses the `≥1 ms`
resolutions.

### Remove configuration (`CT=1`) — `FO_PRS_VDP_00141`

Extended header (one byte): `[7:5]=CT(=1)  [4:3]=reserved  [2]=DCA_REM  [1]=GLOBAL  [0]=T_CYCLIC`.

- `T_CYCLIC=1`: no payload — stop cyclic transmission (`FO_PRS_VDP_00038`).
- `GLOBAL=1`: no payload — remove everything (`FO_PRS_VDP_00026`).
- `DCA_REM=1`: a list of `DCA_REM_ID` (DDLE).
- otherwise: a list of `VDP_SLOT_ID` (DDLE).

### Activation (`CT=2`) — `FO_PRS_VDP_00067`

Extended header: `[7:5]=CT(=2)  [4:1]=reserved  [0]=ACT`. Payload: a non-empty list of
`VDP_SLOT_ID` (DDLE). `ACT=1` activates, `ACT=0` deactivates.

### Trigger (`CT=3`) — `FO_PRS_VDP_00081`

Extended header: `[7:5]=CT(=3)  [4:1]=reserved  [0]=TX_TRIG`. Payload: a list of
`VDP_SLOT_ID` (DDLE), possibly empty when `TX_TRIG=1` (transmit only).

### Control response — `FO_PRS_VDP_00047`

Base header (mirrored `CON_SQ_CT`) + extended header byte
`[7:5]=CT  [4:1]=reserved  [0]=ACK`. When `ACK=0`, the payload is a list of
`(REF_ID : DDLE, ERROR_CODE : u8)` pairs, where `REF_ID` is the affected slot or DCA
Remote ID (`FO_PRS_VDP_00017`).

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
