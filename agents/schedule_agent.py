from langchain_groq import ChatGroq
from tools.data_loader import get_schedule_by_project, get_delayed_phases
from tools.calculator import calculate_schedule_risk

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)


def run_schedule_analysis(project_id: str, project_name: str) -> str:
    """Analyze schedule status for a given project using real data + LLM interpretation"""

    # Step 1: Load raw data
    schedule = get_schedule_by_project(project_id)
    if not schedule:
        return f"No schedule data found for project {project_id}"

    delayed_phases = get_delayed_phases(project_id)
    risk_level = calculate_schedule_risk(schedule["overall_delay_days"])

    # Step 2: Send to LLM for professional analysis
    prompt = f"""You are a senior construction schedule analyst.
Analyze this schedule data and write a professional analysis.

PROJECT: {project_name} ({project_id})

OVERALL SCHEDULE:
- Overall Delay: {schedule['overall_delay_days']} days
- Projected End Date: {schedule['projected_end_date']}
- Risk Level: {risk_level}
- Critical Path Items: {', '.join(schedule['critical_path_items'])}

ALL PHASES:
{_format_phases(schedule['phases'])}

DELAYED PHASES ONLY ({len(delayed_phases)}):
{_format_delayed(delayed_phases)}

Write a 3-4 paragraph analysis covering:
1. Overall schedule health - is the project on time?
2. Root causes of delays - what went wrong and why?
3. Impact on future phases - will current delays cascade?
4. Recommendations - specific actions to get back on track

Be specific with dates and numbers. No generic advice."""

    response = llm.invoke(prompt)
    return response.content


def _format_phases(phases: list) -> str:
    """Format all phases into readable text"""
    lines = []
    for p in phases:
        lines.append(
            f"- {p['phase']}: {p['status']} | "
            f"Planned: {p['planned_start']} to {p['planned_end']} | "
            f"Delay: {p['delay_days']} days"
        )
    return "\n".join(lines)


def _format_delayed(delayed: list) -> str:
    """Format only delayed phases with reasons"""
    if not delayed:
        return "No delayed phases."
    lines = []
    for p in delayed:
        lines.append(
            f"- {p['phase']}: {p['delay_days']} days delayed — Reason: {p['delay_reason']}"
        )
    return "\n".join(lines)