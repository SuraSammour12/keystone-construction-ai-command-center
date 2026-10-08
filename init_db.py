"""
Build (or rebuild) the Keystone system of record from the seed JSON.

Run once before starting the API:  python init_db.py

It reads data/projects.json, budgets.json and contractors.json, then populates
keystone.db. Purchase orders are synthesized from the pending invoices; a few
are deliberately set below the invoice amount so the reconciliation logic has a
real overbill to catch in the demo.
"""
import json
import os
from contextlib import closing

from tools import db

DATA = os.path.join(os.path.dirname(__file__), "data")

# Purchase-order amount overrides to create realistic reconciliation cases.
# Any invoice not listed gets a PO equal to its own amount (clean match).
PO_OVERRIDES = {
    "INV-1001": 100000,   # SteelWorks billed 120k against a 100k PO -> overbill
    "INV-2001": 180000,   # BuildRight billed 200k against a 180k PO -> overbill
}


def _load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def main():
    os.makedirs(DATA, exist_ok=True)
    projects = _load("projects.json")["projects"]
    budgets = _load("budgets.json")["budgets"]

    with closing(db.get_conn()) as conn:
        db.init_schema(conn)
        for t in ("roi_events", "audit_log", "ledger_entries", "invoices",
                  "purchase_orders", "budget_lines", "projects"):
            conn.execute(f"DELETE FROM {t}")

        for p in projects:
            conn.execute(
                "INSERT INTO projects (id,name,type,location,status,project_manager,client) "
                "VALUES (?,?,?,?,?,?,?)",
                (p["id"], p["name"], p.get("type"), p.get("location"), p.get("status"),
                 p.get("project_manager"), p.get("client")),
            )

        for b in budgets:
            pid = b["project_id"]
            for line in b["breakdown"]:
                conn.execute(
                    "INSERT INTO budget_lines (project_id,category,budgeted,actual,note) "
                    "VALUES (?,?,?,?,?)",
                    (pid, line["category"], line["budgeted"], line["actual"], line.get("note")),
                )
            for inv in b["invoices_pending"]:
                po_id = "PO-" + inv["id"].split("-")[1]
                po_amount = PO_OVERRIDES.get(inv["id"], inv["amount"])
                conn.execute(
                    "INSERT INTO purchase_orders (id,project_id,contractor,category,amount) "
                    "VALUES (?,?,?,?,?)",
                    (po_id, pid, inv["contractor"], None, po_amount),
                )
                conn.execute(
                    "INSERT INTO invoices (id,project_id,po_id,contractor,category,amount,due_date,status) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (inv["id"], pid, po_id, inv["contractor"], None, inv["amount"],
                     inv.get("due_date"), inv.get("status", "Pending Approval")),
                )
        conn.commit()

        n = conn.execute("SELECT COUNT(*) c FROM projects").fetchone()["c"]
        ni = conn.execute("SELECT COUNT(*) c FROM invoices").fetchone()["c"]
        print(f"Keystone DB built at {db.DB_PATH}: {n} projects, {ni} invoices.")


if __name__ == "__main__":
    main()
