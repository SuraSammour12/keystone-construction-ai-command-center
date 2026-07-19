from langchain_groq import ChatGroq
from tools.data_loader import get_budget_by_project, get_project_by_id

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)


def propose_budget_transfer(from_project_id: str, to_project_id: str, amount: float = None) -> dict:
    """Propose a budget transfer between two projects - always requires human approval"""

    # Step 1: Load both project budgets
    from_budget = get_budget_by_project(from_project_id)
    to_budget = get_budget_by_project(to_project_id)
    from_project = get_project_by_id(from_project_id)
    to_project = get_project_by_id(to_project_id)

    if not from_budget or not to_budget:
        return {"error": "Budget data not found for one or both projects"}

    # Step 2: Calculate safe transfer amount if not specified
    if amount is None:
        available = from_budget["remaining"]
        if available <= 0:
            return {"error": f"Project {from_project_id} has no remaining budget to transfer"}
        amount = round(available * 0.5, 2)  # Suggest transferring 50% of remaining

    # Step 3: Validate the transfer
    if amount > from_budget["remaining"]:
        return {
            "error": f"Requested ${amount:,} exceeds available ${from_budget['remaining']:,} in {from_project_id}"
        }

    # Step 4: Ask LLM for impact analysis
    prompt = f"""You are a financial analyst. Analyze this proposed budget transfer.

TRANSFER: ${amount:,} from {from_project['name']} to {to_project['name']}

SOURCE PROJECT ({from_project['name']}):
- Total Budget: ${from_budget['total_budget']:,}
- Spent: ${from_budget['spent_to_date']:,}
- Remaining BEFORE transfer: ${from_budget['remaining']:,}
- Remaining AFTER transfer: ${from_budget['remaining'] - amount:,}

DESTINATION PROJECT ({to_project['name']}):
- Total Budget: ${to_budget['total_budget']:,}
- Spent: ${to_budget['spent_to_date']:,}
- Remaining BEFORE transfer: ${to_budget['remaining']:,}
- Remaining AFTER transfer: ${to_budget['remaining'] + amount:,}

Provide:
1. Is this transfer safe for the source project? (Yes/No with reason)
2. How does this help the destination project?
3. Any risks?
4. Your recommendation (Approve / Approve with conditions / Reject)

Keep it to 2-3 short paragraphs."""

    response = llm.invoke(prompt)

    return {
        "transfer": {
            "from_project": from_project["name"],
            "to_project": to_project["name"],
            "amount": amount,
            "from_remaining_before": from_budget["remaining"],
            "from_remaining_after": from_budget["remaining"] - amount,
            "to_remaining_before": to_budget["remaining"],
            "to_remaining_after": to_budget["remaining"] + amount
        },
        "impact_analysis": response.content,
        "requires_approval": True,  # Always requires human approval
        "approval_reason": "All budget transfers require human authorization"
    }