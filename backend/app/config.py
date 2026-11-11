"""Central configuration. All assumptions about the brief live here."""
from datetime import date
from zoneinfo import ZoneInfo

LONDON = ZoneInfo("Europe/London")

# Purchase decisions are made in January 2026 (decision date = the day the buyer acts, D-1).
DECISION_MIN = date(2026, 1, 1)
DECISION_MAX = date(2026, 1, 31)

# Day-ahead gate closures (UK local time). Assumptions - configurable in the UI.
CUTOFF_PRESETS = {
    "09:20": "Hourly day-ahead auction (assumed 09:20 UK)",
    "15:30": "Half-hourly day-ahead auction (assumed 15:30 UK)",
}
DEFAULT_CUTOFF = "09:20"

# Only forecasts published up to this long before delivery are kept in snapshots.
MAX_HORIZON_HOURS = 72

ELEXON_BASE = "https://data.elexon.co.uk/bmrs/api/v1"
