"""
Risk Agent - a real ReAct agent: the LLM autonomously decides which project
data to fetch via tools. Hardened against hallucination: it must use only
values returned by the tools, invent nothing, and abstain when data is missing.
Temperature 0.
"""
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from tools.data_loader import (
    get_project_summary,
    get_contractors_by_project,
    get_pending_invoices,
    get_delayed_phases,
)
from tools.calculator import calculate_project_health

_llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)


@tool
def fetch_project_summary(project_id: str) -> dict:
    """Get a consolidated snapshot of a project: budget totals, schedule delay, contractors."""
    summary = get_project_summary(project_id)
    return summary or {"error": f"No summary for {project_id}"}


@tool
def fetch_contractors(project_id: str) -> list:
    """List contractors currently working on this project."""
    return get_contractors_by_project(project_id)


@tool
def fetch_pending_invoices(project_id: str) -> list:
    """List unapproved invoices; large or overdue ones are cash-flow risk signals."""
    return get_pending_invoices(project_id)


@tool
def fetch_delayed_phases(project_id: str) -> list:
    """List only phases that are behind schedule, with the recorded delay reasons."""
    return get_delayed_phases(project_id)


@tool
def compute_health(over_budget_pct: float, delay_days: int) -> str:
    """Classify overall health as HEALTHY / WATCH / AT RISK / CRITICAL."""
    return calculate_project_health(over_budget_pct, delay_days)


_TOOLS = [fetch_project_summary, fetch_contractors, fetch_pending_invoices,
          fetch_delayed_phases, compute_health]

_SYSTEM = """You are a senior construction risk analyst.

Use the available tools to gather the data you need. Do not guess, call tools to
get real numbers. You may call multiple tools.

STRICT DATA RULES:
- Reference ONLY numbers, names and dates returned by the tools. Copy them exactly.
- Do NOT invent, estimate, or infer any figure, percentage, name, or date.
- If a value is not returned by any tool, write 'not in records' instead of guessing.

Once you have enough information, produce a risk analysis with:
1. Top 3-5 risks, each with: one-sentence description, Severity (HIGH/MEDIUM/LOW),
   Impact, and a specific Mitigation.
2. Overall risk rating: CRITICAL / HIGH / MODERATE / LOW.
3. One paragraph summary with your top recommendation.

Be specific and use only the numbers from the tool outputs."""

_risk_agent = create_react_agent(_llm, _TOOLS, state_modifier=_SYSTEM)


def run_risk_analysis(project_id: str, project_name: str, feedback: str = "") -> str:
    user_msg = f"Analyze risks for project {project_id} ({project_name})."
    if feedback:
        user_msg += (
            f"\n\nPrior version was rejected. Fix these issues and remove any detail "
            f"not returned by the tools:\n{feedback}"
        )
    result = _risk_agent.invoke({"messages": [("user", user_msg)]})
    return result["messages"][-1].content
