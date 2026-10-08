"""
Deterministic finance core.

This module is the single source of every financial figure in Keystone. It
contains NO calls to any language model. Variance, reconciliation, solvency
and budget state are computed here, in plain Python that can be read, tested
and audited. The LLM is only ever allowed to narrate the numbers this module
produces, never to originate them.

Tolerances and thresholds are explicit constants so the rules are inspectable.
"""
from __future__ import annotations

# A contractor may invoice slightly above its purchase order for legitimate
# reasons (rounding, small scope changes). Anything beyond this fraction is
# flagged as an overbill for human review.
PO_TOLERANCE = 0.02          # 2%
# When a transfer would leave the source with less than this fraction of its
# budget as headroom, we warn even if the amount technically fits.
SOLVENCY_FLOOR = 0.0         # must stay >= 0 remaining


def money(x) -> float:
    return round(float(x or 0), 2)


def pct(part, whole) -> float:
    whole = float(whole or 0)
    if whole == 0:
        return 0.0
    return round(part / whole * 100, 1)


# ------------------------------------------------------------------
# Budget state (derived from budget_lines + ledger, never from a field)
# ------------------------------------------------------------------

def project_budget(conn, project_id: str) -> dict:
    """Authoritative budget state for a project, computed from the ledger.

    budget_total = sum(budgeted)  + transfers_in  - transfers_out
    spent        = sum(actual)    + posted invoices
    remaining    = budget_total - spent
    """
    row = conn.execute(
        "SELECT COALESCE(SUM(budgeted),0) b, COALESCE(SUM(actual),0) a "
        "FROM budget_lines WHERE project_id=?", (project_id,)
    ).fetchone()
    budgeted, actual = money(row["b"]), money(row["a"])

    led = conn.execute(
        "SELECT entry_type, COALESCE(SUM(amount),0) s FROM ledger_entries "
        "WHERE project_id=? GROUP BY entry_type", (project_id,)
    ).fetchall()
    tin = tout = posted = 0.0
    for r in led:
        if r["entry_type"] == "transfer_in":
            tin += r["s"]
        elif r["entry_type"] == "transfer_out":
            tout += r["s"]
        elif r["entry_type"] == "invoice_post":
            posted += r["s"]

    budget_total = money(budgeted + tin - tout)
    spent = money(actual + posted)
    remaining = money(budget_total - spent)
    return {
        "project_id": project_id,
        "budget_total": budget_total,
        "spent": spent,
        "remaining": remaining,
        "over_budget": remaining < 0,
        "over_budget_pct": pct(spent - budget_total, budget_total) if spent > budget_total else 0.0,
        "transfers_in": money(tin),
        "transfers_out": money(tout),
        "invoices_posted": money(posted),
    }


def category_variances(conn, project_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT category, budgeted, actual, note FROM budget_lines WHERE project_id=?",
        (project_id,)
    ).fetchall()
    out = []
    for r in rows:
        variance = money(r["actual"] - r["budgeted"])
        out.append({
            "category": r["category"],
            "budgeted": money(r["budgeted"]),
            "actual": money(r["actual"]),
            "variance": variance,
            "variance_pct": pct(variance, r["budgeted"]),
            "status": "Over Budget" if variance > 0 else "Under Budget" if variance < 0 else "On Budget",
            "note": r["note"],
        })
    return out


# ------------------------------------------------------------------
# Invoice reconciliation (invoice vs purchase order vs budget room)
# ------------------------------------------------------------------

def reconcile_invoice(conn, invoice_id: str) -> dict:
    """Match an invoice to its purchase order and the budget line, and flag
    anything that does not reconcile. Deterministic; no model involved."""
    inv = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    if not inv:
        return {"invoice_id": invoice_id, "error": "Invoice not found"}

    flags: list[str] = []
    inv_amount = money(inv["amount"])

    # Find the matching PO: explicit po_id, else same project + contractor.
    po = None
    if inv["po_id"]:
        po = conn.execute("SELECT * FROM purchase_orders WHERE id=?", (inv["po_id"],)).fetchone()
    if po is None:
        po = conn.execute(
            "SELECT * FROM purchase_orders WHERE project_id=? AND contractor=? "
            "ORDER BY amount DESC LIMIT 1",
            (inv["project_id"], inv["contractor"]),
        ).fetchone()

    po_amount = money(po["amount"]) if po else None
    variance = money(inv_amount - po_amount) if po else None
    variance_pct = pct(variance, po_amount) if po else None
    within_tolerance = None
    if po:
        within_tolerance = inv_amount <= po_amount * (1 + PO_TOLERANCE)
        if not within_tolerance:
            flags.append(
                f"Invoice ${inv_amount:,.0f} exceeds PO ${po_amount:,.0f} "
                f"by ${variance:,.0f} ({variance_pct}%), above the {PO_TOLERANCE*100:.0f}% tolerance"
            )
    else:
        flags.append("No matching purchase order found for this invoice")

    # Budget room on the project after this invoice.
    budget = project_budget(conn, inv["project_id"])
    room_after = money(budget["remaining"] - inv_amount)
    if room_after < 0:
        flags.append(
            f"Posting this invoice pushes {inv['project_id']} to "
            f"${room_after:,.0f} remaining (over budget)"
        )

    reconciled = len(flags) == 0
    return {
        "invoice_id": invoice_id,
        "project_id": inv["project_id"],
        "contractor": inv["contractor"],
        "invoice_amount": inv_amount,
        "po_id": po["id"] if po else None,
        "po_amount": po_amount,
        "variance": variance,
        "variance_pct": variance_pct,
        "within_tolerance": within_tolerance,
        "remaining_before": budget["remaining"],
        "remaining_after": room_after,
        "reconciled": reconciled,
        "flags": flags,
        "recommendation": "Post" if reconciled else "Hold for review",
    }


# ------------------------------------------------------------------
# Transfer safety check
# ------------------------------------------------------------------

def check_transfer(conn, from_id: str, to_id: str, amount: float) -> dict:
    """Validate a proposed transfer against the live ledger. Deterministic."""
    amount = money(amount)
    result = {
        "from_project_id": from_id,
        "to_project_id": to_id,
        "amount": amount,
        "ok": False,
        "reason": "",
    }
    if from_id == to_id:
        result["reason"] = "Source and destination are the same project"
        return result
    if amount <= 0:
        result["reason"] = f"Transfer amount must be positive (got ${amount:,.0f})"
        return result

    src = project_budget(conn, from_id)
    dst = project_budget(conn, to_id)
    if not conn.execute("SELECT 1 FROM projects WHERE id=?", (from_id,)).fetchone():
        result["reason"] = f"Unknown source project {from_id}"
        return result
    if not conn.execute("SELECT 1 FROM projects WHERE id=?", (to_id,)).fetchone():
        result["reason"] = f"Unknown destination project {to_id}"
        return result

    from_after = money(src["remaining"] - amount)
    to_after = money(dst["remaining"] + amount)
    result.update({
        "from_remaining_before": src["remaining"],
        "from_remaining_after": from_after,
        "to_remaining_before": dst["remaining"],
        "to_remaining_after": to_after,
    })
    if from_after < SOLVENCY_FLOOR:
        result["reason"] = (
            f"Transfer would leave {from_id} at ${from_after:,.0f} remaining, "
            f"below zero. Available headroom is ${src['remaining']:,.0f}."
        )
        return result

    result["ok"] = True
    result["reason"] = "Transfer keeps the source solvent"
    return result
