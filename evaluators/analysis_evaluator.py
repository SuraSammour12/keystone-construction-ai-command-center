from langchain_groq import ChatGroq

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

def evaluate_analysis(analysis_text: str, analysis_type: str) -> dict:
    """Evaluate the quality of a budget, schedule, or risk analysis"""

    prompt = f"""You are a quality reviewer for construction project analyses.
Evaluate this {analysis_type} analysis strictly.

ANALYSIS TO EVALUATE:
{analysis_text}

Score each criterion from 0-2:
1. DATA USAGE - Does it reference specific numbers, dates, percentages? (0=none, 1=some, 2=thorough)
2. ROOT CAUSE - Does it explain WHY problems exist, not just WHAT? (0=no, 1=partial, 2=yes)
3. SPECIFICITY - Are recommendations specific and actionable? (0=generic, 1=somewhat, 2=very specific)
4. COMPLETENESS - Does it cover all important aspects? (0=major gaps, 1=minor gaps, 2=complete)
5. PROFESSIONALISM - Is the tone and structure professional? (0=poor, 1=ok, 2=excellent)

Respond in this EXACT format:
DATA_USAGE: [0-2]
ROOT_CAUSE: [0-2]
SPECIFICITY: [0-2]
COMPLETENESS: [0-2]
PROFESSIONALISM: [0-2]
TOTAL: [sum out of 10]
FEEDBACK: [2-3 sentences on what to improve]"""

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
        "passed": total >= 7,
        "feedback": feedback,
        "raw_evaluation": content
    }