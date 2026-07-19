import React, { useState, useEffect } from "react";
import axios from "axios";

const API = "http://localhost:5000/api";

function ApprovalQueue() {
  const [approvals, setApprovals] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchApprovals();
  }, []);

  const fetchApprovals = async () => {
    try {
      const res = await axios.get(`${API}/approvals`);
      setApprovals(res.data.approvals);
      setLoading(false);
    } catch (err) {
      console.error("Approvals error:", err);
      setLoading(false);
    }
  };

  const handleApproval = async (id, action) => {
    try {
      await axios.post(`${API}/approvals/${id}`, { action });
      fetchApprovals();
    } catch (err) {
      console.error("Approval action error:", err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading approvals...</div>
      </div>
    );
  }

  if (approvals.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-12 text-center shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          No Pending Approvals
        </h3>
        <p className="text-gray-500 text-sm">
          When an agent needs human approval for emails or budget transfers, items will appear here.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">
          Pending Approvals ({approvals.length})
        </h2>
        <button
          onClick={fetchApprovals}
          className="text-sm text-amber-600 hover:text-amber-700 font-medium"
        >
          Refresh
        </button>
      </div>

      {approvals.map((item) => (
        <div
          key={item.id}
          className="bg-white border border-amber-200 rounded-xl p-5 space-y-4 shadow-sm"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div>
                <span className="font-semibold text-gray-900">
                  {item.type === "email" ? "Email Draft" : "Budget Transfer"}
                </span>
                <span className="text-gray-500 text-sm ml-2">
                  #{item.id} - {item.project}
                </span>
              </div>
            </div>
            <span className="text-xs bg-amber-100 text-amber-700 px-3 py-1 rounded-full font-medium">
              Pending Review
            </span>
          </div>

          <pre className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm text-gray-700 whitespace-pre-wrap overflow-x-auto max-h-64 overflow-y-auto">
            {item.details}
          </pre>

          <div className="flex gap-3 justify-end">
            <button
              onClick={() => handleApproval(item.id, "reject")}
              className="px-5 py-2 rounded-lg text-sm font-medium bg-white text-red-600 border border-red-300 hover:bg-red-50 transition-colors"
            >
              Reject
            </button>
            <button
              onClick={() => handleApproval(item.id, "approve")}
              className="px-5 py-2 rounded-lg text-sm font-medium bg-emerald-600 text-white hover:bg-emerald-700 transition-colors"
            >
              Approve
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

export default ApprovalQueue;