"""Shared types and helpers for control command handlers.

A handler consumes the request payload (a :class:`~vdp_server.codec.Reader` positioned
just after the extended header) together with the decoded command flags, mutates the
server state, and returns a :class:`ControlOutcome`. Malformed requests raise
:class:`~vdp_server.errors.ProtocolError`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..codec import Writer
from ..constants import ACK_BIT, CommandType, MessageType
from ..errors import SlotError
from ..header import BaseHeader


@dataclass
class ControlOutcome:
    """Result of a control command.

    ``ack=True`` means the request was fully applied (empty payload). ``ack=False``
    means it was partially or fully erroneous; the successfully applicable parts are
    still applied and ``errors`` lists the affected slot / DCA IDs with error codes
    (``FO_PRS_VDP_00016``, ``FO_PRS_VDP_00017``, ``FO_PRS_VDP_00074``).
    """

    ack: bool = True
    errors: list[SlotError] = field(default_factory=list)

    def fail(self, error: SlotError) -> None:
        self.ack = False
        self.errors.append(error)


def encode_control_response(
    con_sq_ct: int, ct: CommandType, outcome: ControlOutcome
) -> bytes:
    """Serialise a control response (``MT=1``) mirroring ``CON_SQ_CT`` and ``CT``.

    Extended header byte: bits ``[1:0]`` = ``CT``; bit ``ACK_BIT`` = ``ACK``.
    When ``ACK=0`` the payload is a list of ``(ref_id DDLE, error_code u8)`` pairs.
    """
    writer = Writer()
    BaseHeader(MessageType.CONTROL, add=con_sq_ct).encode(writer)
    ext = int(ct) & 0x03
    if outcome.ack:
        ext |= 1 << ACK_BIT
    writer.write_u8(ext)
    if not outcome.ack:
        for err in outcome.errors:
            writer.write_ddle(err.ref_id)
            writer.write_u8(int(err.code))
    return writer.to_bytes()
