"""Message Codec — shared little-endian / DDLE encoding rules.

Single source of truth for the cross-cutting VDP encoding rules used by **both** the
client (VDP-CM Proxy) and the server (VDP-CM Remote):

* **Endianness:** every VDP-specific multi-byte field is little-endian
  (``FO_PRS_VDP_00001``).
* **Reserved bits:** always ``0`` (``FO_PRS_VDP_00138``).
* **DDLE[UINT]:** dynamic-length encoding of unsigned integers; the MSB of each byte
  flags a following byte; leading zero bytes are omitted (``FO_PRS_VDP_00003``).
* **Relative timestamp:** a DDLE-encoded delta at a per-slot resolution ``TRES``
  (``FO_PRS_VDP_00004``, ``FO_PRS_VDP_00042``).

The module has no dependency on the transport or on any role-specific state, so it can
be unit-tested in isolation. Roles that need a different parse-error type (e.g. the
server maps truncation to a protocol error message) subclass :class:`Reader` and
override :meth:`Reader._decode_error`.
"""

from __future__ import annotations

from .constants import TRES_TO_MS, TimestampResolution


class DecodeError(Exception):
    """Raised when an inbound message cannot be parsed (truncated / malformed)."""


class Reader:
    """A little-endian cursor over an immutable byte string."""

    __slots__ = ("_data", "_pos")

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._pos = 0

    @property
    def pos(self) -> int:
        return self._pos

    def remaining(self) -> int:
        return len(self._data) - self._pos

    def at_end(self) -> bool:
        return self._pos >= len(self._data)

    def _decode_error(self, message: str) -> Exception:
        """Build the exception raised on a parse failure.

        Overridden by roles that require a different error type (e.g. the server's
        :class:`~vdp_server.codec.Reader` raises a protocol error carrying a PEC).
        """
        return DecodeError(message)

    def _need(self, n: int) -> None:
        if self.remaining() < n:
            raise self._decode_error("unexpected end of message")

    def read_u8(self) -> int:
        self._need(1)
        value = self._data[self._pos]
        self._pos += 1
        return value

    def read_u16(self) -> int:
        self._need(2)
        value = int.from_bytes(self._data[self._pos : self._pos + 2], "little")
        self._pos += 2
        return value

    def read_u32(self) -> int:
        self._need(4)
        value = int.from_bytes(self._data[self._pos : self._pos + 4], "little")
        self._pos += 4
        return value

    def read_bytes(self, n: int) -> bytes:
        self._need(n)
        chunk = self._data[self._pos : self._pos + n]
        self._pos += n
        return chunk

    def read_ddle(self) -> int:
        """Decode a DDLE[UINT]: 7 data bits per byte, MSB = continuation flag."""
        value = 0
        shift = 0
        while True:
            self._need(1)
            byte = self._data[self._pos]
            self._pos += 1
            value |= (byte & 0x7F) << shift
            if byte & 0x80 == 0:
                return value
            shift += 7
            if shift > 63:  # guard against pathological input
                raise self._decode_error("DDLE value too long")


class Writer:
    """A little-endian byte accumulator."""

    __slots__ = ("_buf",)

    def __init__(self) -> None:
        self._buf = bytearray()

    def write_u8(self, value: int) -> "Writer":
        self._buf.append(value & 0xFF)
        return self

    def write_u16(self, value: int) -> "Writer":
        self._buf += (value & 0xFFFF).to_bytes(2, "little")
        return self

    def write_u32(self, value: int) -> "Writer":
        self._buf += (value & 0xFFFFFFFF).to_bytes(4, "little")
        return self

    def write_bytes(self, data: bytes) -> "Writer":
        self._buf += data
        return self

    def write_ddle(self, value: int) -> "Writer":
        """Encode a DDLE[UINT]; leading zero bytes are omitted (value 0 -> one byte)."""
        if value < 0:
            raise ValueError("DDLE only encodes unsigned integers")
        while True:
            byte = value & 0x7F
            value >>= 7
            if value:
                self._buf.append(byte | 0x80)
            else:
                self._buf.append(byte)
                return self

    def to_bytes(self) -> bytes:
        return bytes(self._buf)

    def __len__(self) -> int:
        return len(self._buf)


def encode_ddle(value: int) -> bytes:
    return Writer().write_ddle(value).to_bytes()


def decode_ddle(data: bytes) -> int:
    return Reader(data).read_ddle()


# --- Relative timestamps [FO_PRS_VDP_00004], [FO_PRS_VDP_00042] ---------------

def encode_relative_timestamp(
    sample_ms: int, previous_ms: int, tres: TimestampResolution
) -> bytes:
    """DDLE-encode ``(sample_ms - previous_ms)`` quantised to the slot resolution."""
    step = TRES_TO_MS[tres]
    delta_ms = sample_ms - previous_ms
    if delta_ms < 0:
        delta_ms = 0
    ticks = delta_ms // step
    return encode_ddle(ticks)


def decode_relative_timestamp(
    ticks: int, previous_ms: int, tres: TimestampResolution
) -> int:
    """Reconstruct the absolute sample time (ms) from a relative-timestamp delta."""
    return previous_ms + ticks * TRES_TO_MS[tres]


# The client historically calls the decode direction ``reconstruct_timestamp``.
reconstruct_timestamp = decode_relative_timestamp
