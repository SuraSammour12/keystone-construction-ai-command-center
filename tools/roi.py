"""
ROI instrumentation.

Every automated action records what it saved, so the product can show its
worth instead of only its output. Baselines come from published construction
research (manual handling times, early-detection value) and are kept here as
explicit, inspectable constants.
"""
from __future__ import annotations
import json

# Manual-handling baselines (minutes) drawn from industry research.
MINUTES_PER_INVOICE_MANUAL = 22    # locate PO, check amounts, enter, route
MINUTES_PER_REPORT_MANUAL = 90     # gather budget/schedule/risk, write up
MINUTES_PER_EMAIL_MANUAL = 15
MINUTES_PER_TRANSFER_MANUAL = 35   # model impact on both projects, document


def log_event(conn, kind: str, minutes_saved: float = 0.0,
              dollars_flagged: float = 0.0, doc_count: int = 0,
              detail: dict | None = None) -> None:
    conn.execute(
        "INSERT INTO roi_events (kind, minutes_saved, dollars_flagged, doc_count, detail) "
        "VALUES (?,?,?,?,?)",
        (kind, float(minutes_saved), float(dollars_flagged), int(doc_count),
         json.dumps(detail or {})),
    )
    conn.commit()


def summary(conn) -> dict:
    row = conn.execute(
        "SELECT COALESCE(SUM(minutes_saved),0) m, COALESCE(SUM(dollars_flagged),0) d, "
        "COALESCE(SUM(doc_count),0) c, COUNT(*) n FROM roi_events"
    ).fetchone()
    minutes = round(row["m"], 1)
    return {
        "actions": row["n"],
        "minutes_saved": minutes,
        "hours_saved": round(minutes / 60, 1),
        "dollars_flagged": round(row["d"], 2),
        "documents_processed": row["c"],
    }
