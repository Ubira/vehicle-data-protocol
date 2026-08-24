"""Base header (de)serialisation — re-exported from the shared protocol core.

See :mod:`vdp_common.header`; exposed here under ``vdp_client.header`` for a stable,
role-local import surface.
"""

from __future__ import annotations

from vdp_common.header import BaseHeader, decode_base_header

__all__ = ["BaseHeader", "decode_base_header"]
