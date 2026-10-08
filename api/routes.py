"""
REST layer.

Budget numbers now come from the live system of record (SQLite via
finance_core), so an approved transfer or invoice visibly changes the
dashboard. Schedule and contractor data still come from the seed JSON.

HITL stays delegated to LangGraph (interrupt/resume + SqliteSaver). The actual
side effects of an approval (moving budget, posting an invoice) run through the
deterministic services and write to the ledger with an audit trail.
"""
import uuid
import time
from contextlib import closing

from flask import Blueprint, request, jsonify
from langgraph.types import Command

from workflows.main_graph import graph
from tools import db, finance_core as fc, roi
from services import ledger
from evaluators import grounding
from tools.data_loader import (
    get_schedule_by_project, get_delayed_phases, get_contractors_by_project,
)

api_blueprint = Blueprint("api", __name__)

_KNOWN_THREADS: dict[str, dict] = {}


# ------------------------------------------------------------
# HITL snapshot helpers (unchanged)
# ------------------------------------------------------------
def _snapshot(thread_id: str) -> dict:
    cfg = {"configurable": {"thread_id": thread_id}}
    state = graph.get_state(cfg)
    interrupts = []
    for task in state.tasks:
        for it in task.interrupts:
            interrupts.append(it.value)
    return {"thread_id": thread_id, "next": list(state.next),
            "interrupts": interrupts, "values": state.values}


def _serialize_result(thread_id: str) -> dict:
    snap = _snapshot(thread_id)
    values = snap["values"] or {}
    if snap["interrupts"]:
        return {"thread_id": thread_id, "status": "awaiting_approval",
                "interrupt": snap["interrupts"][0],
                "partial": {"task_type": values.get("task_type"),
                            "project": values.get("project_name")}}
    return {
        "thread_id": thread_id, "status": "complete",
        "task_type": values.get("task_type"), "project": values.get("project_name"),
        "response": values.get("final_response", ""),
        "scores": {"budget": values.get("budget_eval_score", 0),
                   "schedule": values.get("schedule_eval_score", 0),
                   "risk": values.get("risk_eval_score", 0),
                   "report": values.get("report_eval_score", 0),
                   "email": values.get("email_eval_score", 0)},
        "attempts": {"budget": values.get("budget_attempt", 0),
                     "schedule": values.get("schedule_attempt", 0),
                     "risk": values.get("risk_attempt", 0),
                     "report": values.get("report_attempt", 0),
                     "email": values.get("email_attempt", 0)},
        "confirmation": values.get("sent_confirmation", ""),
    }


# ------------------------------------------------------------
# Chat + approvals (unchanged control flow)
# ------------------------------------------------------------
@api_blueprint.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    msg = data.get("message", "").strip()
    if not msg:
        return jsonify({"error": "No message provided"}), 400
    thread_id = data.get("thread_id") or str(uuid.uuid4())
    cfg = {"configurable": {"thread_id": thread_id}}
    initial_state = {"user_request": msg, "project_id": data.get("project_id", ""),
                     "project_name": data.get("project_name", "")}
    _KNOWN_THREADS[thread_id] = {"created_at": time.time(), "request": msg}
    try:
        graph.invoke(initial_state, config=cfg)
    except Exception as e:
        return jsonify({"error": str(e), "thread_id": thread_id}), 500
    return jsonify(_serialize_result(thread_id))


@api_blueprint.route("/approvals", methods=["GET"])
def list_approvals():
    pending = []
    for tid in list(_KNOWN_THREADS.keys()):
        try:
            snap = _snapshot(tid)
        except Exception:
            continue
        if snap["interrupts"]:
            pending.append({"thread_id": tid,
                            "created_at": _KNOWN_THREADS[tid]["created_at"],
                            "request": _KNOWN_THREADS[tid]["request"],
                            "interrupt": snap["interrupts"][0]})
    pending.sort(key=lambda p: p["created_at"], reverse=True)
    return jsonify({"approvals": pending, "total": len(pending)})


@api_blueprint.route("/approvals/<thread_id>", methods=["POST"])
def resolve_approval(thread_id):
    data = request.get_json() or {}
    action = data.get("action", "")
    reason = data.get("reason", "")
    if action not in ("approve", "reject"):
        return jsonify({"error": "action must be 'approve' or 'reject'"}), 400
    cfg = {"configurable": {"thread_id": thread_id}}
    try:
        graph.invoke(Command(resume={"action": "approved" if action == "approve" else "rejected",
                                     "reason": reason}), config=cfg)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify(_serialize_result(thread_id))


# ------------------------------------------------------------
# Dashboard + project detail (now DB-backed for budget)
# ------------------------------------------------------------
def _overview():
    out = []
    with closing(db.get_conn()) as conn:
        for p in conn.execute("SELECT id,name,status FROM projects ORDER BY id").fetchall():
            b = fc.project_budget(conn, p["id"])
            sched = get_schedule_by_project(p["id"])
            delay = sched["overall_delay_days"] if sched else 0
            flag = "RED" if b["over_budget"] else "YELLOW" if delay > 14 else "GREEN"
            out.append({"id": p["id"], "name": p["name"], "status": p["status"],
                        "flag": flag, "budget_total": b["budget_total"],
                        "budget_spent": b["spent"], "delay_days": delay})
    return out


@api_blueprint.route("/dashboard", methods=["GET"])
def dashboard():
    return jsonify({"projects": _overview()})


@api_blueprint.route("/project/<project_id>", methods=["GET"])
def project_detail(project_id):
    with closing(db.get_conn()) as conn:
        p = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        if not p:
            return jsonify({"error": "Project not found"}), 404
        b = fc.project_budget(conn, project_id)
        pend = conn.execute(
            "SELECT id,contractor,amount FROM invoices "
            "WHERE project_id=? AND status='Pending Approval'", (project_id,)).fetchall()
        pending = [{"id": r["id"], "contractor": r["contractor"], "amount": r["amount"]} for r in pend]
        project = {k: p[k] for k in p.keys()}
    sched = get_schedule_by_project(project_id)
    summary = {
        "project": project,
        "budget": {"total": b["budget_total"], "spent": b["spent"],
                   "remaining": b["remaining"], "over_budget": b["over_budget"],
                   "over_budget_pct": b["over_budget_pct"], "pending_invoices": pending},
        "schedule": {"overall_delay_days": sched["overall_delay_days"] if sched else 0,
                     "projected_end_date": sched["projected_end_date"] if sched else None,
                     "delayed_phases": get_delayed_phases(project_id),
                     "critical_path": sched["critical_path_items"] if sched else []},
        "contractors": get_contractors_by_project(project_id),
    }
    return jsonify(summary)


# ------------------------------------------------------------
# Invoice automation (reconcile + resolve, DB-backed)
# ------------------------------------------------------------
@api_blueprint.route("/invoices", methods=["GET"])
def all_invoices():
    status = request.args.get("status")
    q = "SELECT id,project_id,contractor,amount,due_date,status FROM invoices"
    args = ()
    if status:
        q += " WHERE status=?"
        args = (status,)
    with closing(db.get_conn()) as conn:
        rows = conn.execute(q, args).fetchall()
        inv = [dict(r) for r in rows]
    return jsonify({"invoices": inv, "total": len(inv)})


@api_blueprint.route("/invoices/<invoice_id>/reconcile", methods=["GET"])
def reconcile(invoice_id):
    with closing(db.get_conn()) as conn:
        return jsonify(fc.reconcile_invoice(conn, invoice_id))


@api_blueprint.route("/invoices/<invoice_id>/resolve", methods=["POST"])
def resolve_invoice(invoice_id):
    data = request.get_json() or {}
    decision = data.get("decision", "")
    if decision not in ("approved", "rejected"):
        return jsonify({"error": "decision must be 'approved' or 'rejected'"}), 400
    with closing(db.get_conn()) as conn:
        res = ledger.resolve_invoice(conn, invoice_id, decision,
                                     actor=data.get("actor", "human"),
                                     thread_id=data.get("thread_id", ""),
                                     reason=data.get("reason", ""))
    code = 200 if res.get("status") in ("approved", "rejected") else 409
    return jsonify(res), code


# ------------------------------------------------------------
# Ledger, audit, ROI
# ------------------------------------------------------------
@api_blueprint.route("/ledger/<project_id>", methods=["GET"])
def ledger_for(project_id):
    with closing(db.get_conn()) as conn:
        rows = conn.execute(
            "SELECT ts,entry_type,amount,memo,ref FROM ledger_entries "
            "WHERE project_id=? ORDER BY id DESC", (project_id,)).fetchall()
        return jsonify({"project_id": project_id, "entries": [dict(r) for r in rows]})


@api_blueprint.route("/audit", methods=["GET"])
def audit():
    with closing(db.get_conn()) as conn:
        rows = conn.execute(
            "SELECT ts,actor,action,thread_id,detail FROM audit_log "
            "ORDER BY id DESC LIMIT 200").fetchall()
        return jsonify({"audit": [dict(r) for r in rows]})


@api_blueprint.route("/roi", methods=["GET"])
def roi_summary():
    with closing(db.get_conn()) as conn:
        return jsonify(roi.summary(conn))


# ------------------------------------------------------------
# Activity (from checkpointer-known threads, unchanged)
# ------------------------------------------------------------
@api_blueprint.route("/activity", methods=["GET"])
def activity():
    log = []
    for tid, meta in _KNOWN_THREADS.items():
        try:
            snap = _snapshot(tid)
        except Exception:
            continue
        values = snap["values"] or {}
        log.append({"thread_id": tid, "created_at": meta["created_at"],
                    "request": meta["request"], "task_type": values.get("task_type"),
                    "project": values.get("project_name"),
                    "status": "awaiting_approval" if snap["interrupts"] else "complete",
                    "scores": {"budget": values.get("budget_eval_score", 0),
                               "schedule": values.get("schedule_eval_score", 0),
                               "risk": values.get("risk_eval_score", 0),
                               "report": values.get("report_eval_score", 0),
                               "email": values.get("email_eval_score", 0)}})
    log.sort(key=lambda e: e["created_at"], reverse=True)
    return jsonify({"log": log, "total": len(log)})
