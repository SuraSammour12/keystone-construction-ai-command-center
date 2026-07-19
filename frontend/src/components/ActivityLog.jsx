import React, { useState, useEffect } from "react";
import axios from "axios";

const API = "http://localhost:5000/api";

function ActivityLog() {
  const [log, setLog] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLog();
  }, []);

  const fetchLog = async () => {
    try {
      const res = await axios.get(`${API}/activity`);
      setLog(res.data.log);
      setLoading(false);
    } catch (err) {
      console.error("Activity log error:", err);
      setLoading(false);
    }
  };

  const getTaskLabel = (type) => {
    switch (type) {
      case "report": return "Report";
      case "email": return "Email";
      case "transfer": return "Transfer";
      case "status": return "Overview";
      case "approval": return "Approval";
      default: return "Task";
    }
  };

  const getTaskStyle = (type) => {
    switch (type) {
      case "report": return "bg-blue-100 text-blue-700";
      case "email": return "bg-purple-100 text-purple-700";
      case "transfer": return "bg-amber-100 text-amber-700";
      case "approval": return "bg-emerald-100 text-emerald-700";
      default: return "bg-gray-100 text-gray-700";
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading activity log...</div>
      </div>
    );
  }

  if (log.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-12 text-center shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">No Activity Yet</h3>
        <p className="text-gray-500 text-sm">
          Agent activities will be logged here as you use the chat.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">
          Activity Log ({log.length} entries)
        </h2>
        <button
          onClick={fetchLog}
          className="text-sm text-amber-600 hover:text-amber-700 font-medium"
        >
          Refresh
        </button>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl divide-y divide-gray-100 shadow-sm">
        {log.map((entry, i) => (
          <div key={i} className="p-4 flex items-start gap-4">
            <span className={`text-xs font-medium px-2 py-1 rounded-full mt-1 ${getTaskStyle(entry.task_type)}`}>
              {getTaskLabel(entry.task_type)}
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-900 font-medium truncate">
                {entry.request}
              </p>
              <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
                <span>Project: {entry.project || "N/A"}</span>
                {entry.attempts > 0 && (
                  <span>Attempts: {entry.attempts}</span>
                )}
              </div>
              {entry.scores && Object.values(entry.scores).some((v) => v > 0) && (
                <div className="flex gap-2 mt-2 flex-wrap">
                  {Object.entries(entry.scores)
                    .filter(([_, v]) => v > 0)
                    .map(([key, val]) => (
                      <span
                        key={key}
                        className={`text-xs px-2 py-1 rounded-full font-medium ${
                          val >= 8
                            ? "bg-emerald-100 text-emerald-700"
                            : val >= 5
                            ? "bg-amber-100 text-amber-700"
                            : "bg-red-100 text-red-700"
                        }`}
                      >
                        {key}: {val}/10
                      </span>
                    ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ActivityLog;