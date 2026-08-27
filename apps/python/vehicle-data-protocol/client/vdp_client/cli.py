"""Command-line VDP client (Proxy) that dumps all traffic.

A configurable CLI for driving a VDP Server: it sends the commands and payloads you
specify and prints **every** frame in both directions — requests it sends (``P -> S``)
and the responses, data and error messages the Server sends back (``S -> P``) — while
writing the same annotated dump (raw frames + translation) to a timestamped log file.

Two connection modes:

* **TCP** (``--host``/``--port``) — talk to a real VDP Server over the network.
* **Loopback** (``--loopback``) — spin up the real in-process ``vdp_server`` with a demo
  DCA Remote and an automatic clock, so the tool is fully demonstrable without a network
  server. Requires the sibling server package to be importable.

Usage examples::

    # one-shot: ask a server for its protocol version
    python -m vdp_client --host 127.0.0.1 --port 5000 version

    # loopback demo of scenarios S1-S3, dumping all traffic
    python -m vdp_client --loopback demo

    # interactive session against a loopback server
    python -m vdp_client --loopback interactive

    # send an arbitrary raw payload
    python -m vdp_client --host 10.0.0.5 --port 5000 raw --hex "01 00"
"""

from __future__ import annotations

import argparse
import os
import shlex
import sys
import threading
import time
from pathlib import Path
from typing import Optional, Sequence

from . import DpConfig, VdpClient
from .constants import TimestampResolution
from .traffic import Direction, TrafficLogger, default_log_name
from .transport import CallbackTransport, TcpClientTransport, Transport

_TRES_BY_MS = {
    1: TimestampResolution.MS_1,
    10: TimestampResolution.MS_10,
    100: TimestampResolution.MS_100,
    1000: TimestampResolution.S_1,
}

# Traffic dumps default to a 'logs' directory next to this package.
DEFAULT_LOG_DIR = Path(__file__).resolve().parent / "logs"


# --- transports --------------------------------------------------------------

class LoggingTransport(Transport):
    """Wraps a transport so every outbound frame is logged as ``P -> S``."""

    def __init__(self, inner: Transport, logger: TrafficLogger) -> None:
        super().__init__(inner.max_message_size)
        self._inner = inner
        self._logger = logger

    def send(self, data: bytes) -> None:
        self._logger.log(Direction.PROXY_TO_SERVER, data)
        self._inner.send(data)


# --- sessions ----------------------------------------------------------------

class Session:
    """Common surface: exposes a :class:`VdpClient` and streams inbound traffic."""

    client: VdpClient

    def start(self) -> None:  # pragma: no cover - trivial
        ...

    def close(self) -> None:  # pragma: no cover - trivial
        ...

    def __enter__(self) -> "Session":
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class TcpSession(Session):
    """Connects to a real VDP Server over TCP and pumps inbound frames."""

    def __init__(self, host: str, port: int, logger: TrafficLogger) -> None:
        self._logger = logger
        self._tcp = TcpClientTransport(host, port)
        self.client = VdpClient(LoggingTransport(self._tcp, logger))
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._tcp.connect()
        self._thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._thread.start()

    def _recv_loop(self) -> None:
        while not self._stop.is_set():
            try:
                msg = self._tcp.recv()
            except OSError:
                break
            if msg is None:
                break
            self._logger.log(Direction.SERVER_TO_PROXY, msg, self.client.slot_resolutions)
            self.client.handle(msg)

    def close(self) -> None:
        self._stop.set()
        self._tcp.close()
        if self._thread is not None:
            self._thread.join(timeout=1.0)


class LoopbackSession(Session):
    """Runs the real in-process ``vdp_server`` with an automatic clock.

    Lets the CLI exercise both traffic directions (including asynchronous cyclic data)
    without a network server. The server is driven from a background ticker thread; a
    lock serialises the client-driven ``receive`` and the ticker-driven ``tick`` because
    both mutate server state.
    """

    def __init__(self, logger: TrafficLogger, tick_ms: int = 100, dca_rem_id: int = 1) -> None:
        if not _add_server_to_path():
            raise RuntimeError(
                "Loopback mode needs the sibling 'vdp_server' package; it was not found. "
                "Install it or run against a real server with --host/--port."
            )
        from vdp_server.dca import DemoDcaRemote  # type: ignore
        from vdp_server.server import ServerConfig, VdpServer  # type: ignore
        from vdp_server.transport import CallbackTransport as ServerCallbackTransport  # type: ignore

        self._logger = logger
        self._tick_ms = tick_ms
        self._clock = {"ms": 0}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

        def server_to_client(msg: bytes) -> None:
            self._logger.log(Direction.SERVER_TO_PROXY, msg, self.client.slot_resolutions)
            self.client.handle(msg)

        server_transport = ServerCallbackTransport(
            ServerConfig().max_message_size, server_to_client
        )
        self._server = VdpServer(server_transport, clock_ms=lambda: self._clock["ms"])
        self._server.register_dca(DemoDcaRemote(dca_rem_id=dca_rem_id))

        # Outbound requests are delivered to the in-process server under the lock.
        def to_server(msg: bytes) -> None:
            with self._lock:
                self._server.receive(msg)

        self.client = VdpClient(LoggingTransport(CallbackTransport(to_server), logger))

    def start(self) -> None:
        self._thread = threading.Thread(target=self._tick_loop, daemon=True)
        self._thread.start()

    def _tick_loop(self) -> None:
        # Advance simulated time in real time so cyclic slots produce data messages.
        while not self._stop.wait(self._tick_ms / 1000.0):
            with self._lock:
                self._clock["ms"] += self._tick_ms
                self._server.tick()

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)


def _add_server_to_path() -> bool:
    """Add the sibling server package folder to ``sys.path`` if present."""
    here = os.path.dirname(os.path.abspath(__file__))
    vdp_root = os.path.abspath(os.path.join(here, "..", ".."))
    server_python = os.path.join(vdp_root, "server")
    if os.path.isdir(os.path.join(server_python, "vdp_server")):
        if server_python not in sys.path:
            sys.path.insert(0, server_python)
        return True
    return False


# --- slot spec parsing -------------------------------------------------------

def _parse_slot(spec: str) -> DpConfig:
    """Parse a ``--slot`` spec: ``id=1,tres=10,cyclic,sct=100,init_act,...``.

    Keys: id (required), tres (ms: 1/10/100/1000), cyclic, sct (ms), on_change,
    init_act, sec, persist, tx_on_sampling. Flags may appear bare (``cyclic``) or as
    ``key=1``/``key=0``. The transmission-cycle settings (``tx_cyclic``/``tct``) are
    request-level and are set with the ``add`` command's ``--tx-cyclic``/``--tct``
    options, not per slot.
    """
    fields: dict[str, str] = {}
    for token in spec.split(","):
        token = token.strip()
        if not token:
            continue
        key, _, value = token.partition("=")
        fields[key.strip().lower()] = value.strip()

    if "id" not in fields:
        raise argparse.ArgumentTypeError(f"slot spec '{spec}' is missing required 'id='")

    def flag(name: str) -> bool:
        if name not in fields:
            return False
        val = fields[name]
        return val == "" or val.lower() in {"1", "true", "yes", "on"}

    def num(name: str, default: int = 0) -> int:
        return int(fields[name]) if fields.get(name) else default

    tres_ms = num("tres", 1)
    if tres_ms not in _TRES_BY_MS:
        raise argparse.ArgumentTypeError(
            f"slot spec '{spec}': tres must be one of {sorted(_TRES_BY_MS)} (ms)"
        )

    return DpConfig(
        slot_id=int(fields["id"]),
        tres=_TRES_BY_MS[tres_ms],
        sec=flag("sec"),
        persist=flag("persist"),
        tx_on_sampling=flag("tx_on_sampling"),
        init_act=flag("init_act"),
        on_change=flag("on_change"),
        cyclic=flag("cyclic"),
        sct_ms=num("sct"),
    )


def _parse_hex(text: str) -> bytes:
    cleaned = text.replace("0x", "").replace(",", " ").replace("-", " ")
    cleaned = cleaned.replace(":", " ").strip()
    compact = "".join(cleaned.split())
    if len(compact) % 2 != 0:
        raise argparse.ArgumentTypeError(f"hex payload '{text}' has an odd number of digits")
    try:
        return bytes.fromhex(compact)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid hex payload '{text}': {exc}") from exc


# --- command dispatch --------------------------------------------------------

def _dispatch(session: Session, args: argparse.Namespace) -> None:
    """Send the request(s) described by ``args`` on ``session``."""
    client = session.client
    cmd = args.command
    if cmd == "version":
        client.request_version()
    elif cmd == "add":
        client.add_config(
            dca_rem_id=args.dca,
            dps=list(args.slot),
            tx_cyclic=args.tx_cyclic,
            tct_ms=args.tct,
        )
    elif cmd == "activate":
        client.activate(args.slots)
    elif cmd == "deactivate":
        client.deactivate(args.slots)
    elif cmd == "trigger":
        client.trigger_transmission(args.slots or None)
    elif cmd == "sample":
        client.trigger_sampling(args.slots)
    elif cmd == "remove":
        if args.all:
            client.remove_all()
        elif args.cyclic_tx:
            client.remove_cyclic_tx()
        elif args.dcas:
            client.remove_dcas(args.dcas)
        elif args.slots:
            client.remove_slots(args.slots)
        else:
            print("remove: specify --slots, --dcas, --all or --cyclic-tx", file=sys.stderr)
    elif cmd == "raw":
        client._transport.send(args.hex)  # deliberately bypasses higher-level API
    elif cmd == "listen":
        pass  # nothing to send; just observe


# --- interactive REPL --------------------------------------------------------

_REPL_HELP = """\
Commands (all traffic is printed and logged):
  version                          send a version request
  add DCA SLOTSPEC [SLOTSPEC...]   add config, e.g.  add 1 id=1,cyclic,sct=100,tres=10,init_act
  activate SLOT [SLOT...]          activate slots
  deactivate SLOT [SLOT...]        deactivate slots
  trigger [SLOT...]                transmission trigger (optionally sampling SLOTs too)
  sample SLOT [SLOT...]            on-request sampling trigger
  remove slots SLOT... | dcas ID... | all | cyclic-tx
  raw HEX                          send a raw payload, e.g.  raw 01 00
  wait SECONDS                     just listen for inbound traffic
  help                             show this help
  quit / exit                      leave
"""


def _repl(session: Session) -> None:
    client = session.client
    print(_REPL_HELP)
    while True:
        try:
            line = input("vdp> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not line:
            continue
        try:
            parts = shlex.split(line)
        except ValueError as exc:
            print(f"parse error: {exc}", file=sys.stderr)
            continue
        verb, rest = parts[0].lower(), parts[1:]
        try:
            if verb in {"quit", "exit"}:
                return
            if verb == "help":
                print(_REPL_HELP)
            elif verb == "version":
                client.request_version()
            elif verb == "add":
                dca = int(rest[0])
                dps = [_parse_slot(s) for s in rest[1:]]
                if not dps:
                    print("add: need at least one slot spec", file=sys.stderr)
                    continue
                client.add_config(dca_rem_id=dca, dps=dps)
            elif verb == "activate":
                client.activate([int(x) for x in rest])
            elif verb == "deactivate":
                client.deactivate([int(x) for x in rest])
            elif verb == "trigger":
                client.trigger_transmission([int(x) for x in rest] or None)
            elif verb == "sample":
                client.trigger_sampling([int(x) for x in rest])
            elif verb == "remove":
                _repl_remove(client, rest)
            elif verb == "raw":
                client._transport.send(_parse_hex(" ".join(rest)))
            elif verb == "wait":
                time.sleep(float(rest[0]) if rest else 1.0)
            else:
                print(f"unknown command: {verb} (try 'help')", file=sys.stderr)
        except (ValueError, IndexError, argparse.ArgumentTypeError) as exc:
            print(f"error: {exc}", file=sys.stderr)


def _repl_remove(client: VdpClient, rest: list[str]) -> None:
    if not rest:
        print("remove: slots|dcas|all|cyclic-tx", file=sys.stderr)
        return
    what = rest[0].lower()
    if what == "all":
        client.remove_all()
    elif what in {"cyclic-tx", "cyclic_tx"}:
        client.remove_cyclic_tx()
    elif what == "slots":
        client.remove_slots([int(x) for x in rest[1:]])
    elif what == "dcas":
        client.remove_dcas([int(x) for x in rest[1:]])
    else:
        print("remove: slots|dcas|all|cyclic-tx", file=sys.stderr)


# --- scripted loopback demo --------------------------------------------------

def _run_demo(logger: TrafficLogger) -> None:
    """Drive the real in-process server through scenarios S1-S3, dumping all traffic."""
    session = LoopbackSession(logger, tick_ms=100)
    client = session.client
    with session:
        logger.note("S1: query protocol version")
        client.request_version()

        logger.note("S2/S3: add a cyclic slot (100 ms) with initial activation ON")
        client.add_config(
            dca_rem_id=1,
            dps=[
                DpConfig(
                    slot_id=1,
                    cyclic=True,
                    sct_ms=100,
                    init_act=True,
                    tres=TimestampResolution.MS_10,
                )
            ],
        )

        logger.note("Sample cyclically for ~500 ms, then pull the buffered data")
        time.sleep(0.55)
        client.trigger_transmission()
        time.sleep(0.1)

        logger.note("Deactivate slot 1")
        client.deactivate([1])
        time.sleep(0.1)


# --- argument parsing --------------------------------------------------------

def _slots_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--slots", nargs="*", type=int, default=[], metavar="SLOT",
        help="slot IDs to act on",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vdp-client",
        description="VDP client (Proxy) CLI: send configurable commands and dump all traffic.",
    )
    parser.add_argument("--host", help="server host for a TCP connection")
    parser.add_argument("--port", type=int, help="server port for a TCP connection")
    parser.add_argument(
        "--loopback", action="store_true",
        help="talk to an in-process demo server instead of a TCP peer",
    )
    parser.add_argument(
        "--log-dir", default=str(DEFAULT_LOG_DIR),
        help="directory for the traffic dump (default: the package 'logs' folder)",
    )
    parser.add_argument(
        "--log-file", help="explicit log file path (overrides --log-dir naming)",
    )
    parser.add_argument("--no-color", action="store_true", help="disable coloured output")
    parser.add_argument(
        "--listen", type=float, default=2.0, metavar="SECONDS",
        help="one-shot commands: seconds to keep receiving after sending (default: 2)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("version", help="send a version request")

    p_add = sub.add_parser("add", help="add a dynamic configuration")
    p_add.add_argument("--dca", type=int, required=True, help="DCA Remote ID")
    p_add.add_argument(
        "--slot", action="append", required=True, type=_parse_slot, metavar="SPEC",
        help="slot spec 'id=1,tres=10,cyclic,sct=100,init_act' (repeatable)",
    )
    p_add.add_argument(
        "--tx-cyclic", dest="tx_cyclic", action="store_true",
        help="request cyclic transmission (uses --tct)",
    )
    p_add.add_argument(
        "--tct", type=int, default=0, metavar="MS",
        help="transmission cycle time in ms (with --tx-cyclic)",
    )

    p_act = sub.add_parser("activate", help="activate slots")
    _slots_arg(p_act)
    p_deact = sub.add_parser("deactivate", help="deactivate slots")
    _slots_arg(p_deact)

    p_trig = sub.add_parser("trigger", help="transmission trigger (flush buffered data)")
    _slots_arg(p_trig)
    p_samp = sub.add_parser("sample", help="on-request sampling trigger")
    _slots_arg(p_samp)

    p_rem = sub.add_parser("remove", help="remove configuration")
    _slots_arg(p_rem)
    p_rem.add_argument("--dcas", nargs="*", type=int, default=[], help="DCA Remote IDs to remove")
    p_rem.add_argument("--all", action="store_true", help="remove all configurations")
    p_rem.add_argument("--cyclic-tx", action="store_true", help="remove cyclic transmission mode")

    p_raw = sub.add_parser("raw", help="send a raw payload")
    p_raw.add_argument("--hex", required=True, type=_parse_hex, help="payload as hex, e.g. '01 00'")

    sub.add_parser("listen", help="connect and only observe inbound traffic")
    sub.add_parser("interactive", help="interactive REPL session")
    sub.add_parser("demo", help="scripted loopback demo of scenarios S1-S3")

    return parser


def _resolve_log_path(args: argparse.Namespace) -> Path:
    if args.log_file:
        return Path(args.log_file)
    return Path(args.log_dir) / default_log_name()


def _make_session(args: argparse.Namespace, logger: TrafficLogger) -> Session:
    if args.loopback:
        return LoopbackSession(logger)
    if not args.host or not args.port:
        raise SystemExit("error: TCP mode requires --host and --port (or use --loopback)")
    return TcpSession(args.host, args.port, logger)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = _build_parser().parse_args(argv)
    if not args.loopback and args.command != "demo" and (not args.host or not args.port):
        raise SystemExit("error: TCP mode requires --host and --port (or use --loopback)")

    log_path = _resolve_log_path(args)
    logger = TrafficLogger(log_path, echo=True, color=not args.no_color)
    print(f"Logging VDP traffic to {log_path}\n")

    with logger:
        if args.command == "demo":
            _run_demo(logger)
            return

        session = _make_session(args, logger)
        with session:
            _dispatch(session, args)
            if args.command == "interactive":
                _repl(session)
            else:
                # Keep receiving so responses / data messages are captured.
                try:
                    time.sleep(args.listen)
                except KeyboardInterrupt:
                    pass


def demo() -> None:
    """Console-script entry point for the scripted loopback demo."""
    main(["demo"])


if __name__ == "__main__":
    main()
