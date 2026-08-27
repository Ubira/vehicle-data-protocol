"""Base header (de)serialisation — shared by the client and the server.

Base header (1 byte), bit layout (``FO_PRS_VDP_00002``):

* bits ``[7:5]`` — ``MT`` (message type, 3 bits)
* bits ``[4:0]`` — ``ADD`` (5-bit context field): the control sequence counter
  ``CON_SQ_CT`` for control messages / the data sequence counter ``SQ_CT`` for data
  messages; ``0`` for version and error messages

There is no reserved bit in the base header: ``MT`` occupies the full top three bits.
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
        byte = ((int(self.mt) & 0x07) << 5) | (self.add & 0x1F)
        return writer.write_u8(byte)

    def to_bytes(self) -> bytes:
        return self.encode(Writer()).to_bytes()


def decode_base_header(reader: Reader) -> BaseHeader:
    byte = reader.read_u8()
    mt_value = (byte >> 5) & 0x07
    add = byte & 0x1F
    mt = MessageType(mt_value)  # MT is 3 bits, so always a valid 0..7 value
    return BaseHeader(mt=mt, add=add)
