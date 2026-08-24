"""Transport / bus adapter.

The transport is infrastructure: it moves whole VDP messages between the Proxy and the
Server and enforces ``VDP.maxMessageSize``. VDP performs **no segmentation** of its own
(``FO_PRS_VDP_00040``); when a real bus frame is too small a Transport Protocol is
assumed to carry the message.

Two transports are provided:

* :class:`CallbackTransport` — an in-process loopback used by tests and the demo.
* :class:`TcpServerTransport` — a TCP server. Because TCP is a byte stream, this
  transport frames each VDP message with a 2-byte little-endian length prefix. The
  prefix is a transport concern only and is **not** part of the VDP message.
"""

from __future__ import annotations

import socket
from abc import ABC, abstractmethod
from typing import Callable


class Transport(ABC):
    def __init__(self, max_message_size: int) -> None:
        self.max_message_size = max_message_size

    def _check_size(self, data: bytes) -> None:
        if len(data) > self.max_message_size:
            raise ValueError(
                f"VDP message of {len(data)} bytes exceeds "
                f"maxMessageSize={self.max_message_size}"
            )

    @abstractmethod
    def send(self, data: bytes) -> None:
        """Emit one complete VDP message toward the Proxy."""


class CallbackTransport(Transport):
    """Delivers outbound messages to a Python callable (loopback / tests)."""

    def __init__(self, max_message_size: int, sink: Callable[[bytes], None]) -> None:
        super().__init__(max_message_size)
        self._sink = sink

    def send(self, data: bytes) -> None:
        self._check_size(data)
        self._sink(data)


class TcpServerTransport(Transport):
    """A minimal single-client TCP transport with 2-byte length framing."""

    def __init__(self, max_message_size: int, host: str = "127.0.0.1", port: int = 0):
        super().__init__(max_message_size)
        self._host = host
        self._port = port
        self._listener: socket.socket | None = None
        self._conn: socket.socket | None = None

    @property
    def port(self) -> int:
        assert self._listener is not None
        return self._listener.getsockname()[1]

    def listen(self) -> None:
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listener.bind((self._host, self._port))
        self._listener.listen(1)

    def accept(self) -> None:
        assert self._listener is not None
        self._conn, _ = self._listener.accept()

    def send(self, data: bytes) -> None:
        self._check_size(data)
        assert self._conn is not None
        self._conn.sendall(len(data).to_bytes(2, "little") + data)

    def recv(self) -> bytes | None:
        """Receive one framed VDP message, or ``None`` when the peer closes."""
        assert self._conn is not None
        header = self._recv_exact(2)
        if header is None:
            return None
        length = int.from_bytes(header, "little")
        return self._recv_exact(length)

    def _recv_exact(self, n: int) -> bytes | None:
        assert self._conn is not None
        chunks = bytearray()
        while len(chunks) < n:
            chunk = self._conn.recv(n - len(chunks))
            if not chunk:
                return None
            chunks += chunk
        return bytes(chunks)

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
        if self._listener is not None:
            self._listener.close()
