"""Entry point for ``python -m vdp_client``.

Runs the traffic-dumping command-line client. See :mod:`vdp_client.cli` for the full
command reference, or run ``python -m vdp_client --help``. The previous scripted demo is
now available as the ``demo`` subcommand (``python -m vdp_client --loopback demo``, or
simply ``python -m vdp_client demo``).
"""

from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    main()
