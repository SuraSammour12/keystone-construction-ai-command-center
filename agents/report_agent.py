from langchain_groq import ChatGroq

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3)


def generate_report(project_name: str, budget_analysis: str, schedule_analysis: str, risk_analysis: str) -> str:
    """Combine all analyses into one professional executive report"""

    prompt = f"""You are a senior project manager writing an executive report.
Combine these three analyses into ONE professional report.

PROJECT: {project_name}

=== BUDGET ANALYSIS ===
{budget_analysis}

=== SCHEDULE ANALYSIS ===
{schedule_analysis}

=== RISK ANALYSIS ===
{risk_analysis}

Write a professional executive report with these sections:
1. EXECUTIVE SUMMARY - One paragraph, the most important findings
2. BUDGET STATUS - Key numbers and concerns
3. SCHEDULE STATUS - Key dates and delays
4. RISK ASSESSMENT - Top risks with severity
5. RECOMMENDATIONS - Numbered list of specific actions
6. NEXT STEPS - What needs to happen this week

Rules:
- Professional tone suitable for C-level executives
- Every claim must reference specific numbers from the analyses
- Recommendations must be actionable (who, what, when)
- Keep it under 800 words"""

    response = llm.invoke(prompt)
    return response.content