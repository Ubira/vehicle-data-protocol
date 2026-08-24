"""Integration tests grounded in the documented scenarios (docs/scenarios)."""

from vdp_server import proxy
from vdp_server.codec import Reader
from vdp_server.constants import (
    ACK_BIT,
    ErrorCode,
    MessageType,
    PROTOCOL_VERSION_MAIN,
    PROTOCOL_VERSION_MINOR,
    ProtocolErrorCode,
    SLOT_ID_ASYNC_ERROR,
    TimestampResolution,
)
from vdp_server.header import decode_base_header


def _mt(message: bytes) -> MessageType:
    return decode_base_header(Reader(message)).mt


def _is_ack(response: bytes) -> bool:
    return bool((response[1] >> ACK_BIT) & 1)


def test_s1_version_query(harness):
    harness.server.receive(proxy.version_request())
    (resp,) = harness.pop_all()
    reader = Reader(resp)
    assert decode_base_header(reader).mt == MessageType.VERSION
    assert reader.read_u8() == PROTOCOL_VERSION_MAIN
    assert reader.read_u8() == PROTOCOL_VERSION_MINOR


def test_s2_add_config_ack(harness):
    add = proxy.add_config(1, dca_rem_id=1, dps=[proxy.DpConfig(slot_id=1, cyclic=True, sct_ms=100)])
    harness.server.receive(add)
    (resp,) = harness.pop_all()
    assert _mt(resp) == MessageType.CONTROL
    assert _is_ack(resp)
    assert harness.server.ctx.slots.exists(1)


def test_s2_add_config_unknown_dca_nack(harness):
    add = proxy.add_config(1, dca_rem_id=99, dps=[proxy.DpConfig(slot_id=1)])
    harness.server.receive(add)
    (resp,) = harness.pop_all()
    assert not _is_ack(resp)
    reader = Reader(resp)
    decode_base_header(reader)
    reader.read_u8()  # extended header
    assert reader.read_ddle() == 99
    assert reader.read_u8() == ErrorCode.UNKNOWN_DCA_REM_ID


def test_s3_cyclic_sampling_with_init_act(harness):
    add = proxy.add_config(
        1,
        dca_rem_id=1,
        dps=[proxy.DpConfig(slot_id=1, cyclic=True, sct_ms=100, init_act=True, tres=TimestampResolution.MS_10)],
    )
    harness.server.receive(add)
    harness.pop_all()

    for _ in range(5):
        harness.advance(100)

    # Pull the buffered samples via a transmission trigger.
    harness.server.receive(proxy.trigger(2, tx_trigger=True, slot_ids=[]))
    messages = harness.pop_all()
    assert _mt(messages[0]) == MessageType.CONTROL  # trigger response first
    data = [m for m in messages if _mt(m) == MessageType.DATA]
    assert data, "expected a data message after the trigger response"


def test_s4_init_act_off_then_activate(harness):
    add = proxy.add_config(1, dca_rem_id=1, dps=[proxy.DpConfig(slot_id=1, cyclic=True, sct_ms=100, init_act=False)])
    harness.server.receive(add)
    harness.pop_all()
    harness.advance(300)
    assert len(harness.server.ctx.buffer) == 0  # no sampling while inactive

    harness.server.receive(proxy.activation(2, activate=True, slot_ids=[1]))
    harness.pop_all()
    harness.advance(300)
    assert len(harness.server.ctx.buffer) > 0


def test_s5_on_request_sampling(harness):
    add = proxy.add_config(1, dca_rem_id=1, dps=[proxy.DpConfig(slot_id=5)])  # no auto sampling
    harness.server.receive(add)
    harness.pop_all()
    harness.advance(500)
    assert len(harness.server.ctx.buffer) == 0

    harness.server.receive(proxy.trigger(2, tx_trigger=False, slot_ids=[5]))
    (resp,) = harness.pop_all()
    assert _is_ack(resp)
    assert len(harness.server.ctx.buffer) == 1


def test_s10_remove_all(harness):
    harness.server.receive(proxy.add_config(1, 1, [proxy.DpConfig(slot_id=1)]))
    harness.pop_all()
    harness.server.receive(proxy.remove_all(2))
    (resp,) = harness.pop_all()
    assert _is_ack(resp)
    assert not harness.server.ctx.slots.exists(1)


def test_s11_lost_control_message_sequence_error(harness):
    # Expected CON_SQ_CT is 1; send 5 instead.
    harness.server.receive(proxy.add_config(5, 1, [proxy.DpConfig(slot_id=1)]))
    (resp,) = harness.pop_all()
    assert _mt(resp) == MessageType.ERROR
    reader = Reader(resp)
    decode_base_header(reader)
    assert reader.read_u8() == ProtocolErrorCode.CONTROL_SEQUENCE_COUNTER
    assert reader.read_u8() == 1  # expected counter


def test_s12_malformed_request_error_message(harness):
    # Activation with an empty payload is malformed (incorrect number of bytes).
    harness.server.receive(proxy.activation(1, activate=True, slot_ids=[]))
    (resp,) = harness.pop_all()
    assert _mt(resp) == MessageType.ERROR
    reader = Reader(resp)
    decode_base_header(reader)
    assert reader.read_u8() == ProtocolErrorCode.INCORRECT_NUMBER_OF_BYTES


def test_s13_async_sampling_error_in_data_message(harness):
    harness.server.receive(proxy.add_config(1, 1, [proxy.DpConfig(slot_id=3)]))
    harness.pop_all()
    harness.server.report_async_error(3, ErrorCode.SAMPLING_ERROR)
    harness.server.receive(proxy.trigger(2, tx_trigger=True, slot_ids=[]))
    data = [m for m in harness.pop_all() if _mt(m) == MessageType.DATA]
    assert data
    reader = Reader(data[0])
    decode_base_header(reader)
    reader.read_u32()  # REF_TS
    assert reader.read_ddle() == SLOT_ID_ASYNC_ERROR
    assert reader.read_u8() == ErrorCode.SAMPLING_ERROR


def test_sequence_counter_wraps(harness):
    # Drive 31 accepted control requests; the 32nd expected counter wraps back to 1.
    seq = 1
    for _ in range(31):
        harness.server.receive(proxy.trigger(seq, tx_trigger=True, slot_ids=[]))
        harness.pop_all()
        seq = 1 if seq >= 31 else seq + 1
    assert harness.server._dispatcher.expected_con_sq_ct == 1


def test_duplicate_slot_in_message_is_protocol_error(harness):
    add = proxy.add_config(
        1, 1, [proxy.DpConfig(slot_id=7), proxy.DpConfig(slot_id=7)]
    )
    harness.server.receive(add)
    (resp,) = harness.pop_all()
    assert _mt(resp) == MessageType.ERROR
    reader = Reader(resp)
    decode_base_header(reader)
    assert reader.read_u8() == ProtocolErrorCode.DUPLICATED_SLOT_ID
