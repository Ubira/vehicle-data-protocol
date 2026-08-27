"""Unit tests for decoding the messages the server sends to the client."""

from vdp_client.codec import Writer
from vdp_client.constants import (
    ACK_BIT,
    CommandType,
    ErrorCode,
    MessageType,
    ProtocolErrorCode,
    SLOT_ID_ASYNC_ERROR,
    TimestampResolution,
)
from vdp_client.decode import (
    ControlResponse,
    DataMessage,
    ErrorMessage,
    VersionResponse,
    decode_message,
)


def _base(mt: MessageType, add: int = 0) -> Writer:
    return Writer().write_u8(((int(mt) & 0x07) << 5) | (add & 0x1F))


def test_decode_version_response():
    msg = _base(MessageType.VERSION).write_u8(0x01).write_u8(0x01).to_bytes()
    decoded = decode_message(msg)
    assert isinstance(decoded, VersionResponse)
    assert (decoded.main, decoded.minor) == (0x01, 0x01)


def test_decode_control_ack():
    ext = ((int(CommandType.ACTIVATION) & 0x07) << 5) | (1 << ACK_BIT)
    msg = _base(MessageType.CONTROL, add=5).write_u8(ext).to_bytes()
    decoded = decode_message(msg)
    assert isinstance(decoded, ControlResponse)
    assert decoded.ack
    assert decoded.con_sq_ct == 5
    assert decoded.command == CommandType.ACTIVATION


def test_decode_control_nack_with_errors():
    ext = (int(CommandType.ADD_CONFIG) & 0x07) << 5  # ACK bit clear
    w = _base(MessageType.CONTROL, add=2).write_u8(ext)
    w.write_ddle(99).write_u8(int(ErrorCode.UNKNOWN_DCA_REM_ID))
    decoded = decode_message(w.to_bytes())
    assert isinstance(decoded, ControlResponse)
    assert not decoded.ack
    assert decoded.errors[0].ref_id == 99
    assert decoded.errors[0].code == ErrorCode.UNKNOWN_DCA_REM_ID


def test_decode_data_message_reconstructs_timestamps():
    # Two samples for slot 1 at 10 ms resolution, 100 ms apart, ref_ts = 0 s.
    w = _base(MessageType.DATA, add=1).write_u32(0)
    # sample 1: slot 1, rel 0 ticks, len 4
    w.write_ddle(1).write_ddle(0).write_ddle(4).write_bytes(b"\x00\x00\x00\x00")
    # sample 2: slot 1, rel 10 ticks (= 100 ms at MS_10), len 4
    w.write_ddle(1).write_ddle(10).write_ddle(4).write_bytes(b"\x01\x00\x00\x00")
    decoded = decode_message(w.to_bytes(), {1: TimestampResolution.MS_10})
    assert isinstance(decoded, DataMessage)
    assert [s.timestamp_ms for s in decoded.samples] == [0, 100]
    assert decoded.samples[1].data == b"\x01\x00\x00\x00"


def test_decode_data_message_async_error():
    w = _base(MessageType.DATA, add=1).write_u32(0)
    w.write_ddle(SLOT_ID_ASYNC_ERROR).write_u8(int(ErrorCode.SAMPLING_ERROR))
    w.write_ddle(2).write_u16(3)  # info: referenced slot 3
    decoded = decode_message(w.to_bytes())
    assert isinstance(decoded, DataMessage)
    assert decoded.async_errors[0].slot_id == 3
    assert decoded.async_errors[0].code == ErrorCode.SAMPLING_ERROR


def test_decode_error_message_sequence_counter():
    w = _base(MessageType.ERROR).write_u8(int(ProtocolErrorCode.CONTROL_SEQUENCE_COUNTER))
    w.write_u8(1)  # expected CON_SQ_CT
    decoded = decode_message(w.to_bytes())
    assert isinstance(decoded, ErrorMessage)
    assert decoded.pec == ProtocolErrorCode.CONTROL_SEQUENCE_COUNTER
    assert decoded.expected_con_sq_ct == 1
