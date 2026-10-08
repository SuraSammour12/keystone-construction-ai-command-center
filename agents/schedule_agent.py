"""
Schedule analysis agent. Hardened against hallucination: strict data rules,
temperature 0, and abstention when data is missing. Schedule data is the
project's recorded schedule of record.
"""
from langchain_groq import ChatGroq
from tools.data_loader import get_schedule_by_project, get_delayed_phases
from tools.calculator import calculate_schedule_risk

llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)

STRICT = (
    "STRICT DATA RULES:\n"
    "- Use ONLY the dates, phases and day counts in the DATA below.\n"
    "- Do NOT invent or estimate any date, number, or name not present in the DATA.\n"
    "- If something is not in the DATA, write 'not in records'.\n\n"
)


def run_schedule_analysis(project_id: str, project_name: str, feedback: str = "") -> str:
    schedule = get_schedule_by_project(project_id)
    if not schedule:
        return f"No schedule data in records for {project_id}."

    delayed_phases = get_delayed_phases(project_id)
    risk_level = calculate_schedule_risk(schedule["overall_delay_days"])

    feedback_section = ""
    if feedback:
        feedback_section = (
            f"\n\nREVISION REQUIRED. Fix these issues and remove any detail not in the DATA:\n{feedback}\n"
        )

    prompt = f"""{STRICT}You are a senior construction schedule analyst.

DATA for {project_name} ({project_id}):
OVERALL:
- Overall Delay: {schedule['overall_delay_days']} days
- Projected End Date: {schedule['projected_end_date']}
- Risk Level: {risk_level}
- Critical Path Items: {', '.join(schedule['critical_path_items'])}

ALL PHASES:
{_format_phases(schedule['phases'])}

DELAYED PHASES ({len(delayed_phases)}):
{_format_delayed(delayed_phases)}

Write a 3-4 paragraph schedule analysis covering overall health, root causes of
delays (from the recorded reasons), impact on future phases, and recommendations.
Use only the dates and numbers in the DATA.{feedback_section}"""

    return llm.invoke(prompt).content


def _format_phases(phases: list) -> str:
    return "\n".join(
        f"- {p['phase']}: {p['status']} | Planned: {p['planned_start']} to {p['planned_end']} "
        f"| Delay: {p['delay_days']} days" for p in phases
    )


def _format_delayed(delayed: list) -> str:
    if not delayed:
        return "No delayed phases."
    return "\n".join(
        f"- {p['phase']}: {p['delay_days']} days delayed - Reason: {p['delay_reason']}" for p in delayed
    )
