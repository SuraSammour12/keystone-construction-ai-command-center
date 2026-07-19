import json
import os

# Base path to the data directory
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def load_json(filename: str) -> dict:
    """Load a JSON file from the data directory"""
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# ========================
# Projects
# ========================

def get_all_projects() -> list:
    """Return all projects"""
    data = load_json("projects.json")
    return data["projects"]


def get_project_by_id(project_id: str) -> dict | None:
    """Find a single project by its ID"""
    projects = get_all_projects()
    for project in projects:
        if project["id"] == project_id:
            return project
    return None


def get_project_by_name(name: str) -> dict | None:
    """Find a single project by name (partial match, case-insensitive)"""
    projects = get_all_projects()
    for project in projects:
        if name.lower() in project["name"].lower():
            return project
    return None


# ========================
# Budgets
# ========================

def get_budget_by_project(project_id: str) -> dict | None:
    """Return budget data for a specific project"""
    data = load_json("budgets.json")
    for budget in data["budgets"]:
        if budget["project_id"] == project_id:
            return budget
    return None


def get_all_budgets() -> list:
    """Return all budget records"""
    data = load_json("budgets.json")
    return data["budgets"]


def get_pending_invoices(project_id: str) -> list:
    """Return only pending (unapproved) invoices for a project"""
    budget = get_budget_by_project(project_id)
    if not budget:
        return []
    return [inv for inv in budget["invoices_pending"] if inv["status"] == "Pending Approval"]


# ========================
# Schedules
# ========================

def get_schedule_by_project(project_id: str) -> dict | None:
    """Return schedule data for a specific project"""
    data = load_json("schedules.json")
    for schedule in data["schedules"]:
        if schedule["project_id"] == project_id:
            return schedule
    return None


def get_all_schedules() -> list:
    """Return all schedule records"""
    data = load_json("schedules.json")
    return data["schedules"]


def get_delayed_phases(project_id: str) -> list:
    """Return only the delayed phases for a project"""
    schedule = get_schedule_by_project(project_id)
    if not schedule:
        return []
    return [phase for phase in schedule["phases"] if phase["delay_days"] > 0]


# ========================
# Contractors
# ========================

def get_all_contractors() -> list:
    """Return all contractors"""
    data = load_json("contractors.json")
    return data["contractors"]


def get_contractor_by_id(contractor_id: str) -> dict | None:
    """Find a single contractor by ID"""
    contractors = get_all_contractors()
    for contractor in contractors:
        if contractor["id"] == contractor_id:
            return contractor
    return None


def get_contractors_by_project(project_id: str) -> list:
    """Return all contractors assigned to a specific project"""
    contractors = get_all_contractors()
    return [c for c in contractors if project_id in c["project_ids"]]


# ========================
# Summary Helpers
# ========================

def get_project_summary(project_id: str) -> dict | None:
    """Build a complete summary combining project, budget, and schedule data"""
    project = get_project_by_id(project_id)
    if not project:
        return None

    budget = get_budget_by_project(project_id)
    schedule = get_schedule_by_project(project_id)
    contractors = get_contractors_by_project(project_id)

    summary = {
        "project": project,
        "budget": {
            "total": budget["total_budget"] if budget else None,
            "spent": budget["spent_to_date"] if budget else None,
            "remaining": budget["remaining"] if budget else None,
            "over_budget": budget["spent_to_date"] > budget["total_budget"] if budget else False,
            "over_budget_pct": round(((budget["spent_to_date"] - budget["total_budget"]) / budget["total_budget"]) * 100, 1) if budget and budget["spent_to_date"] > budget["total_budget"] else 0,
            "pending_invoices": get_pending_invoices(project_id)
        },
        "schedule": {
            "overall_delay_days": schedule["overall_delay_days"] if schedule else 0,
            "projected_end_date": schedule["projected_end_date"] if schedule else None,
            "delayed_phases": get_delayed_phases(project_id),
            "critical_path": schedule["critical_path_items"] if schedule else []
        },
        "contractors": contractors
    }

    return summary


def get_all_projects_overview() -> list:
    """Build a quick overview of all projects with key metrics"""
    projects = get_all_projects()
    overview = []

    for project in projects:
        pid = project["id"]
        budget = get_budget_by_project(pid)
        schedule = get_schedule_by_project(pid)

        status_flag = "GREEN"
        if budget and budget["spent_to_date"] > budget["total_budget"]:
            status_flag = "RED"
        elif schedule and schedule["overall_delay_days"] > 14:
            status_flag = "YELLOW"

        overview.append({
            "id": pid,
            "name": project["name"],
            "status": project["status"],
            "flag": status_flag,
            "budget_total": budget["total_budget"] if budget else 0,
            "budget_spent": budget["spent_to_date"] if budget else 0,
            "delay_days": schedule["overall_delay_days"] if schedule else 0
        })

    return overview