"""Base and extended header (de)serialisation — re-exported from the shared core.

The base header is identical on both sides of the link; see :mod:`vdp_common.header`.
It is exposed here under ``vdp_server.header`` for a stable, role-local import surface.
On the server, header decoding uses the server's :class:`~vdp_server.codec.Reader`, so a
truncated header is reported as a protocol error message. See ``WIRE_FORMAT.md`` for the
complete message layout.
"""

from __future__ import annotations

from vdp_common.header import BaseHeader, decode_base_header

__all__ = ["BaseHeader", "decode_base_header"]
