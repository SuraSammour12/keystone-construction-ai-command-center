import React, { useEffect, useState } from "react";
import axios from "axios";

const API = "http://localhost:5000/api";
const money = (n) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n || 0);

export default function ApprovalQueue() {
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(null);

  const load = () => axios.get(`${API}/approvals`).then(({ data }) => setItems(data.approvals || [])).catch(() => {});
  useEffect(() => { load(); const t = setInterval(load, 3000); return () => clearInterval(t); }, []);

  async function resolve(threadId, action) {
    const reason = action === "reject" ? (window.prompt("Reason for rejection (optional):") || "") : "";
    setBusy(threadId);
    try { await axios.post(`${API}/approvals/${threadId}`, { action, reason }); await load(); }
    finally { setBusy(null); }
  }

  return (
    <div>
      <div className="ks-eyebrow">Human in the Loop</div>
      <h2 className="ks-h2" style={{ margin: "8px 0 20px" }}>Pending Approvals ({items.length})</h2>
      {items.length === 0 && <div className="ks-empty">Nothing waiting. Sensitive actions pause here for your decision.</div>}
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {items.map((item) => {
          const it = item.interrupt || {};
          const isEmail = it.kind === "email_approval";
          const t = it.proposal?.transfer || {};
          return (
            <div key={item.thread_id} className="ks-card">
              <div className="ks-row" style={{ marginBottom: 12 }}>
                <span className="ks-h2" style={{ fontSize: "1.1rem" }}>{isEmail ? "Email Draft" : "Budget Transfer"}</span>
                <span className="ks-pill">{it.project || "—"} · {item.thread_id.slice(0, 8)}…</span>
              </div>
              {isEmail ? (
                <>
                  <div className="ks-muted" style={{ fontSize: ".85rem", marginBottom: 10 }}>
                    Sensitivity: {it.sensitivity} · Quality: {it.quality_score}/10 · To: {it.recipient}
                  </div>
                  <div className="ks-code">{it.draft}</div>
                </>
              ) : (
                <>
                  <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 10 }}>
                    <div className="ks-row"><span className="ks-muted">From</span><span>{t.from_project}</span></div>
                    <div className="ks-row"><span className="ks-muted">To</span><span>{t.to_project}</span></div>
                    <div className="ks-row"><span className="ks-muted">Amount</span><span className="ks-num" style={{ fontSize: "1.1rem" }}>{money(t.amount)}</span></div>
                  </div>
                  <div className="ks-code">{it.proposal?.impact_analysis}</div>
                </>
              )}
              <div style={{ display: "flex", gap: 10, marginTop: 18 }}>
                <button className="ks-btn solid" disabled={busy === item.thread_id} onClick={() => resolve(item.thread_id, "approve")}>Approve</button>
                <button className="ks-btn danger" disabled={busy === item.thread_id} onClick={() => resolve(item.thread_id, "reject")}>Reject</button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
