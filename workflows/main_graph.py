from typing import TypedDict, Literal, Optional
from langgraph.graph import StateGraph, END
from agents.budget_agent import run_budget_analysis
from agents.schedule_agent import run_schedule_analysis
from agents.risk_agent import run_risk_analysis
from agents.report_agent import generate_report
from agents.email_agent import draft_email
from agents.budget_transfer_agent import propose_budget_transfer
from evaluators.analysis_evaluator import evaluate_analysis
from evaluators.report_evaluator import evaluate_report
from evaluators.email_evaluator import evaluate_email
from tools.data_loader import get_project_by_name, get_all_projects_overview


# ============================================================
# STATE - The shared memory that flows through the entire graph
# ============================================================

class CommandCenterState(TypedDict):
    # User input
    user_request: str
    project_id: str
    project_name: str

    # Orchestrator decision
    task_type: str  # "report" | "email" | "transfer" | "status" | "unknown"

    # Agent outputs
    budget_analysis: str
    schedule_analysis: str
    risk_analysis: str
    report: str
    email_draft: dict
    transfer_proposal: dict

    # Evaluator tracking
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

    # Loop control
    attempt: int
    max_attempts: int

    # Human-in-the-loop
    requires_approval: bool
    approval_type: str  # "email" | "transfer" | "none"
    approval_status: str  # "pending" | "approved" | "rejected"

    # Final output
    final_response: str
    error: str


# ============================================================
# NODE 1: ORCHESTRATOR - Understands the request and routes it
# ============================================================

def orchestrator_node(state: CommandCenterState) -> dict:
    """Parse the user request and decide which agents to call"""

    request = state["user_request"].lower()

    # Detect project name from request
    project_id = state.get("project_id", "")
    project_name = state.get("project_name", "")

    if not project_id:
        # Try to find project from the request text
        keywords = ["alpha", "beta", "gamma"]
        for kw in keywords:
            if kw in request:
                project = get_project_by_name(kw)
                if project:
                    project_id = project["id"]
                    project_name = project["name"]
                    break

    # If still no project found, default to first project
    if not project_id:
        overview = get_all_projects_overview()
        if overview:
            project_id = overview[0]["id"]
            project_name = overview[0]["name"]

    # Determine task type
    task_type = "unknown"
    if any(word in request for word in ["report", "تقرير", "status", "وضع", "حالة", "analyze", "حلل"]):
        task_type = "report"
    elif any(word in request for word in ["email", "إيميل", "ايميل", "send", "ابعت", "اكتب", "draft", "رسالة"]):
        task_type = "email"
    elif any(word in request for word in ["transfer", "حوّل", "حول", "نقل", "move budget", "انقل"]):
        task_type = "transfer"
    elif any(word in request for word in ["overview", "all projects", "dashboard", "كل المشاريع", "ملخص"]):
        task_type = "status"

    return {
        "project_id": project_id,
        "project_name": project_name,
        "task_type": task_type,
        "attempt": 0,
        "max_attempts": 3
    }


# ============================================================
# NODE 2: BUDGET ANALYSIS + EVALUATION LOOP
# ============================================================

def budget_analysis_node(state: CommandCenterState) -> dict:
    """Run budget analysis with evaluator-optimizer loop"""

    analysis = state.get("budget_analysis", "")
    feedback = state.get("budget_eval_feedback", "")

    # If there is feedback from a previous attempt, prepend it
    if feedback and analysis:
        # Re-run with feedback context (the agent will produce a better version)
        pass

    analysis = run_budget_analysis(state["project_id"], state["project_name"])

    # Evaluate
    evaluation = evaluate_analysis(analysis, "budget")

    return {
        "budget_analysis": analysis,
        "budget_eval_score": evaluation["score"],
        "budget_eval_feedback": evaluation["feedback"]
    }


# ============================================================
# NODE 3: SCHEDULE ANALYSIS + EVALUATION LOOP
# ============================================================

def schedule_analysis_node(state: CommandCenterState) -> dict:
    """Run schedule analysis with evaluator-optimizer loop"""

    analysis = run_schedule_analysis(state["project_id"], state["project_name"])

    # Evaluate
    evaluation = evaluate_analysis(analysis, "schedule")

    return {
        "schedule_analysis": analysis,
        "schedule_eval_score": evaluation["score"],
        "schedule_eval_feedback": evaluation["feedback"]
    }


# ============================================================
# NODE 4: RISK ANALYSIS + EVALUATION LOOP
# ============================================================

def risk_analysis_node(state: CommandCenterState) -> dict:
    """Run risk analysis with evaluator-optimizer loop"""

    analysis = run_risk_analysis(state["project_id"], state["project_name"])

    # Evaluate
    evaluation = evaluate_analysis(analysis, "risk")

    return {
        "risk_analysis": analysis,
        "risk_eval_score": evaluation["score"],
        "risk_eval_feedback": evaluation["feedback"]
    }


# ============================================================
# NODE 5: REPORT GENERATION + EVALUATION LOOP
# ============================================================

def report_generation_node(state: CommandCenterState) -> dict:
    """Generate executive report from all analyses, with evaluation loop"""

    report = generate_report(
        state["project_name"],
        state["budget_analysis"],
        state["schedule_analysis"],
        state["risk_analysis"]
    )

    # Evaluate the report
    evaluation = evaluate_report(report)

    attempt = state.get("attempt", 0) + 1

    return {
        "report": report,
        "report_eval_score": evaluation["score"],
        "report_eval_feedback": evaluation["feedback"],
        "attempt": attempt
    }


# ============================================================
# NODE 6: EMAIL DRAFTING + EVALUATION LOOP
# ============================================================

def email_drafting_node(state: CommandCenterState) -> dict:
    """Draft an email with evaluation loop"""

    # Extract email details from the request
    request = state["user_request"]

    email_result = draft_email(
        context=f"Project: {state['project_name']}. Request: {request}",
        recipient="contractor",
        purpose=request
    )

    # Evaluate the email
    evaluation = evaluate_email(email_result["email"], request)

    attempt = state.get("attempt", 0) + 1

    return {
        "email_draft": email_result,
        "email_eval_score": evaluation["score"],
        "email_eval_feedback": evaluation["feedback"],
        "attempt": attempt,
        "requires_approval": email_result["requires_approval"],
        "approval_type": "email" if email_result["requires_approval"] else "none",
        "approval_status": "pending" if email_result["requires_approval"] else "approved"
    }


# ============================================================
# NODE 7: BUDGET TRANSFER
# ============================================================

def budget_transfer_node(state: CommandCenterState) -> dict:
    """Propose a budget transfer - always requires approval"""

    # For demo purposes, transfer from Beta (has surplus) to Alpha (over budget)
    proposal = propose_budget_transfer("PRJ-002", "PRJ-001")

    if "error" in proposal:
        return {
            "error": proposal["error"],
            "final_response": f"Transfer failed: {proposal['error']}"
        }

    return {
        "transfer_proposal": proposal,
        "requires_approval": True,
        "approval_type": "transfer",
        "approval_status": "pending"
    }


# ============================================================
# NODE 8: STATUS OVERVIEW
# ============================================================

def status_overview_node(state: CommandCenterState) -> dict:
    """Generate a quick overview of all projects"""

    overview = get_all_projects_overview()

    lines = ["=== ALL PROJECTS OVERVIEW ===\n"]
    for proj in overview:
        flag_label = {"GREEN": "[OK]", "YELLOW": "[AT RISK]", "RED": "[CRITICAL]"}.get(proj["flag"], "[--]")
        lines.append(
            f"{flag_label} {proj['name']} ({proj['id']})\n"
            f"   Status: {proj['status']}\n"
            f"   Budget: ${proj['budget_spent']:,} / ${proj['budget_total']:,}\n"
            f"   Delay: {proj['delay_days']} days\n"
        )

    return {
        "final_response": "\n".join(lines),
        "requires_approval": False
    }


# ============================================================
# NODE 9: COMPILE FINAL RESPONSE
# ============================================================

def compile_response_node(state: CommandCenterState) -> dict:
    """Compile the final response based on task type"""

    task = state["task_type"]

    if task == "report":
        response = (
            f"📊 PROJECT REPORT: {state['project_name']}\n"
            f"{'=' * 50}\n\n"
            f"{state.get('report', 'No report generated.')}\n\n"
            f"{'=' * 50}\n"
            f"Quality Scores:\n"
            f"  Budget Analysis: {state.get('budget_eval_score', 'N/A')}/10\n"
            f"  Schedule Analysis: {state.get('schedule_eval_score', 'N/A')}/10\n"
            f"  Risk Analysis: {state.get('risk_eval_score', 'N/A')}/10\n"
            f"  Final Report: {state.get('report_eval_score', 'N/A')}/10\n"
            f"  Attempts: {state.get('attempt', 1)}"
        )

    elif task == "email":
        email = state.get("email_draft", {})
        response = (
            f"✉️ EMAIL DRAFT\n"
            f"{'=' * 50}\n"
            f"Sensitivity: {email.get('sensitivity', 'N/A')}\n"
            f"Requires Approval: {email.get('requires_approval', False)}\n"
            f"{'=' * 50}\n\n"
            f"{email.get('email', 'No email generated.')}\n\n"
            f"Quality Score: {state.get('email_eval_score', 'N/A')}/10"
        )

    elif task == "transfer":
        proposal = state.get("transfer_proposal", {})
        transfer = proposal.get("transfer", {})
        response = (
            f"💰 BUDGET TRANSFER PROPOSAL\n"
            f"{'=' * 50}\n"
            f"From: {transfer.get('from_project', 'N/A')}\n"
            f"To: {transfer.get('to_project', 'N/A')}\n"
            f"Amount: ${transfer.get('amount', 0):,}\n\n"
            f"Impact Analysis:\n{proposal.get('impact_analysis', 'N/A')}\n\n"
            f"⚠️ STATUS: AWAITING HUMAN APPROVAL"
        )

    else:
        response = state.get("final_response", "I couldn't understand the request. Please try again.")

    return {"final_response": response}


# ============================================================
# ROUTING FUNCTIONS
# ============================================================

def route_by_task(state: CommandCenterState) -> str:
    """Route to the correct workflow based on task type"""
    task = state["task_type"]
    if task == "report":
        return "analyze"
    elif task == "email":
        return "email"
    elif task == "transfer":
        return "transfer"
    elif task == "status":
        return "status"
    else:
        return "compile"


def should_retry_report(state: CommandCenterState) -> Literal["retry", "compile"]:
    """Decide if the report needs another attempt"""
    score = state.get("report_eval_score", 0)
    attempt = state.get("attempt", 0)
    max_attempts = state.get("max_attempts", 3)

    if score >= 8 or attempt >= max_attempts:
        return "compile"
    return "retry"


def should_retry_email(state: CommandCenterState) -> Literal["retry", "compile"]:
    """Decide if the email needs another attempt"""
    score = state.get("email_eval_score", 0)
    attempt = state.get("attempt", 0)
    max_attempts = state.get("max_attempts", 3)

    if score >= 8 or attempt >= max_attempts:
        return "compile"
    return "retry"


# ============================================================
# BUILD THE GRAPH
# ============================================================

def build_command_center_graph():
    """Construct the full LangGraph workflow"""

    workflow = StateGraph(CommandCenterState)

    # Add all nodes
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("budget_analysis", budget_analysis_node)
    workflow.add_node("schedule_analysis", schedule_analysis_node)
    workflow.add_node("risk_analysis", risk_analysis_node)
    workflow.add_node("report_generation", report_generation_node)
    workflow.add_node("email_drafting", email_drafting_node)
    workflow.add_node("budget_transfer", budget_transfer_node)
    workflow.add_node("status_overview", status_overview_node)
    workflow.add_node("compile_response", compile_response_node)

    # Entry point
    workflow.set_entry_point("orchestrator")

    # Orchestrator routes to the correct workflow
    workflow.add_conditional_edges(
        "orchestrator",
        route_by_task,
        {
            "analyze": "budget_analysis",
            "email": "email_drafting",
            "transfer": "budget_transfer",
            "status": "status_overview",
            "compile": "compile_response"
        }
    )

    # Report workflow: Budget → Schedule → Risk → Report (parallel would be better but sequential is clearer)
    workflow.add_edge("budget_analysis", "schedule_analysis")
    workflow.add_edge("schedule_analysis", "risk_analysis")
    workflow.add_edge("risk_analysis", "report_generation")

    # Report evaluation loop
    workflow.add_conditional_edges(
        "report_generation",
        should_retry_report,
        {
            "retry": "report_generation",
            "compile": "compile_response"
        }
    )

    # Email evaluation loop
    workflow.add_conditional_edges(
        "email_drafting",
        should_retry_email,
        {
            "retry": "email_drafting",
            "compile": "compile_response"
        }
    )

    # Transfer and Status go straight to compile
    workflow.add_edge("budget_transfer", "compile_response")
    workflow.add_edge("status_overview", "compile_response")

    # Compile is the end
    workflow.add_edge("compile_response", END)

    return workflow.compile()


# ============================================================
# RUN FUNCTION - Entry point for the API
# ============================================================

def run_command_center(user_request: str, project_id: str = "", project_name: str = "") -> dict:
    """Main entry point - takes a user request and returns the full result"""

    graph = build_command_center_graph()

    initial_state = {
        "user_request": user_request,
        "project_id": project_id,
        "project_name": project_name,
        "task_type": "",
        "budget_analysis": "",
        "schedule_analysis": "",
        "risk_analysis": "",
        "report": "",
        "email_draft": {},
        "transfer_proposal": {},
        "budget_eval_score": 0,
        "schedule_eval_score": 0,
        "risk_eval_score": 0,
        "report_eval_score": 0,
        "email_eval_score": 0,
        "budget_eval_feedback": "",
        "schedule_eval_feedback": "",
        "risk_eval_feedback": "",
        "report_eval_feedback": "",
        "email_eval_feedback": "",
        "attempt": 0,
        "max_attempts": 3,
        "requires_approval": False,
        "approval_type": "none",
        "approval_status": "",
        "final_response": "",
        "error": ""
    }

    result = graph.invoke(initial_state)

    return {
        "response": result["final_response"],
        "task_type": result["task_type"],
        "project": result["project_name"],
        "requires_approval": result["requires_approval"],
        "approval_type": result.get("approval_type", "none"),
        "scores": {
            "budget": result.get("budget_eval_score", 0),
            "schedule": result.get("schedule_eval_score", 0),
            "risk": result.get("risk_eval_score", 0),
            "report": result.get("report_eval_score", 0),
            "email": result.get("email_eval_score", 0)
        },
        "attempts": result.get("attempt", 0)
    }