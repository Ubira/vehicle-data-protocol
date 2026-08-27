"""Decoders for the messages the server sends to the client.

The server emits four message kinds toward the Proxy:

* **Version response** (``MT=0``) -> :class:`VersionResponse`.
* **Control response** (``MT=1``) -> :class:`ControlResponse` (``ACK`` + per-slot/DCA
  error codes).
* **Data message** (``MT=2``) -> :class:`DataMessage` (reference timestamp, samples with
  reconstructed absolute times, and embedded asynchronous errors).
* **Error message** (``MT=3``) -> :class:`ErrorMessage` (protocol error code).

Reconstructing absolute sample times needs the per-slot timestamp resolution ``TRES``.
Provide a ``slot_tres`` mapping (the client records this from the add requests it sent);
unknown slots fall back to millisecond resolution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Union

from .codec import DecodeError, Reader, reconstruct_timestamp
from .constants import (
    ACK_BIT,
    CommandType,
    CT_MASK,
    CT_SHIFT,
    ErrorCode,
    MessageType,
    ProtocolErrorCode,
    SLOT_ID_ASYNC_ERROR,
    TimestampResolution,
)
from .header import decode_base_header


@dataclass(frozen=True)
class VersionResponse:
    main: int
    minor: int


@dataclass(frozen=True)
class SlotErrorInfo:
    ref_id: int  # slot ID or DCA Remote ID
    code: ErrorCode


@dataclass(frozen=True)
class ControlResponse:
    con_sq_ct: int
    command: CommandType
    ack: bool
    errors: list[SlotErrorInfo] = field(default_factory=list)


@dataclass(frozen=True)
class DataPointSample:
    slot_id: int
    timestamp_ms: int
    data: bytes


@dataclass(frozen=True)
class DataAsyncError:
    slot_id: int
    code: ErrorCode
    info: bytes = b""


@dataclass(frozen=True)
class DataMessage:
    seq_ct: int
    ref_ts_s: int
    samples: list[DataPointSample] = field(default_factory=list)
    async_errors: list[DataAsyncError] = field(default_factory=list)


@dataclass(frozen=True)
class ErrorMessage:
    pec: ProtocolErrorCode
    info: bytes = b""

    @property
    def expected_con_sq_ct(self) -> int | None:
        """For ``PEC=0`` the info carries the expected control sequence counter."""
        if self.pec == ProtocolErrorCode.CONTROL_SEQUENCE_COUNTER and self.info:
            return self.info[0] & 0x1F
        return None


Decoded = Union[VersionResponse, ControlResponse, DataMessage, ErrorMessage]


def _decode_version(reader: Reader) -> VersionResponse:
    main = reader.read_u8()
    minor = reader.read_u8()
    return VersionResponse(main=main, minor=minor)


def _decode_control_response(con_sq_ct: int, reader: Reader) -> ControlResponse:
    ext = reader.read_u8()
    command = CommandType((ext >> CT_SHIFT) & CT_MASK)
    ack = bool((ext >> ACK_BIT) & 1)
    errors: list[SlotErrorInfo] = []
    if not ack:
        while not reader.at_end():
            ref_id = reader.read_ddle()
            code = reader.read_u8()
            errors.append(SlotErrorInfo(ref_id=ref_id, code=_as_error_code(code)))
    return ControlResponse(con_sq_ct=con_sq_ct, command=command, ack=ack, errors=errors)


def _decode_data_message(
    seq_ct: int,
    reader: Reader,
    slot_tres: Mapping[int, TimestampResolution],
) -> DataMessage:
    ref_ts_s = reader.read_u32()
    samples: list[DataPointSample] = []
    async_errors: list[DataAsyncError] = []
    previous_ms = ref_ts_s * 1000

    while not reader.at_end():
        slot_id = reader.read_ddle()
        if slot_id == SLOT_ID_ASYNC_ERROR:
            code = reader.read_u8()
            length = reader.read_ddle()
            payload = reader.read_bytes(length)
            if len(payload) < 2:
                raise DecodeError("async error info too short")
            ref_slot = int.from_bytes(payload[:2], "little")
            async_errors.append(
                DataAsyncError(
                    slot_id=ref_slot, code=_as_error_code(code), info=payload[2:]
                )
            )
            continue
        ticks = reader.read_ddle()
        length = reader.read_ddle()
        data = reader.read_bytes(length)
        tres = slot_tres.get(slot_id, TimestampResolution.MS_1)
        timestamp_ms = reconstruct_timestamp(ticks, previous_ms, tres)
        samples.append(DataPointSample(slot_id=slot_id, timestamp_ms=timestamp_ms, data=data))
        previous_ms = timestamp_ms

    return DataMessage(
        seq_ct=seq_ct, ref_ts_s=ref_ts_s, samples=samples, async_errors=async_errors
    )


def _decode_error_message(reader: Reader) -> ErrorMessage:
    err_byte = reader.read_u8()
    pec_value = err_byte & 0x1F
    try:
        pec = ProtocolErrorCode(pec_value)
    except ValueError:
        pec = ProtocolErrorCode.INVALID_OPTIONS  # unknown/reserved -> treat generically
    info = reader.read_bytes(reader.remaining())
    return ErrorMessage(pec=pec, info=info)


def _as_error_code(value: int) -> ErrorCode:
    try:
        return ErrorCode(value)
    except ValueError:
        return ErrorCode.GENERIC_REMOTE


def decode_message(
    message: bytes,
    slot_tres: Mapping[int, TimestampResolution] | None = None,
) -> Decoded:
    """Decode one inbound VDP message from the server."""
    reader = Reader(message)
    header = decode_base_header(reader)
    if header.mt == MessageType.VERSION:
        return _decode_version(reader)
    if header.mt == MessageType.CONTROL:
        return _decode_control_response(header.add, reader)
    if header.mt == MessageType.DATA:
        return _decode_data_message(header.add, reader, slot_tres or {})
    return _decode_error_message(reader)
