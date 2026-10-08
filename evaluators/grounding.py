"""
Grounding verifier.

The old evaluator scored analyses on a 0 to 10 "quality" rubric judged by
another language model. That measures style, not truth. This verifier is
deterministic: it extracts every dollar figure a generated report states and
checks each one against the set of figures that actually exist in the system
of record for that project. A number the model invented, that does not trace
back to the data, fails the check.

This does not grade prose. It answers one question with no model in the loop:
is every figure real?
"""
from __future__ import annotations
import re

from tools import finance_core as fc

# Treat two dollar figures as the same if within this absolute amount, to allow
# for rounding in the narration.
MATCH_TOLERANCE = 1.0

# Matches $2,300,000 as well as scaled shorthand like $2.30 M, $180 k, $1.2 B.
# The unit letter only counts when it is not part of a following word (so the
# "b" in "budget" after "$2,000,000" is not read as "billion").
_MONEY_RE = re.compile(r"\$\s?([0-9][0-9,]*(?:\.[0-9]+)?)\s?([MmKkBb])?(?![A-Za-z])")

_SCALE = {"k": 1e3, "m": 1e6, "b": 1e9}


def _parse_money(num: str, suffix: str) -> float:
    v = float(num.replace(",", ""))
    return v * _SCALE.get((suffix or "").lower(), 1)


def known_figures(conn, project_id: str) -> set[float]:
    """Every dollar figure that legitimately describes this project."""
    figs: set[float] = set()
    b = fc.project_budget(conn, project_id)
    for k in ("budget_total", "spent", "remaining", "transfers_in",
              "transfers_out", "invoices_posted"):
        figs.add(abs(round(b[k], 0)))
    for line in fc.category_variances(conn, project_id):
        figs.add(abs(round(line["budgeted"], 0)))
        figs.add(abs(round(line["actual"], 0)))
        figs.add(abs(round(line["variance"], 0)))
    for r in conn.execute(
            "SELECT amount FROM invoices WHERE project_id=?", (project_id,)).fetchall():
        figs.add(abs(round(r["amount"], 0)))
    for r in conn.execute(
            "SELECT amount FROM purchase_orders WHERE project_id=?", (project_id,)).fetchall():
        figs.add(abs(round(r["amount"], 0)))
    return figs


def verify_report(conn, project_id: str, text: str) -> dict:
    """Check that every dollar figure in `text` traces back to the record."""
    known = known_figures(conn, project_id)
    stated = [abs(round(_parse_money(num, suf), 0)) for num, suf in _MONEY_RE.findall(text or "")]
    unknown = []
    for v in stated:
        if not any(abs(v - k) <= MATCH_TOLERANCE for k in known):
            unknown.append(v)
    # De-duplicate while preserving order.
    seen, unknown_unique = set(), []
    for v in unknown:
        if v not in seen:
            seen.add(v)
            unknown_unique.append(v)
    return {
        "project_id": project_id,
        "figures_checked": len(stated),
        "ungrounded_figures": unknown_unique,
        "grounded": len(unknown_unique) == 0,
    }
