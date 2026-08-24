"""Vehicle Data Protocol (VDP) — shared protocol core.

The single source of truth for the parts of the AUTOSAR Vehicle Data Protocol wire
format that are identical on both sides of the link, so the client (VDP-CM Proxy,
``vdp_client``) and the server (VDP-CM Remote, ``vdp_server``) cannot drift apart:

* :mod:`vdp_common.codec` — little-endian ``Reader``/``Writer`` and DDLE encoding.
* :mod:`vdp_common.constants` — protocol enums and bit-field layout.
* :mod:`vdp_common.header` — the 1-byte base header.
* :mod:`vdp_common.builders` — control/version request builders and ``DpConfig``.
* :mod:`vdp_common.transport` — the transport ABC and length-framing helpers.
"""

from __future__ import annotations

from .codec import (
    DecodeError,
    Reader,
    Writer,
    decode_ddle,
    decode_relative_timestamp,
    encode_ddle,
    encode_relative_timestamp,
    reconstruct_timestamp,
)
from .header import BaseHeader, decode_base_header
from .transport import Transport, frame, recv_message

__all__ = [
    "DecodeError",
    "Reader",
    "Writer",
    "encode_ddle",
    "decode_ddle",
    "encode_relative_timestamp",
    "decode_relative_timestamp",
    "reconstruct_timestamp",
    "BaseHeader",
    "decode_base_header",
    "Transport",
    "frame",
    "recv_message",
]

__version__ = "0.1.0"
