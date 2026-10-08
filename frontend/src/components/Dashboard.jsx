import React, { useState, useEffect } from "react";
import axios from "axios";

const API = "http://localhost:5000/api";

const money = (n) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 })
    .format(n || 0);

function RoiBar() {
  const [roi, setRoi] = useState(null);
  useEffect(() => {
    const load = () => axios.get(`${API}/roi`).then((r) => setRoi(r.data)).catch(() => {});
    load();
    const t = setInterval(load, 8000);
    return () => clearInterval(t);
  }, []);
  if (!roi) return null;
  return (
    <div className="ks-roi">
      <div className="cell"><div className="v">{roi.hours_saved}</div><div className="l">Hours reclaimed</div></div>
      <div className="cell"><div className="v">{money(roi.dollars_flagged)}</div><div className="l">Flagged before overrun</div></div>
      <div className="cell"><div className="v">{roi.actions}</div><div className="l">Automated actions</div></div>
    </div>
  );
}

const flagPill = (flag) => {
  const map = { RED: ["crit", "Critical"], YELLOW: ["warn", "At Risk"], GREEN: ["ok", "On Track"] };
  const [cls, label] = map[flag] || ["", "Unknown"];
  return <span className={`ks-pill ${cls}`}>{label}</span>;
};

export default function Dashboard() {
  const [projects, setProjects] = useState([]);
  const [sel, setSel] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadDash = () =>
    axios.get(`${API}/dashboard`).then((r) => { setProjects(r.data.projects); setLoading(false); })
      .catch(() => setLoading(false));

  useEffect(() => { loadDash(); }, []);

  const openDetail = (id) => {
    setSel(id);
    axios.get(`${API}/project/${id}`).then((r) => setDetail(r.data)).catch(() => {});
  };

  if (loading) return <div className="ks-empty">Loading command center...</div>;

  return (
    <div>
      <RoiBar />
      <div className="ks-grid-3">
        {projects.map((p) => {
          const pctUsed = Math.min((p.budget_spent / p.budget_total) * 100, 100);
          const over = p.budget_spent > p.budget_total;
          return (
            <div key={p.id} className={`ks-card clickable ${sel === p.id ? "sel" : ""}`} onClick={() => openDetail(p.id)}>
              <div className="ks-row" style={{ marginBottom: 16 }}>
                <span className="ks-h2" style={{ fontSize: "1.2rem" }}>{p.name}</span>
                {flagPill(p.flag)}
              </div>
              <div className="ks-row" style={{ marginBottom: 8 }}>
                <span className="ks-muted" style={{ fontSize: ".85rem" }}>Budget</span>
                <span style={{ fontSize: ".9rem" }}>{money(p.budget_spent)} / {money(p.budget_total)}</span>
              </div>
              <div className="ks-track"><div className={`ks-fill ${over ? "over" : ""}`} style={{ width: `${pctUsed}%` }} /></div>
              <div className="ks-row" style={{ marginTop: 14 }}>
                <span className="ks-muted" style={{ fontSize: ".85rem" }}>Delay</span>
                <span style={{ color: p.delay_days > 0 ? "var(--crit)" : "var(--ok)", fontSize: ".9rem" }}>{p.delay_days} days</span>
              </div>
            </div>
          );
        })}
      </div>

      {detail && (
        <div className="ks-card" style={{ marginTop: 24 }}>
          <div className="ks-eyebrow">Detail View</div>
          <h2 className="ks-h2" style={{ margin: "8px 0 22px" }}>{detail.project.name}</h2>

          <div className="ks-grid-3" style={{ marginBottom: 24 }}>
            <div className="ks-card"><div className="ks-muted" style={{ fontSize: ".75rem" }}>Total Budget</div><div className="ks-num" style={{ fontSize: "1.6rem" }}>{money(detail.budget.total)}</div></div>
            <div className="ks-card"><div className="ks-muted" style={{ fontSize: ".75rem" }}>Spent to Date</div><div className="ks-num" style={{ fontSize: "1.6rem" }}>{money(detail.budget.spent)}</div></div>
            <div className="ks-card"><div className="ks-muted" style={{ fontSize: ".75rem" }}>Remaining</div><div className="ks-num" style={{ fontSize: "1.6rem", color: detail.budget.over_budget ? "var(--crit)" : "var(--teal)" }}>{money(detail.budget.remaining)}</div></div>
          </div>

          <div className="ks-grid-2">
            <div>
              <div className="ks-eyebrow" style={{ marginBottom: 10 }}>Schedule</div>
              <div className="ks-row"><span className="ks-muted">Overall delay</span><span style={{ color: detail.schedule.overall_delay_days > 0 ? "var(--crit)" : "var(--ok)" }}>{detail.schedule.overall_delay_days} days</span></div>
              <div className="ks-row" style={{ marginTop: 8 }}><span className="ks-muted">Projected end</span><span>{detail.schedule.projected_end_date || "N/A"}</span></div>
              {detail.schedule.delayed_phases?.length > 0 && (
                <div style={{ marginTop: 14 }}>
                  {detail.schedule.delayed_phases.map((ph, i) => (
                    <div key={i} className="ks-card" style={{ padding: 12, marginBottom: 8 }}>
                      <span style={{ color: "var(--crit)" }}>{ph.phase}</span>
                      <span className="ks-muted" style={{ fontSize: ".85rem" }}> — {ph.delay_days}d — {ph.delay_reason}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div>
              <div className="ks-eyebrow" style={{ marginBottom: 10 }}>Pending Invoices</div>
              {detail.budget.pending_invoices?.length ? detail.budget.pending_invoices.map((inv, i) => (
                <div key={i} className="ks-row ks-card" style={{ padding: 12, marginBottom: 8 }}>
                  <span className="ks-muted" style={{ fontSize: ".9rem" }}>{inv.id} — {inv.contractor}</span>
                  <span className="ks-num" style={{ fontSize: "1rem" }}>{money(inv.amount)}</span>
                </div>
              )) : <span className="ks-muted" style={{ fontSize: ".9rem" }}>None pending.</span>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
