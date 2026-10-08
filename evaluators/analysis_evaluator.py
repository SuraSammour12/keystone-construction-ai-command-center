from langchain_groq import ChatGroq
from workflows.schemas import AnalysisEvaluation

# Smaller/faster model for evaluation — cost-aware, and reduces same-model bias.
llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)
structured_llm = llm.with_structured_output(AnalysisEvaluation)


def evaluate_analysis(analysis_text: str, analysis_type: str) -> dict:
    prompt = f"""You are a strict quality reviewer for construction project analyses.
Score this {analysis_type} analysis on each criterion from 0 (poor) to 2 (excellent).

ANALYSIS:
{analysis_text}

Criteria:
- data_usage: references specific numbers, dates, percentages
- root_cause: explains WHY problems exist, not just WHAT
- specificity: recommendations are specific and actionable
- completeness: covers all important aspects
- professionalism: tone and structure are professional

Then provide 2-3 sentences of feedback on what to improve."""

    try:
        result: AnalysisEvaluation = structured_llm.invoke(prompt)
        return {
            "score": result.total,
            "max_score": 10,
            "passed": result.total >= 7,
            "feedback": result.feedback,
        }
    except Exception as e:
        # Structured parsing failed — do NOT silently pass. Fail low so we retry.
        return {
            "score": 0,
            "max_score": 10,
            "passed": False,
            "feedback": f"Evaluator failed to produce structured output ({e}). "
                        f"Regenerate the analysis with stricter adherence to the requested format.",
        }
