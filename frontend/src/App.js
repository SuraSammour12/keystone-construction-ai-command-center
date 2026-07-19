import React, { useState } from "react";
import Dashboard from "./components/Dashboard";
import ChatInterface from "./components/ChatInterface";
import ApprovalQueue from "./components/ApprovalQueue";
import ActivityLog from "./components/ActivityLog";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "chat", label: "Chat" },
  { id: "approvals", label: "Approvals" },
  { id: "activity", label: "Activity Log" },
];

function App() {
  const [activeTab, setActiveTab] = useState("dashboard");

  return (
    <div className="min-h-screen bg-gray-50 text-gray-800">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 shadow-sm">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 tracking-tight">
              Construction AI Command Center
            </h1>
            <p className="text-sm text-gray-500 mt-1">
              Powered by Multi-Agent Orchestration
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span>
            System Online
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto flex gap-1 px-6">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-5 py-3 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? "text-amber-700 border-b-2 border-amber-600"
                  : "text-gray-500 hover:text-gray-800"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto p-6">
        {activeTab === "dashboard" && <Dashboard />}
        {activeTab === "chat" && <ChatInterface />}
        {activeTab === "approvals" && <ApprovalQueue />}
        {activeTab === "activity" && <ActivityLog />}
      </main>
    </div>
  );
}

export default App;