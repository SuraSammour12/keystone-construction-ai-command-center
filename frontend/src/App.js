import React, { useState, useEffect } from "react";
import Dashboard from "./components/Dashboard";
import ChatInterface from "./components/ChatInterface";
import Invoices from "./components/Invoices";
import ApprovalQueue from "./components/ApprovalQueue";
import ActivityLog from "./components/ActivityLog";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "chat", label: "Chat" },
  { id: "invoices", label: "Invoices" },
  { id: "approvals", label: "Approvals" },
  { id: "activity", label: "Activity" },
];

const SUN = (
  <path d="M12 3v2M12 19v2M5 5l1.4 1.4M17.6 17.6 19 19M3 12h2M19 12h2M5 19l1.4-1.4M17.6 6.4 19 5M12 8a4 4 0 100 8 4 4 0 000-8z"
    fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
);
const MOON = (
  <path d="M20 14.5A8 8 0 119.5 4 6.3 6.3 0 0020 14.5z"
    fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
);

function App() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [theme, setTheme] = useState("dark");

  useEffect(() => {
    let saved = "dark";
    try { saved = localStorage.getItem("ks-theme") || "dark"; } catch (e) {}
    setTheme(saved);
    document.documentElement.setAttribute("data-theme", saved);
  }, []);

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    try { localStorage.setItem("ks-theme", next); } catch (e) {}
  };

  return (
    <div className="ks-app">
      <header className="ks-header">
        <div className="ks-header-in">
          <a className="ks-brand" href="/keystone.html" data-tip="Return to landing" title="Return to the landing page">
            <img src="/logo.png" alt="Keystone" />
            <div>
              <div className="word">KEYSTONE</div>
              <div className="sub">Construction Command Center</div>
            </div>
          </a>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <span className="ks-status"><span className="ks-dot" /> System Online</span>
            <button className="ks-toggle" onClick={toggleTheme} aria-label="Toggle day and night">
              <svg viewBox="0 0 24 24">{theme === "dark" ? SUN : MOON}</svg>
            </button>
          </div>
        </div>
        <nav className="ks-tabs">
          {TABS.map((t) => (
            <button key={t.id} className={`ks-tab ${activeTab === t.id ? "active" : ""}`}
              onClick={() => setActiveTab(t.id)}>{t.label}</button>
          ))}
        </nav>
      </header>

      <main className="ks-main">
        {activeTab === "dashboard" && <Dashboard />}
        {activeTab === "chat" && <ChatInterface />}
        {activeTab === "invoices" && <Invoices />}
        {activeTab === "approvals" && <ApprovalQueue />}
        {activeTab === "activity" && <ActivityLog />}
      </main>
    </div>
  );
}

export default App;
