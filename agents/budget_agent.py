"""
Budget analysis agent.

Anti-hallucination design (grounded generation + abstention + temp 0):
the numbers come only from the live system of record, and the model is told,
in strict terms, to use only those numbers and to say "not in records" for
anything missing. It never originates a figure.
"""
from contextlib import closing

from langchain_groq import ChatGroq

from tools import db, finance_core as fc

llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)

STRICT = (
    "STRICT DATA RULES (read carefully):\n"
    "- Use ONLY the figures, names and dates provided in the DATA section below.\n"
    "- Do NOT invent, estimate, extrapolate, or infer any number, percentage, name, "
    "or date that is not explicitly present in the DATA.\n"
    "- Every dollar amount and percentage you write MUST appear verbatim in the DATA.\n"
    "- If something is not in the DATA, write 'not in records' rather than guessing.\n"
    "- Do not propose specific invented dollar figures in recommendations; describe "
    "actions qualitatively or reference only the real figures above.\n\n"
)


def _fmt_lines(lines):
    out = []
    for x in lines:
        out.append(
            f"- {x['category']}: Budgeted ${x['budgeted']:,.0f} | Actual ${x['actual']:,.0f} "
            f"| {x['status']} ({x['variance_pct']}%) | Note: {x['note']}"
        )
    return "\n".join(out)


def _fmt_invoices(rows):
    if not rows:
        return "No pending invoices."
    return "\n".join(
        f"- {r['id']}: {r['contractor']} - ${r['amount']:,.0f} - Due: {r['due_date']}" for r in rows
    )


def run_budget_analysis(project_id: str, project_name: str, feedback: str = "") -> str:
    with closing(db.get_conn()) as conn:
        if not conn.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
            return f"No budget data in records for {project_id}."
        b = fc.project_budget(conn, project_id)
        lines = fc.category_variances(conn, project_id)
        pend = conn.execute(
            "SELECT id, contractor, amount, due_date FROM invoices "
            "WHERE project_id=? AND status='Pending Approval'", (project_id,)
        ).fetchall()

    status = "over budget" if b["over_budget"] else "within budget"
    feedback_section = ""
    if feedback:
        feedback_section = (
            f"\n\nREVISION REQUIRED. A previous version was rejected. Fix these issues "
            f"and remove any figure not in the DATA:\n{feedback}\n"
        )

    prompt = f"""{STRICT}You are a senior construction budget analyst.

DATA for {project_name} ({project_id}):
OVERALL:
- Total Budget: ${b['budget_total']:,.0f}
- Spent to Date: ${b['spent']:,.0f}
- Remaining: ${b['remaining']:,.0f}
- Status: {status} ({b['over_budget_pct']}% over)

CATEGORY BREAKDOWN:
{_fmt_lines(lines)}

PENDING INVOICES ({len(pend)} awaiting approval):
{_fmt_invoices(pend)}

Write a 3-4 paragraph budget analysis covering overall health, problem categories
and why (using only the notes and numbers above), pending-invoice concerns, and
recommendations. Use only the figures in the DATA.{feedback_section}"""

    return llm.invoke(prompt).content
