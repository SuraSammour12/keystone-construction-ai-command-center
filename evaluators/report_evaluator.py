from langchain_groq import ChatGroq

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)


def evaluate_report(report_text: str) -> dict:
    """Evaluate the quality of an executive project report"""

    prompt = f"""You are a senior executive reviewing a construction project report.
Evaluate it strictly - this report goes to C-level leadership.

REPORT TO EVALUATE:
{report_text}

Score each criterion from 0-2:
1. EXECUTIVE SUMMARY - Clear, concise, highlights the most critical issues? (0-2)
2. DATA ACCURACY - References specific numbers, dates, percentages throughout? (0-2)
3. STRUCTURE - Has clear sections (Budget, Schedule, Risk, Recommendations)? (0-2)
4. RECOMMENDATIONS - Specific, actionable, with owners and deadlines? (0-2)
5. BREVITY - Under 800 words, no fluff, every sentence adds value? (0-2)

Respond in this EXACT format:
EXECUTIVE_SUMMARY: [0-2]
DATA_ACCURACY: [0-2]
STRUCTURE: [0-2]
RECOMMENDATIONS: [0-2]
BREVITY: [0-2]
TOTAL: [sum out of 10]
FEEDBACK: [2-3 sentences on what must be fixed before sending to executives]"""

    response = llm.invoke(prompt)
    content = response.content

    try:
        total = int(content.split("TOTAL:")[1].split("\n")[0].strip())
        feedback = content.split("FEEDBACK:")[1].strip()
    except (IndexError, ValueError):
        total = 5
        feedback = "Could not parse evaluation. Defaulting to average score."

    return {
        "score": total,
        "max_score": 10,
        "passed": total >= 8,
        "feedback": feedback,
        "raw_evaluation": content
    }