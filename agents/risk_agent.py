from langchain_groq import ChatGroq
from tools.data_loader import get_project_summary
from tools.calculator import calculate_project_health

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)


def run_risk_analysis(project_id: str, project_name: str) -> str:
    """Analyze risks by combining budget + schedule data"""

    # Step 1: Load the full project summary
    summary = get_project_summary(project_id)
    if not summary:
        return f"No data found for project {project_id}"

    # Step 2: Calculate overall health
    health = calculate_project_health(
        summary["budget"]["over_budget_pct"],
        summary["schedule"]["overall_delay_days"]
    )

    # Step 3: Send to LLM for risk analysis
    prompt = f"""You are a senior construction risk analyst.
Analyze this project data and identify all risks.

PROJECT: {project_name} ({project_id})
OVERALL HEALTH: {health}

BUDGET STATUS:
- Total: ${summary['budget']['total']:,}
- Spent: ${summary['budget']['spent']:,}
- Over Budget: {summary['budget']['over_budget_pct']}%
- Pending Invoices: {len(summary['budget']['pending_invoices'])}

SCHEDULE STATUS:
- Delay: {summary['schedule']['overall_delay_days']} days
- Projected End: {summary['schedule']['projected_end_date']}
- Delayed Phases: {len(summary['schedule']['delayed_phases'])}
- Critical Path: {', '.join(summary['schedule']['critical_path'])}

CONTRACTORS: {len(summary['contractors'])} active

Provide a risk analysis with:
1. List the top 3-5 risks, each with:
   - Risk description (one sentence)
   - Severity: HIGH / MEDIUM / LOW
   - Impact: what happens if this risk materializes
   - Mitigation: specific action to reduce the risk

2. Overall risk rating for the project: CRITICAL / HIGH / MODERATE / LOW

3. One paragraph summary with your top recommendation.

Be specific. Reference actual numbers from the data."""

    response = llm.invoke(prompt)
    return response.content