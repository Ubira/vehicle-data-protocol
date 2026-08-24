"""Base header (de)serialisation, shared with the server.

Base header (1 byte): bits ``[1:0]`` = ``MT``; bits ``[6:2]`` = ``ADD`` (the control
sequence counter ``CON_SQ_CT`` for control messages / the data sequence counter
``SQ_CT`` for data messages / ``0`` otherwise); bit ``[7]`` reserved = ``0``.
"""

from __future__ import annotations

from dataclasses import dataclass

from .codec import DecodeError, Reader, Writer
from .constants import MessageType


@dataclass(frozen=True)
class BaseHeader:
    mt: MessageType
    add: int = 0

    def encode(self, writer: Writer) -> Writer:
        byte = (int(self.mt) & 0x03) | ((self.add & 0x1F) << 2)
        return writer.write_u8(byte)

    def to_bytes(self) -> bytes:
        return self.encode(Writer()).to_bytes()


def decode_base_header(reader: Reader) -> BaseHeader:
    byte = reader.read_u8()
    mt_value = byte & 0x03
    add = (byte >> 2) & 0x1F
    try:
        mt = MessageType(mt_value)
    except ValueError:  # pragma: no cover - MT is 2 bits so always 0..3
        raise DecodeError(f"unknown message type {mt_value}")
    return BaseHeader(mt=mt, add=add)
