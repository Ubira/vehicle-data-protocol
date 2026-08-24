"""Vehicle Data Protocol (VDP) Client — VDP-CM Proxy.

A Python implementation of the AUTOSAR Vehicle Data Protocol client role (the requesting
side). It shares the wire format of the VDP Server under
``apps/python/vehicle-data-protocol/server`` so the two interoperate. See ``README.md``.
"""

from __future__ import annotations

from .client import VdpClient
from .constants import (
    CommandType,
    ErrorCode,
    MessageType,
    ProtocolErrorCode,
    TimestampResolution,
)
from .decode import (
    ControlResponse,
    DataAsyncError,
    DataMessage,
    DataPointSample,
    ErrorMessage,
    SlotErrorInfo,
    VersionResponse,
    decode_message,
)
from .messages import DpConfig
from .transport import CallbackTransport, TcpClientTransport, Transport

__all__ = [
    "VdpClient",
    "DpConfig",
    "Transport",
    "CallbackTransport",
    "TcpClientTransport",
    "decode_message",
    "VersionResponse",
    "ControlResponse",
    "SlotErrorInfo",
    "DataMessage",
    "DataPointSample",
    "DataAsyncError",
    "ErrorMessage",
    "MessageType",
    "CommandType",
    "ErrorCode",
    "ProtocolErrorCode",
    "TimestampResolution",
]

__version__ = "0.1.0"
