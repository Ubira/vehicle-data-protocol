"""Base header (de)serialisation — shared by the client and the server.

Base header (1 byte), bit layout (little-endian bit numbering, LSB first):

* bits ``[1:0]`` — ``MT`` (message type)
* bits ``[6:2]`` — ``ADD`` (5-bit context field): the control sequence counter
  ``CON_SQ_CT`` for control messages / the data sequence counter ``SQ_CT`` for data
  messages; ``0`` for version and error messages
* bit ``[7]`` — reserved, always ``0`` (``FO_PRS_VDP_00138``)

See the server's ``WIRE_FORMAT.md`` for the complete message layout.
"""

from __future__ import annotations

from dataclasses import dataclass

from .codec import Reader, Writer
from .constants import MessageType


@dataclass(frozen=True)
class BaseHeader:
    mt: MessageType
    add: int = 0  # CON_SQ_CT / SQ_CT / 0

    def encode(self, writer: Writer) -> Writer:
        byte = (int(self.mt) & 0x03) | ((self.add & 0x1F) << 2)
        return writer.write_u8(byte)

    def to_bytes(self) -> bytes:
        return self.encode(Writer()).to_bytes()


def decode_base_header(reader: Reader) -> BaseHeader:
    byte = reader.read_u8()
    mt_value = byte & 0x03
    add = (byte >> 2) & 0x1F
    # bit 7 reserved; a set reserved bit is tolerated on decode but never emitted.
    mt = MessageType(mt_value)  # MT is 2 bits, so always a valid 0..3 value
    return BaseHeader(mt=mt, add=add)
