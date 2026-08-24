"""Error Reporter — build error messages (``MT=3``).

Error message layout:

* base header ``MT=3``, ``ADD=0``;
* error header byte: ``PEC`` in bits ``[4:0]`` (5-bit protocol error code);
* ``P_ERR_INFO``: for ``PEC=0`` the expected ``CON_SQ_CT`` (1 byte); for ``PEC=1..4``
  the original message header (``OMH``) plus any additional info.

``FO_PRS_VDP_00120..00126``, ``FO_PRS_VDP_00015``.
"""

from __future__ import annotations

from .codec import Writer
from .constants import MessageType, ProtocolErrorCode
from .header import BaseHeader


def build_error_message(pec: ProtocolErrorCode, info: bytes = b"") -> bytes:
    writer = Writer()
    BaseHeader(MessageType.ERROR, add=0).encode(writer)
    writer.write_u8(int(pec) & 0x1F)
    writer.write_bytes(info)
    return writer.to_bytes()


def build_sequence_error_message(expected_con_sq_ct: int) -> bytes:
    """``PEC=0``: unexpected control sequence counter; carries the expected value."""
    return build_error_message(
        ProtocolErrorCode.CONTROL_SEQUENCE_COUNTER,
        bytes([expected_con_sq_ct & 0x1F]),
    )
