"""Message Codec — re-exported from the shared protocol core.

The client uses the shared little-endian / DDLE codec verbatim (see
:mod:`vdp_common.codec`); it is exposed here under ``vdp_client.codec`` for a stable,
role-local import surface.
"""

from __future__ import annotations

from vdp_common.codec import (
    DecodeError,
    Reader,
    Writer,
    decode_ddle,
    decode_relative_timestamp,
    encode_ddle,
    encode_relative_timestamp,
    reconstruct_timestamp,
)

__all__ = [
    "DecodeError",
    "Reader",
    "Writer",
    "encode_ddle",
    "decode_ddle",
    "encode_relative_timestamp",
    "decode_relative_timestamp",
    "reconstruct_timestamp",
]
