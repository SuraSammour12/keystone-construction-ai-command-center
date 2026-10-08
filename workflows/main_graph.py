"""
Construction AI Command Center - LangGraph workflow (v3).

Changes from v2:
- transfer_execute_node performs a REAL side effect: on approval it calls the
  deterministic ledger service, which posts to the system of record and audits
  the change. It no longer returns a sentence and changes nothing.
- report_generation_node attaches a deterministic grounding check: every dollar
  figure in the report is verified against the database, and ungrounded figures
  are surfaced in the final response.
"""
import os
import sqlite3
from contextlib import closing
from typing import TypedDict, Literal, Optional

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import interrupt
from langchain_groq import ChatGroq

from workflows.schemas import OrchestratorDecision
from agents.budget_agent import run_budget_analysis
from agents.schedule_agent import run_schedule_analysis
from agents.risk_agent import run_risk_analysis
from agents.report_agent import generate_report
from agents.email_agent import draft_email
from agents.budget_transfer_agent import propose_budget_transfer
from evaluators.analysis_evaluator import evaluate_analysis
from evaluators.report_evaluator import evaluate_report
from evaluators.email_evaluator import evaluate_email
from evaluators import grounding
from tools.data_loader import get_project_by_name, get_all_projects_overview
from tools import db, finance_core as fc
from services import ledger

_router_llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)
_router_structured = _router_llm.with_structured_output(OrchestratorDecision)


# ============================================================
# STATE
# ============================================================

class CommandCenterState(TypedDict, total=False):
    user_request: str
    project_id: str
    project_name: str

    task_type: str
    email_recipient: str
    transfer_from_project_id: str
    transfer_to_project_id: str
    transfer_amount: float

    budget_analysis: str
    schedule_analysis: str
    risk_analysis: str
    report: str
    email_draft: dict
    transfer_proposal: dict
    report_grounding: dict

    budget_eval_score: int
    schedule_eval_score: int
    risk_eval_score: int
    report_eval_score: int
    email_eval_score: int
    budget_eval_feedback: str
    schedule_eval_feedback: str
    risk_eval_feedback: str
    report_eval_feedback: str
    email_eval_feedback: str

    budget_attempt: int
    schedule_attempt: int
    risk_attempt: int
    report_attempt: int
    email_attempt: int
    max_attempts: int

    approval_decision: str
    approval_reason: str
    sent_confirmation: str

    final_response: str


# ============================================================
# NODES
# ============================================================

def orchestrator_node(state: CommandCenterState) -> dict:
    request = state["user_request"]
    prompt = f"""You are a construction project management AI orchestrator.
Classify the user request and extract entities.

USER REQUEST: {request}

task_type rules:
- report: user wants analysis/status/overview for ONE specific project
- email: user wants to draft, write, or send an email or message
- transfer: user wants to move budget between two projects
- status: user wants an overview of ALL projects
- unknown: intent cannot be determined"""

    try:
        decision: OrchestratorDecision = _router_structured.invoke(prompt)
    except Exception:
        decision = OrchestratorDecision(task_type="unknown")

    project_id = state.get("project_id", "")
    project_name = state.get("project_name", "")

    if not project_id and decision.project_name:
        proj = get_project_by_name(decision.project_name)
        if proj:
            project_id = proj["id"]
            project_name = proj["name"]

    # Abstention: never guess a project. If a report is requested for a project we
    # cannot find in the records, say so plainly instead of defaulting to another.
    if not project_id and decision.task_type == "report":
        names = ", ".join(p["name"] for p in get_all_projects_overview())
        return {
            "task_type": "unknown",
            "final_response": f"That project is not in the records. Available projects: {names}.",
            "project_id": "", "project_name": "",
            "budget_attempt": 0, "schedule_attempt": 0, "risk_attempt": 0,
            "report_attempt": 0, "email_attempt": 0, "max_attempts": 3,
            "approval_decision": "", "approval_reason": "", "sent_confirmation": "",
        }

    transfer_from_id = transfer_to_id = ""
    if decision.task_type == "transfer":
        f = get_project_by_name(decision.transfer_from_project)
        t = get_project_by_name(decision.transfer_to_project)
        if f: transfer_from_id = f["id"]
        if t: transfer_to_id = t["id"]

    return {
        "project_id": project_id,
        "project_name": project_name,
        "task_type": decision.task_type,
        "email_recipient": decision.email_recipient or "project stakeholder",
        "transfer_from_project_id": transfer_from_id,
        "transfer_to_project_id": transfer_to_id,
        "transfer_amount": decision.transfer_amount,
        "budget_attempt": 0, "schedule_attempt": 0, "risk_attempt": 0,
        "report_attempt": 0, "email_attempt": 0,
        "max_attempts": 3,
        "approval_decision": "", "approval_reason": "", "sent_confirmation": "",
    }


def budget_analysis_node(state):
    fb = state.get("budget_eval_feedback", "")
    text = run_budget_analysis(state["project_id"], state["project_name"], feedback=fb)
    ev = evaluate_analysis(text, "budget")
    return {"budget_analysis": text, "budget_eval_score": ev["score"],
            "budget_eval_feedback": ev["feedback"],
            "budget_attempt": state.get("budget_attempt", 0) + 1}


def schedule_analysis_node(state):
    fb = state.get("schedule_eval_feedback", "")
    text = run_schedule_analysis(state["project_id"], state["project_name"], feedback=fb)
    ev = evaluate_analysis(text, "schedule")
    return {"schedule_analysis": text, "schedule_eval_score": ev["score"],
            "schedule_eval_feedback": ev["feedback"],
            "schedule_attempt": state.get("schedule_attempt", 0) + 1}


def risk_analysis_node(state):
    fb = state.get("risk_eval_feedback", "")
    text = run_risk_analysis(state["project_id"], state["project_name"], feedback=fb)
    ev = evaluate_analysis(text, "risk")
    return {"risk_analysis": text, "risk_eval_score": ev["score"],
            "risk_eval_feedback": ev["feedback"],
            "risk_attempt": state.get("risk_attempt", 0) + 1}


def report_generation_node(state):
    fb = state.get("report_eval_feedback", "")
    text = generate_report(state["project_name"], state["budget_analysis"],
                           state["schedule_analysis"], state["risk_analysis"], feedback=fb)
    ev = evaluate_report(text)
    grounded = {}
    pid = state.get("project_id", "")
    if pid:
        try:
            with closing(db.get_conn()) as conn:
                grounded = grounding.verify_report(conn, pid, text)
        except Exception:
            grounded = {}
    fb_out = ev["feedback"]
    if grounded and not grounded.get("grounded", True):
        figs = grounded.get("ungrounded_figures", [])
        fb_out += (f"\nGROUNDING FAILURE: these dollar figures are NOT in the records and "
                   f"must be removed or corrected: {figs}. Do not state any dollar figure "
                   f"that is not in the provided analyses.")
    return {"report": text, "report_eval_score": ev["score"],
            "report_eval_feedback": fb_out,
            "report_grounding": grounded,
            "report_attempt": state.get("report_attempt", 0) + 1}


def email_drafting_node(state):
    fb = state.get("email_eval_feedback", "")
    email = draft_email(
        context=f"Project: {state['project_name']}. Request: {state['user_request']}",
        recipient=state.get("email_recipient", "project stakeholder"),
        purpose=state["user_request"], feedback=fb,
    )
    ev = evaluate_email(email["email"], state["user_request"])
    return {"email_draft": email, "email_eval_score": ev["score"],
            "email_eval_feedback": ev["feedback"],
            "email_attempt": state.get("email_attempt", 0) + 1}


def budget_transfer_node(state):
    fid = state.get("transfer_from_project_id", "")
    tid = state.get("transfer_to_project_id", "")
    amount = state.get("transfer_amount", 0.0) or None
    if not fid or not tid:
        return {"transfer_proposal": {"error": "Could not identify both projects."}}
    proposal = propose_budget_transfer(fid, tid, amount if amount and amount > 0 else None)
    return {"transfer_proposal": proposal}


def status_overview_node(state):
    overview = get_all_projects_overview()
    labels = {"GREEN": "[OK]", "YELLOW": "[AT RISK]", "RED": "[CRITICAL]"}
    lines = ["ALL PROJECTS OVERVIEW\n" + "=" * 40]
    for p in overview:
        lines.append(
            f"\n{labels.get(p['flag'], '[--]')} {p['name']} ({p['id']})\n"
            f"   Status: {p['status']}\n"
            f"   Budget: ${p['budget_spent']:,} / ${p['budget_total']:,}\n"
            f"   Delay: {p['delay_days']} days"
        )
    return {"final_response": "\n".join(lines)}


# ---------- HITL nodes ----------

def email_approval_node(state):
    decision = interrupt({
        "kind": "email_approval",
        "project": state["project_name"],
        "sensitivity": state["email_draft"]["sensitivity"],
        "recipient": state["email_draft"]["recipient"],
        "draft": state["email_draft"]["email"],
        "quality_score": state["email_eval_score"],
    })
    return {"approval_decision": decision.get("action", "rejected"),
            "approval_reason": decision.get("reason", "")}


def email_send_node(state):
    if state["approval_decision"] == "approved":
        # In production: SMTP / SendGrid / Gmail API call.
        return {"sent_confirmation":
                f"Email dispatched to {state['email_draft']['recipient']}."}
    return {"sent_confirmation":
            f"Email rejected. Reason: {state.get('approval_reason') or 'no reason given'}."}


def transfer_approval_node(state):
    proposal = state.get("transfer_proposal", {})
    if "error" in proposal:
        return {"approval_decision": "rejected", "approval_reason": proposal["error"]}
    decision = interrupt({"kind": "transfer_approval",
                          "project": state["project_name"], "proposal": proposal})
    return {"approval_decision": decision.get("action", "rejected"),
            "approval_reason": decision.get("reason", "")}


def transfer_execute_node(state, config=None):
    """Real side effect: post the approved transfer to the ledger."""
    if state.get("approval_decision") != "approved":
        return {"sent_confirmation":
                f"Transfer rejected. Reason: {state.get('approval_reason') or 'no reason given'}."}

    thread_id = ""
    try:
        thread_id = (config or {}).get("configurable", {}).get("thread_id", "")
    except Exception:
        thread_id = ""

    prop = (state.get("transfer_proposal") or {}).get("transfer", {})
    from_id = state.get("transfer_from_project_id", "")
    to_id = state.get("transfer_to_project_id", "")
    amount = prop.get("amount", 0)

    with closing(db.get_conn()) as conn:
        res = ledger.execute_transfer(conn, from_id, to_id, amount,
                                      actor="human", thread_id=thread_id,
                                      reason=state.get("approval_reason", ""))

    if res.get("status") == "executed":
        return {"sent_confirmation": (
            f"Transfer executed and posted to the ledger. "
            f"{from_id} remaining ${res['from_remaining_after']:,.0f}; "
            f"{to_id} remaining ${res['to_remaining_after']:,.0f}.")}
    if res.get("status") == "already_executed":
        return {"sent_confirmation": "Transfer already executed for this request."}
    return {"sent_confirmation": f"Transfer not executed: {res.get('reason', 'rejected by rule')}."}


# ---------- Compile ----------

def compile_response_node(state):
    task = state["task_type"]

    if task == "report":
        response = (
            f"PROJECT REPORT: {state['project_name']}\n{'=' * 50}\n\n"
            f"{state.get('report', 'No report generated.')}\n\n{'=' * 50}\n"
            f"Quality Scores:\n"
            f"  Budget:   {state.get('budget_eval_score', 'N/A')}/10  (attempts: {state.get('budget_attempt', 1)})\n"
            f"  Schedule: {state.get('schedule_eval_score', 'N/A')}/10  (attempts: {state.get('schedule_attempt', 1)})\n"
            f"  Risk:     {state.get('risk_eval_score', 'N/A')}/10  (attempts: {state.get('risk_attempt', 1)})\n"
            f"  Report:   {state.get('report_eval_score', 'N/A')}/10  (attempts: {state.get('report_attempt', 1)})\n"
        )
        g = state.get("report_grounding") or {}
        if g:
            if g.get("grounded"):
                response += f"  Grounding: all {g.get('figures_checked', 0)} figures trace to the record.\n"
            else:
                response += (f"  Grounding: {len(g.get('ungrounded_figures', []))} figure(s) "
                             f"could not be traced to the record: {g.get('ungrounded_figures')}\n")
    elif task == "email":
        e = state.get("email_draft", {})
        confirmation = state.get("sent_confirmation") or "Draft complete (no send action taken)."
        response = (
            f"EMAIL DRAFT\n{'=' * 50}\n"
            f"Sensitivity: {e.get('sensitivity', 'N/A')} | "
            f"Quality: {state.get('email_eval_score', 'N/A')}/10 "
            f"(attempts: {state.get('email_attempt', 1)})\n"
            f"{'=' * 50}\n\n{e.get('email', '')}\n\n"
            f"--- RESULT ---\n{confirmation}"
        )
    elif task == "transfer":
        p = state.get("transfer_proposal", {})
        if "error" in p:
            response = f"Transfer Error: {p['error']}"
        else:
            t = p.get("transfer", {})
            confirmation = state.get("sent_confirmation") or "Proposal generated."
            response = (
                f"BUDGET TRANSFER PROPOSAL\n{'=' * 50}\n"
                f"From:   {t.get('from_project')}\n"
                f"To:     {t.get('to_project')}\n"
                f"Amount: ${t.get('amount', 0):,.0f}\n\n"
                f"Impact Analysis:\n{p.get('impact_analysis', 'N/A')}\n\n"
                f"--- RESULT ---\n{confirmation}"
            )
    else:
        response = state.get("final_response", "Could not process request. Please rephrase.")

    return {"final_response": response}


# ============================================================
# ROUTING
# ============================================================

def route_by_task(state) -> str:
    return {"report": "analyze", "email": "email",
            "transfer": "transfer", "status": "status"}.get(state["task_type"], "compile")


def should_retry_budget(state):
    if state.get("budget_eval_score", 0) >= 7 or state.get("budget_attempt", 0) >= state.get("max_attempts", 3):
        return "schedule_analysis"
    return "retry_budget"


def should_retry_schedule(state):
    if state.get("schedule_eval_score", 0) >= 7 or state.get("schedule_attempt", 0) >= state.get("max_attempts", 3):
        return "risk_analysis"
    return "retry_schedule"


def should_retry_risk(state):
    if state.get("risk_eval_score", 0) >= 7 or state.get("risk_attempt", 0) >= state.get("max_attempts", 3):
        return "report_generation"
    return "retry_risk"


def should_retry_report(state):
    score = state.get("report_eval_score", 0)
    attempt = state.get("report_attempt", 0)
    max_a = state.get("max_attempts", 3)
    grounded_ok = (state.get("report_grounding") or {}).get("grounded", True)
    # Regenerate if quality is low OR any dollar figure is not grounded in the records.
    if (score >= 8 and grounded_ok) or attempt >= max_a:
        return "compile"
    return "retry_report"


def route_email_after_eval(state):
    score = state.get("email_eval_score", 0)
    attempt = state.get("email_attempt", 0)
    max_a = state.get("max_attempts", 3)
    if score < 8 and attempt < max_a:
        return "retry_email"
    return "needs_approval" if state["email_draft"].get("requires_approval") else "compile"


def route_transfer_after_propose(state):
    return "compile" if "error" in state.get("transfer_proposal", {}) else "needs_approval"


# ============================================================
# BUILD
# ============================================================

def _build_graph():
    wf = StateGraph(CommandCenterState)

    wf.add_node("orchestrator", orchestrator_node)
    wf.add_node("budget_node", budget_analysis_node)
    wf.add_node("schedule_node", schedule_analysis_node)
    wf.add_node("risk_node", risk_analysis_node)
    wf.add_node("report_node", report_generation_node)
    wf.add_node("email_node", email_drafting_node)
    wf.add_node("email_approval", email_approval_node)
    wf.add_node("email_send", email_send_node)
    wf.add_node("transfer_node", budget_transfer_node)
    wf.add_node("transfer_approval", transfer_approval_node)
    wf.add_node("transfer_execute", transfer_execute_node)
    wf.add_node("status_node", status_overview_node)
    wf.add_node("compile_response", compile_response_node)

    wf.set_entry_point("orchestrator")

    wf.add_conditional_edges("orchestrator", route_by_task, {
        "analyze": "budget_node", "email": "email_node",
        "transfer": "transfer_node", "status": "status_node",
        "compile": "compile_response"})

    wf.add_conditional_edges("budget_node", should_retry_budget,
                             {"retry_budget": "budget_node", "schedule_analysis": "schedule_node"})
    wf.add_conditional_edges("schedule_node", should_retry_schedule,
                             {"retry_schedule": "schedule_node", "risk_analysis": "risk_node"})
    wf.add_conditional_edges("risk_node", should_retry_risk,
                             {"retry_risk": "risk_node", "report_generation": "report_node"})
    wf.add_conditional_edges("report_node", should_retry_report,
                             {"retry_report": "report_node", "compile": "compile_response"})

    wf.add_conditional_edges("email_node", route_email_after_eval, {
        "retry_email": "email_node", "needs_approval": "email_approval",
        "compile": "compile_response"})
    wf.add_edge("email_approval", "email_send")
    wf.add_edge("email_send", "compile_response")

    wf.add_conditional_edges("transfer_node", route_transfer_after_propose, {
        "needs_approval": "transfer_approval", "compile": "compile_response"})
    wf.add_edge("transfer_approval", "transfer_execute")
    wf.add_edge("transfer_execute", "compile_response")

    wf.add_edge("status_node", "compile_response")
    wf.add_edge("compile_response", END)

    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "checkpoints.sqlite")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    return wf.compile(checkpointer=SqliteSaver(conn))


graph = _build_graph()
