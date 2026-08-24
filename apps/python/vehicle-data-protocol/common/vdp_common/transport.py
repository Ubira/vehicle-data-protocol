"""Transport / bus adapter — shared framing infrastructure.

The transport is infrastructure: it moves whole VDP messages between the Proxy and the
Server. VDP performs **no segmentation** of its own (``FO_PRS_VDP_00040``); when a real
bus frame is too small a Transport Protocol is assumed to carry the message.

This module provides the parts that are identical on both sides:

* :class:`Transport` — the abstract base, including the optional ``maxMessageSize``
  check (a no-op when no limit is configured, as on the client).
* :func:`frame` / :func:`recv_message` — 2-byte little-endian length framing for
  byte-stream transports such as TCP. The length prefix is a transport concern only and
  is **not** part of the VDP message.

Role-specific transports (in-process loopback, TCP client vs TCP server) live in each
package's ``transport`` module and build on these primitives.
"""

from __future__ import annotations

import socket
from abc import ABC, abstractmethod

_LENGTH_PREFIX_BYTES = 2


class Transport(ABC):
    """Abstract transport that emits one complete VDP message per :meth:`send`."""

    def __init__(self, max_message_size: int | None = None) -> None:
        self.max_message_size = max_message_size

    def _check_size(self, data: bytes) -> None:
        if self.max_message_size is not None and len(data) > self.max_message_size:
            raise ValueError(
                f"VDP message of {len(data)} bytes exceeds "
                f"maxMessageSize={self.max_message_size}"
            )

    @abstractmethod
    def send(self, data: bytes) -> None:
        """Emit one complete VDP message toward the peer."""


def frame(data: bytes) -> bytes:
    """Prefix a message with its 2-byte little-endian length for stream transports."""
    return len(data).to_bytes(_LENGTH_PREFIX_BYTES, "little") + data


def recv_message(sock: socket.socket) -> bytes | None:
    """Receive one length-framed VDP message, or ``None`` when the peer closes."""
    header = _recv_exact(sock, _LENGTH_PREFIX_BYTES)
    if header is None:
        return None
    length = int.from_bytes(header, "little")
    return _recv_exact(sock, length)


def _recv_exact(sock: socket.socket, n: int) -> bytes | None:
    chunks = bytearray()
    while len(chunks) < n:
        chunk = sock.recv(n - len(chunks))
        if not chunk:
            return None
        chunks += chunk
    return bytes(chunks)
