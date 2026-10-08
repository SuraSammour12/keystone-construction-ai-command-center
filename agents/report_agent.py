"""
Executive report agent. The report combines the three analyses. It is the
most hallucination-prone step, so the rules here are the strictest: it may use
only numbers that already appear in the three analyses, must not introduce any
new figure, percentage, name or date, and must not invent dollar amounts in its
recommendations. Temperature 0. A downstream deterministic grounding check
verifies every dollar figure and, if any is ungrounded, the report is
regenerated with that figure fed back (a Chain-of-Verification style loop).
"""
from langchain_groq import ChatGroq

llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)

STRICT = (
    "ABSOLUTE DATA RULES (a financial report, accuracy is mandatory):\n"
    "- You may use ONLY numbers, percentages, names and dates that already appear "
    "in the three analyses provided. Copy them exactly.\n"
    "- Do NOT introduce, compute, sum, project, or estimate any new number or "
    "percentage. If a total is not given, do not invent it; write 'not in records'.\n"
    "- In RECOMMENDATIONS and NEXT STEPS, describe actions and owners, but do NOT "
    "attach invented dollar amounts or savings figures. State targets qualitatively "
    "(for example 'negotiate a discount') rather than fabricating a number.\n"
    "- If asked for something not supported by the analyses, state it is not in the records.\n\n"
)


def generate_report(project_name, budget_analysis, schedule_analysis, risk_analysis, feedback="") -> str:
    feedback_section = ""
    if feedback:
        feedback_section = (
            f"\n\nREVISION REQUIRED. This report was rejected. Every point below must be fixed, "
            f"and any figure not present in the analyses must be removed:\n{feedback}\n"
        )

    prompt = f"""{STRICT}You are a senior project manager writing an executive report.
Combine these three analyses into ONE professional report. Use only their contents.

PROJECT: {project_name}

=== BUDGET ANALYSIS ===
{budget_analysis}

=== SCHEDULE ANALYSIS ===
{schedule_analysis}

=== RISK ANALYSIS ===
{risk_analysis}

Sections: 1. EXECUTIVE SUMMARY, 2. BUDGET STATUS, 3. SCHEDULE STATUS,
4. RISK ASSESSMENT, 5. RECOMMENDATIONS (actions and owners, no invented figures),
6. NEXT STEPS. Keep it under 800 words. Every figure must come from the analyses.{feedback_section}"""

    return llm.invoke(prompt).content
