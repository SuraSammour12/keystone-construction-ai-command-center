from langchain_groq import ChatGroq
from workflows.schemas import EmailEvaluation

llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)
structured_llm = llm.with_structured_output(EmailEvaluation)


def evaluate_email(email_text: str, purpose: str) -> dict:
    prompt = f"""You are a communications director reviewing an email before it is sent.
Score strictly, 0 (poor) to 2 (excellent).

EMAIL:
{email_text}

INTENDED PURPOSE: {purpose}

Criteria:
- subject_line: clear, specific, tells the reader what to expect
- tone: professional, appropriate for the situation
- clarity: key message is obvious within the first 2 sentences
- action_items: clear what the recipient needs to do and by when
- purpose_match: the email achieves its stated purpose

Then provide 2-3 sentences of feedback on what to improve before sending."""

    try:
        result: EmailEvaluation = structured_llm.invoke(prompt)
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
            "feedback": f"Evaluator failed to produce structured output ({e}). Rewrite the email.",
        }
