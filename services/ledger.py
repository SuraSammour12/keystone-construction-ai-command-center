"""
Side-effect services: the part of Keystone that actually DOES the work.

When a human approves an action, these functions mutate the system of record:
a transfer posts two ledger entries and shifts both projects' budgets; an
approved invoice is posted and increases spend. Every mutation writes an audit
row and an ROI event. Each action is idempotent per thread_id, so a repeated
approval cannot double-post.

Numbers are never originated here either: amounts and safety are validated by
finance_core before anything is written.
"""
from __future__ import annotations
import json

from tools import finance_core as fc
from tools import roi


def _already_done(conn, thread_id: str, action: str) -> bool:
    if not thread_id:
        return False
    row = conn.execute(
        "SELECT 1 FROM audit_log WHERE thread_id=? AND action=? LIMIT 1",
        (thread_id, action),
    ).fetchone()
    return row is not None


def _audit(conn, actor: str, action: str, thread_id: str, detail: dict) -> None:
    conn.execute(
        "INSERT INTO audit_log (actor, action, thread_id, detail) VALUES (?,?,?,?)",
        (actor, action, thread_id, json.dumps(detail)),
    )


def execute_transfer(conn, from_id: str, to_id: str, amount: float,
                     actor: str = "human", thread_id: str = "",
                     reason: str = "") -> dict:
    """Post an approved budget transfer to the ledger. Returns the new state."""
    if _already_done(conn, thread_id, "transfer_executed"):
        return {"status": "already_executed", "thread_id": thread_id}

    check = fc.check_transfer(conn, from_id, to_id, amount)
    if not check["ok"]:
        _audit(conn, actor, "transfer_rejected_by_rule", thread_id,
               {"check": check, "reason": reason})
        conn.commit()
        return {"status": "rejected", "reason": check["reason"], "check": check}

    amount = check["amount"]
    memo = reason or f"Approved transfer {from_id} -> {to_id}"
    conn.execute(
        "INSERT INTO ledger_entries (project_id, entry_type, amount, memo, ref) "
        "VALUES (?,?,?,?,?)", (from_id, "transfer_out", amount, memo, thread_id))
    conn.execute(
        "INSERT INTO ledger_entries (project_id, entry_type, amount, memo, ref) "
        "VALUES (?,?,?,?,?)", (to_id, "transfer_in", amount, memo, thread_id))

    src_after = fc.project_budget(conn, from_id)
    dst_after = fc.project_budget(conn, to_id)
    _audit(conn, actor, "transfer_executed", thread_id, {
        "from": from_id, "to": to_id, "amount": amount, "reason": reason,
        "from_remaining_after": src_after["remaining"],
        "to_remaining_after": dst_after["remaining"],
    })
    roi.log_event(conn, "transfer", minutes_saved=roi.MINUTES_PER_TRANSFER_MANUAL,
                  detail={"from": from_id, "to": to_id, "amount": amount})
    conn.commit()
    return {
        "status": "executed",
        "amount": amount,
        "from_remaining_after": src_after["remaining"],
        "to_remaining_after": dst_after["remaining"],
    }


def resolve_invoice(conn, invoice_id: str, decision: str,
                    actor: str = "human", thread_id: str = "",
                    reason: str = "") -> dict:
    """Approve or reject an invoice. Approval posts it to the ledger."""
    inv = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    if not inv:
        return {"status": "error", "reason": "Invoice not found"}
    if inv["status"] != "Pending Approval":
        return {"status": "already_resolved", "invoice_status": inv["status"]}

    recon = fc.reconcile_invoice(conn, invoice_id)

    if decision != "approved":
        conn.execute("UPDATE invoices SET status='Rejected' WHERE id=?", (invoice_id,))
        _audit(conn, actor, "invoice_rejected", thread_id,
               {"invoice": invoice_id, "reason": reason, "reconciliation": recon})
        # Catching an overbill before it is paid is value flagged.
        flagged = recon["variance"] if (recon.get("variance") or 0) > 0 else 0
        roi.log_event(conn, "invoice_rejected", minutes_saved=roi.MINUTES_PER_INVOICE_MANUAL,
                      dollars_flagged=flagged, doc_count=1,
                      detail={"invoice": invoice_id})
        conn.commit()
        return {"status": "rejected", "invoice_id": invoice_id, "reconciliation": recon}

    conn.execute("UPDATE invoices SET status='Approved' WHERE id=?", (invoice_id,))
    conn.execute(
        "INSERT INTO ledger_entries (project_id, entry_type, amount, memo, ref) "
        "VALUES (?,?,?,?,?)",
        (inv["project_id"], "invoice_post", fc.money(inv["amount"]),
         f"Posted invoice {invoice_id} ({inv['contractor']})", thread_id or invoice_id))
    _audit(conn, actor, "invoice_approved", thread_id,
           {"invoice": invoice_id, "amount": fc.money(inv["amount"]),
            "reason": reason, "reconciliation": recon})
    roi.log_event(conn, "invoice_approved", minutes_saved=roi.MINUTES_PER_INVOICE_MANUAL,
                  doc_count=1, detail={"invoice": invoice_id})
    conn.commit()
    budget = fc.project_budget(conn, inv["project_id"])
    return {"status": "approved", "invoice_id": invoice_id,
            "remaining_after": budget["remaining"], "reconciliation": recon}
