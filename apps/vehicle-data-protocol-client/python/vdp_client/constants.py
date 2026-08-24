"""Protocol constants for the VDP Client (VDP-CM Proxy).

Grounded in the AUTOSAR Vehicle Data Protocol (Foundation R25-11) as summarised in the
repository documentation (``docs/``). These constants mirror the **same wire format**
used by the VDP Server under
``apps/vehicle-data-protocol-server`` (see its ``WIRE_FORMAT.md``) so the client and
server are interoperable.
"""

from __future__ import annotations

from enum import IntEnum

# --- Protocol version [FO_PRS_VDP_00020..00023] --------------------------------
PROTOCOL_VERSION_MAIN = 0x01
PROTOCOL_VERSION_MINOR = 0x01

# --- Message types (MT, 2 bits) ------------------------------------------------
class MessageType(IntEnum):
    VERSION = 0  # request <-> response
    CONTROL = 1  # request <-> response
    DATA = 2     # server -> client only
    ERROR = 3    # server -> client only


# --- Control command types (CT, 2 bits) ---------------------------------------
class CommandType(IntEnum):
    ADD_CONFIG = 0
    REMOVE_CONFIG = 1
    ACTIVATION = 2
    TRIGGER = 3


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

# --- Timestamp resolution (TRES, 2 bits) --------------------------------------
class TimestampResolution(IntEnum):
    MS_1 = 0
    MS_10 = 1
    MS_100 = 2
    S_1 = 3


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


# --- Processing / async error codes [FO_PRS_VDP_00105..00118] -----------------
class ErrorCode(IntEnum):
    NONE = 0x00
    GENERIC = 0x01
    SAMPLING_ERROR = 0x02          # async: sampling of a slot failed
    DATA_LOSS = 0x03               # async: sample lost
    CYCLIC_NOT_SUPPORTED = 0x07    # add: cyclic sampling not supported
    ONCHANGE_NOT_SUPPORTED = 0x08  # add: on-change sampling not supported
    TIMEBASE_ERROR = 0x72          # async: global time sync lost
    BUFFER_FULL = 0x74             # async: sample buffer overflow (reported once)
    UNKNOWN_SLOT_ID = 0x75         # activation/trigger/remove: slot not configured
    UNKNOWN_DCA_REM_ID = 0x76      # add/remove: DCA Remote not known
    PERSISTENCY_LIMIT = 0x78       # add: non-volatile storage exhausted
    DUPLICATE_SLOT_ID = 0x79       # add: slot ID already configured
    CYCLIC_TX_ALREADY_SET = 0x7C   # add: a cyclic TCT is already configured


# --- SET field bit positions (per-slot VDP settings) --------------------------
SET_TRES_MASK = 0b0000_0011   # bits [1:0]
SET_SEC_BIT = 2
SET_PERSIST_BIT = 3
SET_TXMODE_ON_SAMPLING_BIT = 4
SET_INIT_ACT_BIT = 5

# --- COL field bit positions (collection / sampling settings) -----------------
COL_SCHANGE_BIT = 0
COL_SCYCLIC_BIT = 1
COL_TCYCLIC_BIT = 2

# --- Remove-command flag bit positions ----------------------------------------
REMOVE_GLOBAL_BIT = 2
REMOVE_DCA_REM_BIT = 3
REMOVE_T_CYCLIC_BIT = 4

# --- Activation / trigger flag bit positions ----------------------------------
ACT_BIT = 2        # activation: 1 = activate, 0 = deactivate
TX_TRIG_BIT = 2    # trigger: 1 = transmission trigger
ACK_BIT = 3        # control response acknowledge flag
