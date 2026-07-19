def calculate_budget_variance(budgeted: float, actual: float) -> dict:
    """Calculate the difference between budgeted and actual amounts"""
    variance = actual - budgeted
    variance_pct = round((variance / budgeted) * 100, 1) if budgeted != 0 else 0

    return {
        "budgeted": budgeted,
        "actual": actual,
        "variance": variance,
        "variance_pct": variance_pct,
        "status": "Over Budget" if variance > 0 else "Under Budget" if variance < 0 else "On Budget"
    }


def calculate_schedule_risk(delay_days: int) -> str:
    """Classify schedule risk based on delay duration"""
    if delay_days == 0:
        return "On Track"
    elif delay_days <= 14:
        return "Low Risk"
    elif delay_days <= 30:
        return "Medium Risk"
    else:
        return "High Risk"


def calculate_project_health(over_budget_pct: float, delay_days: int) -> str:
    """Overall project health score based on budget and schedule"""
    if over_budget_pct > 10 or delay_days > 30:
        return "CRITICAL"
    elif over_budget_pct > 5 or delay_days > 14:
        return "AT RISK"
    elif over_budget_pct > 0 or delay_days > 0:
        return "WATCH"
    else:
        return "HEALTHY"