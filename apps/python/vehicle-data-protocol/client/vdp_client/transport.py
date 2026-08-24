"""Transport / bus adapter for the client side.

Moves whole VDP messages between the Proxy and the Server. The transport ABC and the
2-byte length framing are shared with the server (see :mod:`vdp_common.transport`); this
module adds only the client-specific transports.

* :class:`CallbackTransport` — an in-process loopback used by the demo and tests.
* :class:`TcpClientTransport` — a TCP client. TCP is a byte stream, so each VDP message
  is framed with a 2-byte little-endian length prefix (a transport concern only, matching
  the server's ``TcpServerTransport``).
"""

from __future__ import annotations

import socket
from typing import Callable

from vdp_common.transport import Transport, frame, recv_message

__all__ = ["Transport", "CallbackTransport", "TcpClientTransport"]


class CallbackTransport(Transport):
    """Delivers outbound requests to a Python callable (loopback / tests)."""

    def __init__(self, sink: Callable[[bytes], None]) -> None:
        super().__init__()
        self._sink = sink

    def send(self, data: bytes) -> None:
        self._sink(data)


class TcpClientTransport(Transport):
    """A minimal TCP client with 2-byte length framing."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        super().__init__()
        self._host = host
        self._port = port
        self._sock: socket.socket | None = None

    def connect(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((self._host, self._port))

    def send(self, data: bytes) -> None:
        assert self._sock is not None
        self._sock.sendall(frame(data))

    def recv(self) -> bytes | None:
        """Receive one framed VDP message, or ``None`` when the peer closes."""
        assert self._sock is not None
        return recv_message(self._sock)

    def close(self) -> None:
        if self._sock is not None:
            self._sock.close()
