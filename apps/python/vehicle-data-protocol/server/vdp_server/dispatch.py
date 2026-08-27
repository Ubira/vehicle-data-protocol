"""Message Dispatcher.

Reads the message type (``MT``) and, for control messages, the command type (``CT``);
validates and mirrors the 5-bit control message sequence counter (``CON_SQ_CT``); routes
requests to the correct handler; and turns malformed requests into error messages.

* Unexpected ``CON_SQ_CT`` -> error message ``PEC=0`` carrying the expected counter, and
  **no** control response (``FO_PRS_VDP_00015``, ``FO_PRS_VDP_00123``).
* ``CON_SQ_CT`` is 5-bit ``1..31``, initialised to ``1``, incremented per accepted
  request, wrapping ``31 -> 1`` (``FO_PRS_VDP_00010..00013``); it is mirrored in the
  response (``FO_PRS_VDP_00014``).

``FO_PRS_VDP_00007``, ``FO_PRS_VDP_00048``, ``FO_PRS_VDP_00120..00126``.
"""

from __future__ import annotations

from .codec import Reader
from .commands import (
    build_version_response,
    encode_control_response,
    handle_activation,
    handle_add,
    handle_remove,
    handle_trigger,
)
from .constants import (
    CommandType,
    CT_MASK,
    CT_SHIFT,
    MessageType,
    ProtocolErrorCode,
    SEQ_INIT,
    SEQ_MAX,
    SEQ_MIN,
)
from .context import ServerContext
from .error_report import build_error_message, build_sequence_error_message
from .errors import ProtocolError
from .header import decode_base_header

_CONTROL_HANDLERS = {
    CommandType.ADD_CONFIG: handle_add,
    CommandType.REMOVE_CONFIG: handle_remove,
    CommandType.ACTIVATION: handle_activation,
    CommandType.TRIGGER: handle_trigger,
}


def _next_seq(current: int) -> int:
    return SEQ_MIN if current >= SEQ_MAX else current + 1


class Dispatcher:
    def __init__(self, ctx: ServerContext) -> None:
        self._ctx = ctx
        self.expected_con_sq_ct = SEQ_INIT

    def handle(self, message: bytes) -> list[bytes]:
        """Process one inbound message and return the outbound response messages."""
        reader = Reader(message)
        try:
            header = decode_base_header(reader)
        except ProtocolError as err:
            return [build_error_message(err.pec, err.info)]

        if header.mt == MessageType.VERSION:
            return [build_version_response()]

        if header.mt == MessageType.CONTROL:
            return self._handle_control(header.add, reader)

        # Data and error messages are server -> client only; inbound is invalid.
        return [build_error_message(ProtocolErrorCode.UNKNOWN_MESSAGE_TYPE)]

    def _handle_control(self, con_sq_ct: int, reader: Reader) -> list[bytes]:
        # Validate the control sequence counter before doing anything else.
        if con_sq_ct != self.expected_con_sq_ct:
            return [build_sequence_error_message(self.expected_con_sq_ct)]

        try:
            ext = reader.read_u8()
            ct = CommandType((ext >> CT_SHIFT) & CT_MASK)
            handler = _CONTROL_HANDLERS[ct]
            outcome = handler(self._ctx, reader, ext)
        except ProtocolError as err:
            # A correctly sequenced but malformed request: report an error message.
            # The sequence counter still advances (the request was received in order).
            self.expected_con_sq_ct = _next_seq(self.expected_con_sq_ct)
            return [build_error_message(err.pec, err.info)]

        response = encode_control_response(con_sq_ct, ct, outcome)
        self.expected_con_sq_ct = _next_seq(self.expected_con_sq_ct)
        return [response]
