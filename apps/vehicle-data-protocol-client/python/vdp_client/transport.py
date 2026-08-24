"""Transport / bus adapter for the client side.

Moves whole VDP messages between the Proxy and the Server. VDP performs no segmentation
of its own (``FO_PRS_VDP_00040``); a Transport Protocol is assumed when a real bus frame
is too small.

* :class:`CallbackTransport` — an in-process loopback used by the demo and tests.
* :class:`TcpClientTransport` — a TCP client. TCP is a byte stream, so each VDP message
  is framed with a 2-byte little-endian length prefix (a transport concern only, matching
  the server's ``TcpServerTransport``).
"""

from __future__ import annotations

import socket
from abc import ABC, abstractmethod
from typing import Callable


class Transport(ABC):
    @abstractmethod
    def send(self, data: bytes) -> None:
        """Emit one complete VDP request toward the Server."""


class CallbackTransport(Transport):
    """Delivers outbound requests to a Python callable (loopback / tests)."""

    def __init__(self, sink: Callable[[bytes], None]) -> None:
        self._sink = sink

    def send(self, data: bytes) -> None:
        self._sink(data)


class TcpClientTransport(Transport):
    """A minimal TCP client with 2-byte length framing."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        self._host = host
        self._port = port
        self._sock: socket.socket | None = None

    def connect(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((self._host, self._port))

    def send(self, data: bytes) -> None:
        assert self._sock is not None
        self._sock.sendall(len(data).to_bytes(2, "little") + data)

    def recv(self) -> bytes | None:
        """Receive one framed VDP message, or ``None`` when the peer closes."""
        assert self._sock is not None
        header = self._recv_exact(2)
        if header is None:
            return None
        length = int.from_bytes(header, "little")
        return self._recv_exact(length)

    def _recv_exact(self, n: int) -> bytes | None:
        assert self._sock is not None
        chunks = bytearray()
        while len(chunks) < n:
            chunk = self._sock.recv(n - len(chunks))
            if not chunk:
                return None
            chunks += chunk
        return bytes(chunks)

    def close(self) -> None:
        if self._sock is not None:
            self._sock.close()
