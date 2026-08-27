"""Human-readable translation and dual (terminal + file) logging of VDP traffic.

This module turns raw VDP frames into an annotated, human-readable form and records
every frame that crosses the wire — in **both** directions:

* ``P -> S`` — requests the Proxy (this client) sends to a Server, and
* ``S -> P`` — the version/control responses, data messages and error messages a
  Server sends back.

Each logged entry pairs the **raw bytes** (spaced hex) with their **translation** so a
traffic dump can be read without a separate decoder. The same rendering is echoed to the
terminal and appended to a log file (see :class:`TrafficLogger`).

Outbound *requests* and inbound *responses* share message types (``VERSION``/``CONTROL``)
but not their body layout, so the translator is direction-aware: :func:`translate`
dispatches to the request decoder for ``P -> S`` and to the shared response decoder
(:func:`vdp_client.decode.decode_message`) for ``S -> P``.
"""

from __future__ import annotations

import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Mapping, Optional, TextIO

from .codec import DecodeError, Reader
from .constants import (
    ACK_BIT,
    ACT_BIT,
    ADD_TCYCLIC_BIT,
    COL_SCHANGE_BIT,
    COL_SCYCLIC_BIT,
    CommandType,
    CT_MASK,
    CT_SHIFT,
    MessageType,
    REMOVE_DCA_REM_BIT,
    REMOVE_GLOBAL_BIT,
    REMOVE_T_CYCLIC_BIT,
    SET_INIT_ACT_BIT,
    SET_PERSIST_BIT,
    SET_SEC_BIT,
    SET_TRES_MASK,
    SET_TRES_SHIFT,
    SET_TXMODE_ON_SAMPLING_BIT,
    TRES_TO_MS,
    TX_TRIG_BIT,
    TimestampResolution,
)
from .decode import (
    ControlResponse,
    DataMessage,
    ErrorMessage,
    VersionResponse,
    decode_message,
)
from .header import decode_base_header

__all__ = ["Direction", "translate", "summary_line", "TrafficLogger", "default_log_name"]


class Direction(Enum):
    """Which way a frame travels, relative to this Proxy (client)."""

    PROXY_TO_SERVER = "P -> S"  # outbound request we send
    SERVER_TO_PROXY = "S -> P"  # inbound response / data / error


# --- ANSI colours (terminal only) --------------------------------------------
_RESET = "\033[0m"
_COLORS = {
    Direction.PROXY_TO_SERVER: "\033[36m",  # cyan
    Direction.SERVER_TO_PROXY: "\033[32m",  # green
}
_ERROR_COLOR = "\033[31m"  # red


def default_log_name(now: Optional[datetime] = None) -> str:
    """Return a log file name starting with the timestamp ``YY-MM-DD_HH-MM-SS``."""
    now = now or datetime.now()
    return now.strftime("%y-%m-%d_%H-%M-%S_vdp-traffic-dump.log")


def _hex(data: bytes) -> str:
    return data.hex(" ") if data else "(empty)"


def _add_label(mt: MessageType) -> str:
    """Name of the 5-bit ADD context field for the given message type."""
    if mt == MessageType.CONTROL:
        return "CON_SQ_CT"
    if mt == MessageType.DATA:
        return "SQ_CT"
    return "reserved"


def _render_raw(message: bytes) -> list[str]:
    """Break a raw frame into its base header (MT + ADD) and payload, as hex."""
    if not message:
        return ["  raw: (empty)"]
    header_byte = message[0]
    mt_value = (header_byte >> 5) & 0x07
    add = header_byte & 0x1F
    reserved = (header_byte >> 7) & 1
    try:
        mt_name = MessageType(mt_value).name
        add_name = _add_label(MessageType(mt_value))
    except ValueError:  # MT is 3 bits so this cannot happen, but stay defensive
        mt_name = "?"
        add_name = "ADD"
    payload = message[1:]
    return [
        "  raw:",
        f"    header : 0x{header_byte:02x}"
        f"  (MT={mt_name}[{mt_value}]  {add_name}(ADD)={add})",
        f"    payload: 0x{_hex(payload)}",
    ]



# --- request (Proxy -> Server) translation -----------------------------------

def _tres_ms(tres_value: int) -> str:
    try:
        return f"{TRES_TO_MS[TimestampResolution(tres_value)]}ms"
    except (ValueError, KeyError):
        return f"?({tres_value})"


def _translate_add_config(ext: int, reader: Reader) -> list[str]:
    lines: list[str] = []
    tx_cyclic = bool((ext >> ADD_TCYCLIC_BIT) & 1)
    if tx_cyclic:
        tct = reader.read_u16()
        lines.append(f"  tx_cyclic=1 TCT={tct}ms")
    dca_rem_id = reader.read_ddle()
    count = reader.read_ddle()
    lines.append(f"  DCA_REM_ID={dca_rem_id}  data_points={count}")
    for _ in range(count):
        slot_id = reader.read_ddle()
        set_byte = reader.read_u8()
        col_byte = reader.read_u8()
        cyclic = bool((col_byte >> COL_SCYCLIC_BIT) & 1)
        on_change = bool((col_byte >> COL_SCHANGE_BIT) & 1)
        sct = reader.read_u16() if cyclic else None
        cfg_len = reader.read_ddle()
        cfg = reader.read_bytes(cfg_len)
        lines.append(
            f"  slot {slot_id}: TRES={_tres_ms((set_byte & SET_TRES_MASK) >> SET_TRES_SHIFT)}"
            f" SEC={(set_byte >> SET_SEC_BIT) & 1}"
            f" PERSIST={(set_byte >> SET_PERSIST_BIT) & 1}"
            f" TX_ON_SAMPLING={(set_byte >> SET_TXMODE_ON_SAMPLING_BIT) & 1}"
            f" INIT_ACT={(set_byte >> SET_INIT_ACT_BIT) & 1}"
        )
        detail = (
            f"          on_change={int(on_change)} cyclic={int(cyclic)}"
            + (f" SCT={sct}ms" if sct is not None else "")
            + f" dca_config={_hex(cfg)}"
        )
        lines.append(detail)
    return lines


def _translate_remove(ext: int, reader: Reader) -> list[str]:
    if (ext >> REMOVE_GLOBAL_BIT) & 1:
        return ["  REMOVE all configurations (global)"]
    if (ext >> REMOVE_T_CYCLIC_BIT) & 1:
        return ["  REMOVE cyclic transmission mode"]
    ids = _read_id_list(reader)
    if (ext >> REMOVE_DCA_REM_BIT) & 1:
        return [f"  REMOVE DCA Remotes: {ids or '(none)'}"]
    return [f"  REMOVE slots: {ids or '(none)'}"]


def _read_id_list(reader: Reader) -> list[int]:
    ids: list[int] = []
    while not reader.at_end():
        ids.append(reader.read_ddle())
    return ids


def _translate_control_request(con_sq_ct: int, reader: Reader) -> list[str]:
    ext = reader.read_u8()
    command = CommandType((ext >> CT_SHIFT) & CT_MASK)
    head = f"CT={command.name}  CON_SQ_CT={con_sq_ct}"
    if command == CommandType.ADD_CONFIG:
        return [head, *_translate_add_config(ext, reader)]
    if command == CommandType.REMOVE_CONFIG:
        return [head, *_translate_remove(ext, reader)]
    if command == CommandType.ACTIVATION:
        activate = bool((ext >> ACT_BIT) & 1)
        verb = "ACTIVATE" if activate else "DEACTIVATE"
        return [head, f"  {verb} slots: {_read_id_list(reader) or '(all)'}"]
    # TRIGGER
    tx = bool((ext >> TX_TRIG_BIT) & 1)
    kind = "transmission trigger" if tx else "sampling trigger"
    return [head, f"  {kind}; slots: {_read_id_list(reader) or '(none)'}"]


def _translate_request(message: bytes) -> list[str]:
    reader = Reader(message)
    header = decode_base_header(reader)
    if header.mt == MessageType.VERSION:
        return ["VERSION request (no payload)"]
    if header.mt == MessageType.CONTROL:
        return _translate_control_request(header.add, reader)
    # A Proxy should never send DATA/ERROR; show it generically if it happens.
    return [f"{header.mt.name} message (unexpected from Proxy)"]


# --- response (Server -> Proxy) translation ----------------------------------

def _translate_response(message: bytes, slot_tres: Mapping[int, TimestampResolution]) -> list[str]:
    decoded = decode_message(message, slot_tres)
    if isinstance(decoded, VersionResponse):
        return [f"VERSION response: main={decoded.main:#04x} minor={decoded.minor:#04x}"]
    if isinstance(decoded, ControlResponse):
        status = "ACK" if decoded.ack else "NACK"
        lines = [f"CONTROL response: CT={decoded.command.name} CON_SQ_CT={decoded.con_sq_ct} {status}"]
        for err in decoded.errors:
            lines.append(f"  ref_id={err.ref_id} error={err.code.name} ({err.code.value:#04x})")
        return lines
    if isinstance(decoded, DataMessage):
        lines = [
            f"DATA message: SQ_CT={decoded.seq_ct} REF_TS={decoded.ref_ts_s}s"
            f" samples={len(decoded.samples)} async_errors={len(decoded.async_errors)}"
        ]
        for s in decoded.samples:
            lines.append(f"  slot {s.slot_id} @ {s.timestamp_ms}ms = {_hex(s.data)}")
        for e in decoded.async_errors:
            lines.append(
                f"  async error slot {e.slot_id}: {e.code.name}"
                f" ({e.code.value:#04x}) info={_hex(e.info)}"
            )
        return lines
    if isinstance(decoded, ErrorMessage):
        expected = decoded.expected_con_sq_ct
        extra = f" expected_CON_SQ_CT={expected}" if expected is not None else ""
        return [f"ERROR message: PEC={decoded.pec.name} ({decoded.pec.value:#04x}) info={_hex(decoded.info)}{extra}"]
    return ["(undecodable)"]


def translate(
    message: bytes,
    direction: Direction,
    slot_tres: Optional[Mapping[int, TimestampResolution]] = None,
) -> list[str]:
    """Return the human-readable translation of ``message`` for the given direction."""
    try:
        if direction == Direction.PROXY_TO_SERVER:
            return _translate_request(message)
        return _translate_response(message, slot_tres or {})
    except (DecodeError, ValueError, IndexError) as exc:
        return [f"(could not decode: {exc})"]


def summary_line(message: bytes, direction: Direction) -> str:
    """Return a short one-line summary (message type) for the frame."""
    if not message:
        return "empty frame"
    try:
        mt = MessageType((message[0] >> 5) & 0x07)
    except ValueError:
        return "unknown frame"
    suffix = "request" if direction == Direction.PROXY_TO_SERVER else "response/message"
    return f"{mt.name} {suffix}"


class TrafficLogger:
    """Renders VDP frames (raw + translation) to the terminal and a log file.

    Every call to :meth:`log` writes one annotated block to both sinks. The log file is
    plain text; terminal output may be coloured by direction. Instances are usable as a
    context manager so the file is always flushed and closed.
    """

    _SEP = "-" * 78

    def __init__(
        self,
        log_path: str | Path,
        *,
        echo: bool = True,
        color: bool = True,
        stream: TextIO = sys.stdout,
    ) -> None:
        self.path = Path(log_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("w", encoding="utf-8")
        self._echo = echo
        self._stream = stream
        self._color = color and hasattr(stream, "isatty") and stream.isatty()
        self._write_header()

    def _write_header(self) -> None:
        started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = [
            "VDP traffic dump",
            f"started: {started}",
            "direction legend: 'P -> S' = Proxy(client)->Server request, "
            "'S -> P' = Server->Proxy response/data/error",
            self._SEP,
        ]
        block = "\n".join(header) + "\n"
        self._file.write(block)
        self._file.flush()
        if self._echo:
            self._stream.write(block)
            self._stream.flush()

    def log(
        self,
        direction: Direction,
        message: bytes,
        slot_tres: Optional[Mapping[int, TimestampResolution]] = None,
    ) -> None:
        """Record one frame with its raw bytes and translation, in both sinks."""
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        lines = translate(message, direction, slot_tres)
        head = (
            f"[{ts}] {direction.value} | {summary_line(message, direction)}"
            f" | {len(message)} bytes"
        )
        body = [*_render_raw(message), "  translation:", *(f"  {ln}" for ln in lines)]

        plain = "\n".join([head, *body, self._SEP]) + "\n"
        self._file.write(plain)
        self._file.flush()

        if self._echo:
            if self._color:
                is_error = any("ERROR message" in ln or "NACK" in ln for ln in lines)
                col = _ERROR_COLOR if is_error else _COLORS.get(direction, "")
                colored = "\n".join([f"{col}{head}{_RESET}", *body, self._SEP]) + "\n"
                self._stream.write(colored)
            else:
                self._stream.write(plain)
            self._stream.flush()

    def note(self, text: str) -> None:
        """Write a free-form annotation line to both sinks (e.g. a scenario title)."""
        line = f"# {text}\n"
        self._file.write(line)
        self._file.flush()
        if self._echo:
            self._stream.write(line)
            self._stream.flush()

    def close(self) -> None:
        if not self._file.closed:
            self._file.flush()
            self._file.close()

    def __enter__(self) -> "TrafficLogger":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
