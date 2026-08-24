"""Message Codec for the VDP Server (VDP-CM Remote).

The little-endian / DDLE encoding rules are shared with the client and live in
:mod:`vdp_common.codec`. The server differs in exactly one respect: a truncated or
over-long field must be reported to the Proxy as a protocol error message
(``PEC=INCORRECT_NUMBER_OF_BYTES``) rather than a generic decode error. That is achieved
here by subclassing the shared :class:`~vdp_common.codec.Reader` and overriding its
error hook — the parsing logic itself is **not** duplicated.
"""

from __future__ import annotations

from vdp_common.codec import Reader as _CommonReader
from vdp_common.codec import (  # re-exported for a stable role-local import surface
    DecodeError,
    Writer,
    decode_ddle,
    decode_relative_timestamp,
    encode_ddle,
    encode_relative_timestamp,
    reconstruct_timestamp,
)

from .constants import ProtocolErrorCode
from .errors import ProtocolError

__all__ = [
    "Reader",
    "Writer",
    "DecodeError",
    "encode_ddle",
    "decode_ddle",
    "encode_relative_timestamp",
    "decode_relative_timestamp",
    "reconstruct_timestamp",
]


class Reader(_CommonReader):
    """A little-endian cursor that maps parse failures to a VDP protocol error.

    Truncated messages and over-long DDLE values become a ``ProtocolError`` carrying
    ``INCORRECT_NUMBER_OF_BYTES`` so the dispatcher can answer with an error message
    (``MT=3``) instead of crashing.
    """

    def _decode_error(self, message: str) -> Exception:
        return ProtocolError(ProtocolErrorCode.INCORRECT_NUMBER_OF_BYTES)
