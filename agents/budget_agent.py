from langchain_groq import ChatGroq
from tools.data_loader import get_budget_by_project, get_pending_invoices
from tools.calculator import calculate_budget_variance

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)


def run_budget_analysis(project_id: str, project_name: str) -> str:
    """Analyze budget status for a given project using real data + LLM interpretation"""

    # Step 1: Load raw data
    budget = get_budget_by_project(project_id)
    if not budget:
        return f"No budget data found for project {project_id}"

    pending_invoices = get_pending_invoices(project_id)

    # Step 2: Calculate variance for each category
    breakdown_analysis = []
    for item in budget["breakdown"]:
        variance = calculate_budget_variance(item["budgeted"], item["actual"])
        breakdown_analysis.append({
            "category": item["category"],
            "note": item["note"],
            **variance
        })

    # Step 3: Build the overall picture
    overall_variance = calculate_budget_variance(budget["total_budget"], budget["spent_to_date"])

    # Step 4: Send everything to the LLM for professional analysis
    prompt = f"""You are a senior construction budget analyst. 
Analyze this budget data and write a professional analysis.

PROJECT: {project_name} ({project_id})

OVERALL BUDGET:
- Total Budget: ${budget['total_budget']:,}
- Spent to Date: ${budget['spent_to_date']:,}
- Remaining: ${budget['remaining']:,}
- Status: {overall_variance['status']} by {abs(overall_variance['variance_pct'])}%

CATEGORY BREAKDOWN:
{_format_breakdown(breakdown_analysis)}

PENDING INVOICES ({len(pending_invoices)} awaiting approval):
{_format_invoices(pending_invoices)}

Write a 3-4 paragraph analysis covering:
1. Overall budget health - is the project on track financially?
2. Problem areas - which categories are over budget and why?
3. Pending invoices - any concerns?
4. Recommendations - specific actions to take

Be specific with numbers. No generic advice."""

    response = llm.invoke(prompt)
    return response.content


def _format_breakdown(breakdown: list) -> str:
    """Format budget breakdown into readable text for the LLM"""
    lines = []
    for item in breakdown:
        lines.append(
            f"- {item['category']}: Budgeted ${item['budgeted']:,} | "
            f"Actual ${item['actual']:,} | "
            f"{item['status']} ({item['variance_pct']}%) | "
            f"Note: {item['note']}"
        )
    return "\n".join(lines)


def _format_invoices(invoices: list) -> str:
    """Format pending invoices into readable text for the LLM"""
    if not invoices:
        return "No pending invoices."
    lines = []
    for inv in invoices:
        lines.append(
            f"- {inv['id']}: {inv['contractor']} - ${inv['amount']:,} - Due: {inv['due_date']}"
        )
    return "\n".join(lines)