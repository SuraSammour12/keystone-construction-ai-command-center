"""
Tests for the deterministic core. These run with no API key and no model:
they prove the arithmetic, reconciliation, solvency and writeback are correct.
Run:  python -m pytest -q   (or: python tests/test_finance.py)
"""
import os
import sys
from contextlib import closing

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import init_db
from tools import db, finance_core as fc, roi
from services import ledger
from evaluators import grounding


def fresh():
    init_db.main()
    return db.get_conn()


def test_initial_budget_matches_seed():
    with closing(fresh()) as conn:
        b = fc.project_budget(conn, "PRJ-001")
        assert b["budget_total"] == 2000000
        assert b["spent"] == 2300000
        assert b["remaining"] == -300000
        assert b["over_budget"] is True


def test_reconcile_catches_overbill():
    with closing(fresh()) as conn:
        r = fc.reconcile_invoice(conn, "INV-1001")   # 120k billed vs 100k PO
        assert r["po_amount"] == 100000
        assert r["variance"] == 20000
        assert r["within_tolerance"] is False
        assert r["reconciled"] is False
        assert any("exceeds PO" in f for f in r["flags"])


def test_clean_invoice_reconciles():
    with closing(fresh()) as conn:
        # INV-3002: 32k vs 32k PO on PRJ-003, which has ample budget room.
        r = fc.reconcile_invoice(conn, "INV-3002")
        assert r["variance"] == 0
        assert r["within_tolerance"] is True
        assert r["reconciled"] is True


def test_overbudget_project_holds_clean_invoice():
    with closing(fresh()) as conn:
        # Matches its PO, but the project is already over budget -> held.
        r = fc.reconcile_invoice(conn, "INV-1002")   # 45k vs 45k PO on PRJ-001
        assert r["variance"] == 0
        assert r["reconciled"] is False
        assert any("over budget" in f for f in r["flags"])


def test_transfer_writeback_moves_money():
    with closing(fresh()) as conn:
        before_src = fc.project_budget(conn, "PRJ-002")["remaining"]
        res = ledger.execute_transfer(conn, "PRJ-002", "PRJ-001", 950000,
                                      thread_id="t-1", reason="cover deficit")
        assert res["status"] == "executed"
        assert fc.project_budget(conn, "PRJ-001")["remaining"] == -300000 + 950000  # 650k
        assert fc.project_budget(conn, "PRJ-002")["remaining"] == before_src - 950000


def test_transfer_idempotent():
    with closing(fresh()) as conn:
        ledger.execute_transfer(conn, "PRJ-002", "PRJ-001", 100000, thread_id="t-2")
        again = ledger.execute_transfer(conn, "PRJ-002", "PRJ-001", 100000, thread_id="t-2")
        assert again["status"] == "already_executed"
        # Only one pair of ledger rows for this thread.
        n = conn.execute("SELECT COUNT(*) c FROM ledger_entries WHERE ref='t-2'").fetchone()["c"]
        assert n == 2


def test_transfer_blocks_insolvent_source():
    with closing(fresh()) as conn:
        # PRJ-001 is already negative; it cannot be a source.
        res = ledger.execute_transfer(conn, "PRJ-001", "PRJ-002", 50000, thread_id="t-3")
        assert res["status"] == "rejected"
        assert "below zero" in res["reason"]


def test_invoice_approval_increases_spend():
    with closing(fresh()) as conn:
        before = fc.project_budget(conn, "PRJ-003")["spent"]
        res = ledger.resolve_invoice(conn, "INV-3002", "approved", thread_id="t-4")
        assert res["status"] == "approved"
        after = fc.project_budget(conn, "PRJ-003")["spent"]
        assert round(after - before, 2) == 32000


def test_grounding_rejects_invented_figure():
    with closing(fresh()) as conn:
        good = "Alpha Tower spent $2,300,000 of its $2,000,000 budget."
        bad = "Alpha Tower spent $9,999,999 this quarter."
        assert grounding.verify_report(conn, "PRJ-001", good)["grounded"] is True
        v = grounding.verify_report(conn, "PRJ-001", bad)
        assert v["grounded"] is False
        assert 9999999 in v["ungrounded_figures"]


def test_grounding_understands_scaled_shorthand():
    with closing(fresh()) as conn:
        # Real figures written in M/k shorthand must be recognised as grounded.
        txt = "Alpha spent $2.30 M against a $2.00 M budget; materials ran +$180 k."
        v = grounding.verify_report(conn, "PRJ-001", txt)
        assert v["grounded"] is True
        # A projected total the model invents is still flagged.
        v2 = grounding.verify_report(conn, "PRJ-001", "Projected total spend is $2.465 M.")
        assert v2["grounded"] is False
        assert 2465000 in v2["ungrounded_figures"]


def test_roi_accumulates():
    with closing(fresh()) as conn:
        ledger.execute_transfer(conn, "PRJ-002", "PRJ-001", 100000, thread_id="t-5")
        ledger.resolve_invoice(conn, "INV-1001", "rejected", thread_id="t-6", reason="overbill")
        s = roi.summary(conn)
        assert s["actions"] >= 2
        assert s["minutes_saved"] > 0
        assert s["dollars_flagged"] >= 20000   # the caught overbill


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        try:
            fn(); print(f"PASS {fn.__name__}"); passed += 1
        except Exception:
            print(f"FAIL {fn.__name__}"); traceback.print_exc()
    print(f"\n{passed}/{len(fns)} passed")
