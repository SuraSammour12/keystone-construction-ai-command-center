from flask import Blueprint, request, jsonify
from workflows.main_graph import run_command_center
from tools.data_loader import (
    get_all_projects_overview,
    get_project_summary,
    get_all_projects,
    get_pending_invoices
)

api_blueprint = Blueprint("api", __name__)

# Store approval queue in memory (in production this would be a database)
approval_queue = []
activity_log = []


# ============================================================
# ROUTE 1: Chat — The main endpoint
# ============================================================

@api_blueprint.route("/chat", methods=["POST"])
def chat():
    """Main chat endpoint — receives user request, returns agent response"""
    data = request.get_json()
    user_message = data.get("message", "")
    project_id = data.get("project_id", "")
    project_name = data.get("project_name", "")

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    try:
        result = run_command_center(user_message, project_id, project_name)

        # Log the activity
        activity_log.append({
            "request": user_message,
            "task_type": result["task_type"],
            "project": result["project"],
            "scores": result["scores"],
            "attempts": result["attempts"]
        })

        # If approval is needed, add to queue
        if result["requires_approval"]:
            approval_item = {
                "id": len(approval_queue) + 1,
                "type": result["approval_type"],
                "project": result["project"],
                "details": result["response"],
                "status": "pending"
            }
            approval_queue.append(approval_item)
            result["approval_id"] = approval_item["id"]

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# ROUTE 2: Dashboard — All projects overview
# ============================================================

@api_blueprint.route("/dashboard", methods=["GET"])
def dashboard():
    """Return overview of all projects for the dashboard"""
    try:
        overview = get_all_projects_overview()
        return jsonify({"projects": overview})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# ROUTE 3: Project Detail
# ============================================================

@api_blueprint.route("/project/<project_id>", methods=["GET"])
def project_detail(project_id):
    """Return full details for a single project"""
    try:
        summary = get_project_summary(project_id)
        if not summary:
            return jsonify({"error": "Project not found"}), 404
        return jsonify(summary)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# ROUTE 4: Approval Queue
# ============================================================

@api_blueprint.route("/approvals", methods=["GET"])
def get_approvals():
    """Return all pending approvals"""
    pending = [a for a in approval_queue if a["status"] == "pending"]
    return jsonify({"approvals": pending, "total": len(pending)})


@api_blueprint.route("/approvals/<int:approval_id>", methods=["POST"])
def handle_approval(approval_id):
    """Approve or reject an item"""
    data = request.get_json()
    action = data.get("action", "")  # "approve" or "reject"

    if action not in ["approve", "reject"]:
        return jsonify({"error": "Action must be 'approve' or 'reject'"}), 400

    for item in approval_queue:
        if item["id"] == approval_id:
            item["status"] = "approved" if action == "approve" else "rejected"

            # Log the decision
            activity_log.append({
                "request": f"Approval #{approval_id}: {action}",
                "task_type": "approval",
                "project": item["project"],
                "scores": {},
                "attempts": 0
            })

            return jsonify({
                "message": f"Item #{approval_id} has been {item['status']}",
                "item": item
            })

    return jsonify({"error": "Approval not found"}), 404


# ============================================================
# ROUTE 5: Activity Log
# ============================================================

@api_blueprint.route("/activity", methods=["GET"])
def get_activity():
    """Return the activity log (most recent first)"""
    return jsonify({"log": list(reversed(activity_log)), "total": len(activity_log)})


# ============================================================
# ROUTE 6: Pending Invoices
# ============================================================

@api_blueprint.route("/invoices/<project_id>", methods=["GET"])
def get_invoices(project_id):
    """Return pending invoices for a project"""
    try:
        invoices = get_pending_invoices(project_id)
        return jsonify({"invoices": invoices, "total": len(invoices)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500