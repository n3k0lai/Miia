"""Optional live vehicle state from the Pi CMU harness shim (JSON file or env)."""

from __future__ import annotations

import json
import os
from pathlib import Path


def read_vehicle_state() -> dict | None:
    """
    Read current vehicle telemetry written by the harness daemon.

    Set HERMES_VEHICLE_STATE=/path/to/state.json with content like:
    {
      "timestamp": "2026-06-02T12:00:00Z",
      "ignition": "ON",
      "dtcs": ["U0100:00"],
      "pids": {"0C": 850, "05": 92},
      "can_frames_recent": 12
    }
    """
    path = os.environ.get("HERMES_VEHICLE_STATE")
    if not path:
        return None
    p = Path(path)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None