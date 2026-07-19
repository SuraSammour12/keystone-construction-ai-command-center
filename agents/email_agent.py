from langchain_groq import ChatGroq

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3)


def draft_email(context: str, recipient: str, purpose: str) -> dict:
    """Draft a professional email and classify its sensitivity"""

    # Step 1: Generate the email
    prompt = f"""Write a professional email.

CONTEXT: {context}
RECIPIENT: {recipient}
PURPOSE: {purpose}

Include:
- Clear subject line (on its own line starting with "Subject: ")
- Professional greeting
- Clear body with the key message
- Specific action items or requests
- Professional closing
- Signature placeholder [Your Name]"""

    response = llm.invoke(prompt)
    email_content = response.content

    # Step 2: Classify sensitivity
    classify_prompt = f"""Classify this email's sensitivity level.

EMAIL:
{email_content}

CONTEXT: {context}

Rules:
- LOW: routine updates, meeting confirmations, general info
- MEDIUM: project concerns, schedule changes, budget discussions
- HIGH: contract disputes, legal issues, payments over $50,000, complaints

Respond with ONLY one word: LOW, MEDIUM, or HIGH"""

    sensitivity_response = llm.invoke(classify_prompt)
    sensitivity = sensitivity_response.content.strip().upper()

    # Ensure valid sensitivity level
    if sensitivity not in ["LOW", "MEDIUM", "HIGH"]:
        sensitivity = "MEDIUM"

    return {
        "email": email_content,
        "sensitivity": sensitivity,
        "recipient": recipient,
        "requires_approval": sensitivity in ["MEDIUM", "HIGH"]
    }