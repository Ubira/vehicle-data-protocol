"""Protocol Version Handler.

Answers protocol version requests with the server's main and minor version.

``FO_PRS_VDP_00020..00023``.
"""

from __future__ import annotations

from ..codec import Writer
from ..constants import (
    MessageType,
    PROTOCOL_VERSION_MAIN,
    PROTOCOL_VERSION_MINOR,
)
from ..header import BaseHeader


def build_version_response() -> bytes:
    """Version response (``MT=0``): main then minor version byte."""
    writer = Writer()
    BaseHeader(MessageType.VERSION, add=0).encode(writer)
    writer.write_u8(PROTOCOL_VERSION_MAIN)
    writer.write_u8(PROTOCOL_VERSION_MINOR)
    return writer.to_bytes()
