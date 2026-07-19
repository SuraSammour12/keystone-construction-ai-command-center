"""Quick test - run this first to make sure everything works before starting the API"""

from dotenv import load_dotenv
load_dotenv()  # Load OPENAI_API_KEY from .env file

from tools.data_loader import get_all_projects_overview, get_project_summary

print("=" * 50)
print("TEST 1: Data Loading")
print("=" * 50)

# Test data loading
overview = get_all_projects_overview()
for proj in overview:
    flag = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(proj["flag"], "⚪")
    print(f"{flag} {proj['name']} - Budget: ${proj['budget_spent']:,}/${proj['budget_total']:,} - Delay: {proj['delay_days']} days")

print("\n" + "=" * 50)
print("TEST 2: Project Summary")
print("=" * 50)

summary = get_project_summary("PRJ-001")
print(f"Project: {summary['project']['name']}")
print(f"Over budget: {summary['budget']['over_budget']} ({summary['budget']['over_budget_pct']}%)")
print(f"Delay: {summary['schedule']['overall_delay_days']} days")
print(f"Contractors: {len(summary['contractors'])}")

print("\n" + "=" * 50)
print("TEST 3: Full Agent Run")
print("=" * 50)

from workflows.main_graph import run_command_center

print("\nRunning: 'Give me a status report for Alpha Tower'")
print("This will call multiple AI agents - may take 30-60 seconds...\n")

result = run_command_center("Give me a status report for Alpha Tower")

print(f"Task Type: {result['task_type']}")
print(f"Project: {result['project']}")
print(f"Attempts: {result['attempts']}")
print(f"Scores: {result['scores']}")
print(f"\n{result['response']}")