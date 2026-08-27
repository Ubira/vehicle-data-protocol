"""Shared VDP protocol constants (wire format).

Single source of truth for the on-the-wire constants used by **both** the client
(VDP-CM Proxy) and the server (VDP-CM Remote). Grounded in the AUTOSAR Vehicle Data
Protocol (Foundation R25-11) as summarised in the repository documentation (``docs/``).
Requirement identifiers such as ``FO_PRS_VDP_00007`` refer to the AUTOSAR source
specifications for traceability. See the server's ``WIRE_FORMAT.md`` for the full
message layout.

Role-specific deployment defaults (e.g. the server's ``VDP.maxMessageSize``) live in the
respective package's ``constants`` module, not here.
"""

from __future__ import annotations

from enum import IntEnum

# --- Protocol version [FO_PRS_VDP_00020..00023] --------------------------------
PROTOCOL_VERSION_MAIN = 0x01
PROTOCOL_VERSION_MINOR = 0x01

# --- Message types (MT, 3 bits) [FO_PRS_VDP_00002], [00007] -------------------
#     Carried in the base header bits [7:5] (see ``header.py``).
class MessageType(IntEnum):
    VERSION = 0  # request <-> response
    CONTROL = 1  # request <-> response
    DATA = 2     # server -> client only
    ERROR = 3    # server -> client only


# --- Control command types (CT, 3 bits) [FO_PRS_VDP_00048], [00009] -----------
#     Carried in the control extended-header bits [7:5]; values 4..7 are reserved.
class CommandType(IntEnum):
    ADD_CONFIG = 0
    REMOVE_CONFIG = 1
    ACTIVATION = 2
    TRIGGER = 3


# Command type field position within the extended header (bits [7:5]).
CT_SHIFT = 5
CT_MASK = 0x07


# --- Sequence counters [FO_PRS_VDP_00010..00015], [00092..00095] --------------
SEQ_MIN = 1
SEQ_MAX = 31          # 5-bit counter; wraps 31 -> 1
SEQ_INIT = 1

# --- Identifier ranges [FO_PRS_VDP_00031], [00036], [00146] -------------------
DCA_REM_ID_MIN = 1
DCA_REM_ID_MAX = 16383
SLOT_ID_MIN = 1
SLOT_ID_MAX_LIMIT = 16382     # maxSlotID must be <= 16382
SLOT_ID_ASYNC_ERROR = 16383   # reserved marker (encodes to bytes 0xFF 0x7F)
ASYNC_ERROR_MARKER = (0xFF, 0x7F)

# --- Timestamp resolution (TRES, 3 bits) [FO_PRS_VDP_00042] --------------------
class TimestampResolution(IntEnum):
    US_1 = 0    # 1 microsecond
    US_10 = 1   # 10 microseconds
    US_100 = 2  # 100 microseconds
    MS_1 = 3    # 1 millisecond
    MS_10 = 4   # 10 milliseconds
    MS_100 = 5  # 100 milliseconds
    S_1 = 6     # 1 second
    # value 7 is reserved and unused


# Resolution expressed in whole milliseconds. Only the millisecond-and-coarser
# resolutions are listed: this reference implementation models time in integer
# milliseconds and therefore does not sample at the sub-millisecond resolutions.
TRES_TO_MS = {
    TimestampResolution.MS_1: 1,
    TimestampResolution.MS_10: 10,
    TimestampResolution.MS_100: 100,
    TimestampResolution.S_1: 1000,
}

# --- Protocol error codes (PEC, 5 bits) [FO_PRS_VDP_00006] --------------------
class ProtocolErrorCode(IntEnum):
    CONTROL_SEQUENCE_COUNTER = 0  # unexpected CON_SQ_CT (no control response sent)
    INVALID_OPTIONS = 1
    DUPLICATED_SLOT_ID = 2
    INCORRECT_NUMBER_OF_BYTES = 3
    UNKNOWN_MESSAGE_TYPE = 4


# --- Error codes (EC, 1 byte) [FO_PRS_VDP_00005] ------------------------------
#     Values sent from the VDP-CM Remote to the VDP-CM Proxy in a control response
#     (sync) or a data message (async). Codes 0x00..0x08 originate in the DCA
#     Remote; codes 0x70..0x7D originate in the VDP-CM Remote. The bracketed tags
#     reference the AUTOSAR requirement (FO_PRS_VDP_*) that defines each code.
class ErrorCode(IntEnum):
    # Internal sentinel only: "no error" / success. Never sent on the wire (the
    # on-wire value 0x00 means Generic error (DCA Remote) -> GENERIC_DCA).
    NONE = -1

    # -- Errors originating in the DCA Remote (0x00..0x08) --
    GENERIC_DCA = 0x00             # Generic error (DCA Remote)              [00018/00109]
    DATA_SOURCE_ERROR = 0x01       # Data source error (async)              [00110]
    SAMPLING_ERROR = 0x02          # Data point sampling error (sync/async) [00111/00134]
    DATA_LOSS = 0x03               # Data loss error (async)                [00112]
    INVALID_DCFG = 0x04            # Invalid DCA_REM_DP_DCFG (sync)          [00127]
    DUPLICATED_DCFG = 0x05         # Duplicated DCA_REM_DP_DCFG (sync)       [00128]
    DATA_POINT_LIMIT = 0x06        # Data point limit reached (sync)        [00129]
    CYCLIC_NOT_SUPPORTED = 0x07    # Sampling mode cyclic not supported (sync)    [00062]
    ONCHANGE_NOT_SUPPORTED = 0x08  # Sampling mode on-change not supported (sync) [00058]

    # -- Errors originating in the VDP-CM Remote (0x70..0x7D) --
    GENERIC_REMOTE = 0x70                  # Generic error (VDP-CM Remote)          [00019/00114]
    TIMESTAMP_ENCODING_ERROR = 0x71        # Timestamp encoding error (async)       [00115]
    TIMEBASE_ERROR = 0x72                  # Timebase error (async)                 [00116]
    SAMPLE_TOO_LONG = 0x73                 # Sample too long (async)                [00117]
    BUFFER_FULL = 0x74                     # Data buffer full (async)               [00118]
    UNKNOWN_SLOT_ID = 0x75                 # VDP Slot ID unknown (sync)             [00135]
    UNKNOWN_DCA_REM_ID = 0x76              # DCA Remote ID unknown (sync)           [00130]
    SLOT_ID_OUT_OF_RANGE = 0x77            # VDP Slot ID out of range (sync)        [00131]
    PERSISTENCY_LIMIT = 0x78               # Persistency storage limit reached (sync)     [00052]
    DUPLICATE_SLOT_ID = 0x79               # VDP Slot ID already in use (sync)      [00132]
    DCA_REM_INCONSISTENCY = 0x7A           # DCA Remote inconsistency error (sync)  [00133]
    SECURED_CHANNEL_NOT_SUPPORTED = 0x7B   # Secured channel not supported (sync)   [00046]
    CYCLIC_TX_ALREADY_SET = 0x7C           # TX mode cyclic already in use / not set (sync) [00145/00038]
    SLOT_ID_RESERVED = 0x7D                # VDP Slot ID reserved (sync)            [00136]


# --- SET field bit positions (per-slot VDP settings) [FO_PRS_VDP_00041] --------
#     Byte layout: bit 7 reserved, bits [6:4] TRES, bit 3 SEC, bit 2 PERSIST,
#     bit 1 TXMODE_ON_SAMPLING, bit 0 INIT_ACT.
SET_TRES_SHIFT = 4
SET_TRES_MASK = 0b0111_0000   # bits [6:4]
SET_SEC_BIT = 3
SET_PERSIST_BIT = 2
SET_TXMODE_ON_SAMPLING_BIT = 1
SET_INIT_ACT_BIT = 0

# --- COL field bit positions (collection / sampling settings) [FO_PRS_VDP_00056]
#     Byte layout: bits [7:2] reserved, bit 1 SCHANGE, bit 0 SCYCLIC.
#     Note: transmission-mode-cyclic (TCYCLIC) is *not* part of COL; it lives in
#     the add-configuration extended header (see ADD_TCYCLIC_BIT below).
COL_SCHANGE_BIT = 1
COL_SCYCLIC_BIT = 0

# --- Add-configuration extended-header flag [FO_PRS_VDP_00024] -----------------
#     Byte 0: bits [7:5] CT, bits [4:1] reserved, bit 0 TCYCLIC. When TCYCLIC=1 a
#     2-byte uint16 transmission cycle time (TCT) follows the extended-header byte.
ADD_TCYCLIC_BIT = 0

# --- Remove-command flag bit positions [FO_PRS_VDP_00141] ----------------------
#     Byte 0: bits [7:5] CT, bits [4:3] reserved, bit 2 DCA_REM, bit 1 GLOBAL,
#     bit 0 T_CYCLIC.
REMOVE_DCA_REM_BIT = 2
REMOVE_GLOBAL_BIT = 1
REMOVE_T_CYCLIC_BIT = 0

# --- Activation / trigger / response flag bit positions -----------------------
#     Activation [FO_PRS_VDP_00067]: bit 0 ACT (1 = activate, 0 = deactivate).
#     Trigger    [FO_PRS_VDP_00081]: bit 0 TX_TRIG (1 = transmission trigger).
#     Response   [FO_PRS_VDP_00047]: bit 0 ACK (control-response acknowledge).
ACT_BIT = 0
TX_TRIG_BIT = 0
ACK_BIT = 0


__all__ = [
    "PROTOCOL_VERSION_MAIN",
    "PROTOCOL_VERSION_MINOR",
    "MessageType",
    "CommandType",
    "CT_SHIFT",
    "CT_MASK",
    "SEQ_MIN",
    "SEQ_MAX",
    "SEQ_INIT",
    "DCA_REM_ID_MIN",
    "DCA_REM_ID_MAX",
    "SLOT_ID_MIN",
    "SLOT_ID_MAX_LIMIT",
    "SLOT_ID_ASYNC_ERROR",
    "ASYNC_ERROR_MARKER",
    "TimestampResolution",
    "TRES_TO_MS",
    "ProtocolErrorCode",
    "ErrorCode",
    "SET_TRES_SHIFT",
    "SET_TRES_MASK",
    "SET_SEC_BIT",
    "SET_PERSIST_BIT",
    "SET_TXMODE_ON_SAMPLING_BIT",
    "SET_INIT_ACT_BIT",
    "COL_SCHANGE_BIT",
    "COL_SCYCLIC_BIT",
    "ADD_TCYCLIC_BIT",
    "REMOVE_GLOBAL_BIT",
    "REMOVE_DCA_REM_BIT",
    "REMOVE_T_CYCLIC_BIT",
    "ACT_BIT",
    "TX_TRIG_BIT",
    "ACK_BIT",
]
