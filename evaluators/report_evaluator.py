from langchain_groq import ChatGroq
from workflows.schemas import ReportEvaluation

llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)
structured_llm = llm.with_structured_output(ReportEvaluation)


def evaluate_report(report_text: str) -> dict:
    prompt = f"""You are a senior executive reviewing a construction project report
that will be shown to C-level leadership. Score strictly, 0 (poor) to 2 (excellent).

REPORT:
{report_text}

Criteria:
- executive_summary: clear, concise, highlights the most critical issues
- data_accuracy: references specific numbers, dates, percentages throughout
- structure: has clear sections (Budget, Schedule, Risk, Recommendations)
- recommendations: specific, actionable, with owners and deadlines
- brevity: under 800 words, no fluff

Then provide 2-3 sentences of feedback on what must be fixed."""

    try:
        result: ReportEvaluation = structured_llm.invoke(prompt)
        return {
            "score": result.total,
            "max_score": 10,
            "passed": result.total >= 8,
            "feedback": result.feedback,
        }
    except Exception as e:
        return {
            "score": 0,
            "max_score": 10,
            "passed": False,
            "feedback": f"Evaluator failed to produce structured output ({e}). "
                        f"Rewrite the report ensuring each section is clearly labelled.",
        }
