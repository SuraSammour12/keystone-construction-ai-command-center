"""
Budget transfer proposal.

The numbers here come from the live system of record (finance_core over the
ledger), never from the model. The LLM is used only to suggest an amount when
none is given and to write the impact narrative. Every figure in the proposal,
and the deterministic safety check, come from code.
"""
import re
from contextlib import closing

from langchain_groq import ChatGroq

from tools import db, finance_core as fc

llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)


def _project_name(conn, pid: str) -> str:
    row = conn.execute("SELECT name FROM projects WHERE id=?", (pid,)).fetchone()
    return row["name"] if row else pid


def propose_budget_transfer(from_project_id: str, to_project_id: str, amount: float = None) -> dict:
    with closing(db.get_conn()) as conn:
        if not conn.execute("SELECT 1 FROM projects WHERE id=?", (from_project_id,)).fetchone() \
           or not conn.execute("SELECT 1 FROM projects WHERE id=?", (to_project_id,)).fetchone():
            return {"error": "Budget data not found for one or both projects"}

        from_name = _project_name(conn, from_project_id)
        to_name = _project_name(conn, to_project_id)
        src = fc.project_budget(conn, from_project_id)
        dst = fc.project_budget(conn, to_project_id)

        # Ask the LLM to propose an amount only if none was given.
        if amount is None:
            propose_prompt = f"""You are a construction CFO. Propose a safe budget transfer amount
(a single dollar figure, no explanation) from {from_name} to {to_name}.

SOURCE - {from_name}:
  Total ${src['budget_total']:,.0f} | Spent ${src['spent']:,.0f} | Remaining ${src['remaining']:,.0f}

DESTINATION - {to_name}:
  Total ${dst['budget_total']:,.0f} | Spent ${dst['spent']:,.0f} | Remaining ${dst['remaining']:,.0f}

Reply with ONLY a number (integer dollars), e.g. 750000"""
            proposed_raw = llm.invoke(propose_prompt).content
            digits = re.sub(r"[^\d]", "", proposed_raw)
            try:
                amount = float(digits) if digits else max(src["remaining"] * 0.5, 0)
            except ValueError:
                amount = max(src["remaining"] * 0.5, 0)

        # Deterministic safety check against the live ledger.
        check = fc.check_transfer(conn, from_project_id, to_project_id, amount)
        if not check["ok"]:
            return {"error": check["reason"]}

        amount = check["amount"]
        analyze_prompt = f"""You are a financial analyst. Analyze this proposed budget transfer.

TRANSFER: ${amount:,.0f} from {from_name} to {to_name}

SOURCE ({from_name}):
- Total Budget: ${src['budget_total']:,.0f} | Spent: ${src['spent']:,.0f}
- Remaining BEFORE: ${check['from_remaining_before']:,.0f} | AFTER: ${check['from_remaining_after']:,.0f}

DESTINATION ({to_name}):
- Total Budget: ${dst['budget_total']:,.0f} | Spent: ${dst['spent']:,.0f}
- Remaining BEFORE: ${check['to_remaining_before']:,.0f} | AFTER: ${check['to_remaining_after']:,.0f}

Provide: (1) Is this safe for the source? (2) How does it help the destination?
(3) Risks. (4) Recommendation (Approve / Approve with conditions / Reject).
2-3 short paragraphs."""
        analysis = llm.invoke(analyze_prompt).content

        return {
            "transfer": {
                "from_project": from_name,
                "to_project": to_name,
                "amount": amount,
                "from_remaining_before": check["from_remaining_before"],
                "from_remaining_after": check["from_remaining_after"],
                "to_remaining_before": check["to_remaining_before"],
                "to_remaining_after": check["to_remaining_after"],
            },
            "impact_analysis": analysis,
            "requires_approval": True,
            "approval_reason": "All budget transfers require human authorization",
        }
