import React, { useState, useEffect } from "react";
import axios from "axios";

const API = "http://localhost:5000/api";

export default function ActivityLog() {
  const [log, setLog] = useState([]);
  const [audit, setAudit] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    Promise.all([
      axios.get(`${API}/activity`).then((r) => setLog(r.data.log)).catch(() => {}),
      axios.get(`${API}/audit`).then((r) => setAudit(r.data.audit || [])).catch(() => {}),
    ]).finally(() => setLoading(false));
  };
  useEffect(() => { load(); const t = setInterval(load, 15000); return () => clearInterval(t); }, []);

  const scorePill = (k, v) => (
    <span key={k} className={`ks-pill ${v >= 8 ? "ok" : v >= 5 ? "warn" : "crit"}`}>{k}: {v}/10</span>
  );

  if (loading) return <div className="ks-empty">Loading activity...</div>;

  return (
    <div>
      <div className="ks-eyebrow">Audit Trail</div>
      <h2 className="ks-h2" style={{ margin: "8px 0 20px" }}>Ledger &amp; Activity</h2>

      <div className="ks-grid-2">
        <div>
          <div className="ks-eyebrow" style={{ marginBottom: 12 }}>Ledger writes ({audit.length})</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {audit.length ? audit.map((a, i) => (
              <div key={i} className="ks-card" style={{ padding: 14 }}>
                <div className="ks-row">
                  <span style={{ color: "var(--gold)", fontSize: ".9rem" }}>{a.action}</span>
                  <span className="ks-muted" style={{ fontSize: ".75rem" }}>{a.ts}</span>
                </div>
                <div className="ks-muted" style={{ fontSize: ".82rem", marginTop: 6, wordBreak: "break-word" }}>{a.detail}</div>
              </div>
            )) : <span className="ks-muted" style={{ fontSize: ".9rem" }}>No ledger writes yet.</span>}
          </div>
        </div>

        <div>
          <div className="ks-eyebrow" style={{ marginBottom: 12 }}>Agent activity ({log.length})</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {log.length ? log.map((e, i) => (
              <div key={i} className="ks-card" style={{ padding: 14 }}>
                <div style={{ fontSize: ".92rem" }}>{e.request}</div>
                <div className="ks-muted" style={{ fontSize: ".78rem", marginTop: 4 }}>
                  {e.task_type || "task"} · {e.project || "N/A"} · {e.status}
                </div>
                {e.scores && Object.values(e.scores).some((v) => v > 0) && (
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }}>
                    {Object.entries(e.scores).filter(([, v]) => v > 0).map(([k, v]) => scorePill(k, v))}
                  </div>
                )}
              </div>
            )) : <span className="ks-muted" style={{ fontSize: ".9rem" }}>No activity yet.</span>}
          </div>
        </div>
      </div>
    </div>
  );
}
