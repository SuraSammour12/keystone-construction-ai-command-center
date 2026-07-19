import React, { useState, useEffect } from "react";
import axios from "axios";

const API = "http://localhost:5000/api";

function Dashboard() {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [projectDetail, setProjectDetail] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    try {
      const res = await axios.get(`${API}/dashboard`);
      setProjects(res.data.projects);
      setLoading(false);
    } catch (err) {
      console.error("Dashboard error:", err);
      setLoading(false);
    }
  };

  const fetchProjectDetail = async (projectId) => {
    setSelectedProject(projectId);
    try {
      const res = await axios.get(`${API}/project/${projectId}`);
      setProjectDetail(res.data);
    } catch (err) {
      console.error("Project detail error:", err);
    }
  };

  const getFlagStyle = (flag) => {
    switch (flag) {
      case "RED":
        return "border-red-300 bg-red-50";
      case "YELLOW":
        return "border-amber-300 bg-amber-50";
      case "GREEN":
        return "border-emerald-300 bg-emerald-50";
      default:
        return "border-gray-300 bg-gray-50";
    }
  };

  const getFlagDot = (flag) => {
    switch (flag) {
      case "RED": return "bg-red-500";
      case "YELLOW": return "bg-amber-500";
      case "GREEN": return "bg-emerald-500";
      default: return "bg-gray-400";
    }
  };

  const getFlagLabel = (flag) => {
    switch (flag) {
      case "RED": return "Critical";
      case "YELLOW": return "At Risk";
      case "GREEN": return "On Track";
      default: return "Unknown";
    }
  };

  const formatMoney = (amount) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(amount);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500 text-lg">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {projects.map((proj) => (
          <div
            key={proj.id}
            onClick={() => fetchProjectDetail(proj.id)}
            className={`border-2 rounded-xl p-5 cursor-pointer transition-all hover:shadow-lg ${getFlagStyle(proj.flag)} ${
              selectedProject === proj.id ? "ring-2 ring-amber-500 shadow-md" : ""
            }`}
          >
            <div className="flex items-center justify-between mb-4">
              <span className="text-lg font-bold text-gray-900">{proj.name}</span>
              <div className="flex items-center gap-2">
                <span className={`w-3 h-3 rounded-full ${getFlagDot(proj.flag)}`}></span>
                <span className="text-xs font-medium text-gray-600">{getFlagLabel(proj.flag)}</span>
              </div>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Budget</span>
                <span className="font-semibold text-gray-800">
                  {formatMoney(proj.budget_spent)} / {formatMoney(proj.budget_total)}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all ${
                    proj.budget_spent > proj.budget_total ? "bg-red-500" : "bg-emerald-500"
                  }`}
                  style={{
                    width: `${Math.min((proj.budget_spent / proj.budget_total) * 100, 100)}%`,
                  }}
                ></div>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Delay</span>
                <span className={`font-semibold ${proj.delay_days > 0 ? "text-red-600" : "text-emerald-600"}`}>
                  {proj.delay_days} days
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Status</span>
                <span className="font-medium text-gray-700">{proj.status}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Project Detail Panel */}
      {projectDetail && (
        <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-6 shadow-sm">
          <h2 className="text-xl font-bold text-gray-900">
            {projectDetail.project.name} - Detail View
          </h2>

          {/* Budget Section */}
          <div>
            <h3 className="text-md font-semibold text-amber-700 mb-3">
              Budget Breakdown
            </h3>
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center">
                <p className="text-xs text-gray-500 mb-1">Total Budget</p>
                <p className="text-lg font-bold text-gray-900">{formatMoney(projectDetail.budget.total)}</p>
              </div>
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center">
                <p className="text-xs text-gray-500 mb-1">Spent to Date</p>
                <p className="text-lg font-bold text-gray-900">{formatMoney(projectDetail.budget.spent)}</p>
              </div>
              <div className={`border rounded-lg p-4 text-center ${projectDetail.budget.over_budget ? "bg-red-50 border-red-200" : "bg-emerald-50 border-emerald-200"}`}>
                <p className="text-xs text-gray-500 mb-1">Remaining</p>
                <p className={`text-lg font-bold ${projectDetail.budget.over_budget ? "text-red-600" : "text-emerald-600"}`}>
                  {formatMoney(projectDetail.budget.remaining)}
                </p>
              </div>
            </div>
          </div>

          {/* Schedule Section */}
          <div>
            <h3 className="text-md font-semibold text-amber-700 mb-3">
              Schedule
            </h3>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <p className="text-xs text-gray-500 mb-1">Overall Delay</p>
                <p className={`text-lg font-bold ${projectDetail.schedule.overall_delay_days > 0 ? "text-red-600" : "text-emerald-600"}`}>
                  {projectDetail.schedule.overall_delay_days} days
                </p>
              </div>
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <p className="text-xs text-gray-500 mb-1">Projected End</p>
                <p className="text-lg font-bold text-gray-900">{projectDetail.schedule.projected_end_date}</p>
              </div>
            </div>

            {projectDetail.schedule.delayed_phases.length > 0 && (
              <div className="mt-3">
                <p className="text-sm text-gray-500 mb-2">Delayed Phases</p>
                {projectDetail.schedule.delayed_phases.map((phase, i) => (
                  <div
                    key={i}
                    className="bg-red-50 border border-red-200 rounded-lg p-3 mb-2 text-sm"
                  >
                    <span className="font-semibold text-red-700">{phase.phase}</span>
                    <span className="text-gray-600">
                      {" "} - {phase.delay_days} days - {phase.delay_reason}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Pending Invoices */}
          {projectDetail.budget.pending_invoices.length > 0 && (
            <div>
              <h3 className="text-md font-semibold text-amber-700 mb-3">
                Pending Invoices
              </h3>
              {projectDetail.budget.pending_invoices.map((inv, i) => (
                <div
                  key={i}
                  className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-2 text-sm flex justify-between items-center"
                >
                  <span className="text-gray-700">
                    {inv.id} - {inv.contractor}
                  </span>
                  <span className="font-bold text-gray-900">{formatMoney(inv.amount)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default Dashboard;