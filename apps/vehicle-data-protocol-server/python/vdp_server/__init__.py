"""Vehicle Data Protocol (VDP) Server — VDP-CM Remote.

A Python implementation of the AUTOSAR Vehicle Data Protocol server role, structured to
mirror the module layout of the repository's development view. See ``README.md`` and
``WIRE_FORMAT.md`` for details.
"""

from __future__ import annotations

from .constants import (
    CommandType,
    ErrorCode,
    MessageType,
    ProtocolErrorCode,
    TimestampResolution,
)
from .dca import DcaRemote, DemoDcaRemote
from .server import ServerConfig, VdpServer
from .transport import CallbackTransport, TcpServerTransport, Transport

__all__ = [
    "VdpServer",
    "ServerConfig",
    "DcaRemote",
    "DemoDcaRemote",
    "Transport",
    "CallbackTransport",
    "TcpServerTransport",
    "MessageType",
    "CommandType",
    "ErrorCode",
    "ProtocolErrorCode",
    "TimestampResolution",
]

__version__ = "0.1.0"
