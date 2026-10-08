from langchain_groq import ChatGroq
from workflows.schemas import EmailSensitivity

drafter = ChatGroq(model="openai/gpt-oss-120b", temperature=0.3)
classifier = ChatGroq(model="openai/gpt-oss-20b", temperature=0)
sensitivity_llm = classifier.with_structured_output(EmailSensitivity)


def draft_email(context: str, recipient: str, purpose: str, feedback: str = "") -> dict:
    feedback_section = ""
    if feedback:
        feedback_section = (
            f"\n\nREVISION REQUIRED — Previous draft was rejected. Fix these issues:\n"
            f"{feedback}\n"
            f"Your revised email must address each point above.\n"
        )

    draft_prompt = f"""Write a professional email.

CONTEXT: {context}
RECIPIENT: {recipient}
PURPOSE: {purpose}

Include:
- Clear subject line (on its own line starting with "Subject: ")
- Professional greeting addressing the recipient
- Clear body with the key message
- Specific action items or requests
- Professional closing
- Signature placeholder [Your Name]{feedback_section}"""

    email_content = drafter.invoke(draft_prompt).content

    classify_prompt = f"""Classify this email's sensitivity level.

EMAIL:
{email_content}

CONTEXT: {context}

Rules:
- LOW: routine updates, meeting confirmations, general info
- MEDIUM: project concerns, schedule changes, budget discussions
- HIGH: contract disputes, legal issues, payments over $50,000, complaints"""

    try:
        classification: EmailSensitivity = sensitivity_llm.invoke(classify_prompt)
        sensitivity = classification.sensitivity
    except Exception:
        sensitivity = "MEDIUM"  # safe default: require approval

    return {
        "email": email_content,
        "sensitivity": sensitivity,
        "recipient": recipient,
        "requires_approval": sensitivity in ("MEDIUM", "HIGH"),
    }
