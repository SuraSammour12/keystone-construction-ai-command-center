from langchain_groq import ChatGroq

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)


def evaluate_email(email_text: str, purpose: str) -> dict:
    """Evaluate the quality of a drafted email"""

    prompt = f"""You are a communications director reviewing an email before it is sent.
Evaluate it strictly.

EMAIL TO EVALUATE:
{email_text}

INTENDED PURPOSE: {purpose}

Score each criterion from 0-2:
1. SUBJECT LINE - Clear, specific, tells the reader what to expect? (0-2)
2. TONE - Professional, appropriate for the situation? (0-2)
3. CLARITY - Key message is obvious within the first 2 sentences? (0-2)
4. ACTION ITEMS - Clear what the recipient needs to do and by when? (0-2)
5. PURPOSE MATCH - Does the email achieve its stated purpose? (0-2)

Respond in this EXACT format:
SUBJECT_LINE: [0-2]
TONE: [0-2]
CLARITY: [0-2]
ACTION_ITEMS: [0-2]
PURPOSE_MATCH: [0-2]
TOTAL: [sum out of 10]
FEEDBACK: [2-3 sentences on what to improve before sending]"""

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