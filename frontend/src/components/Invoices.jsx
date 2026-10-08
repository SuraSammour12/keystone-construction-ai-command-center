import React, { useEffect, useState } from "react";
import axios from "axios";

const API = "http://localhost:5000/api";
const money = (n) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n || 0);

const statusPill = (s) => {
  const map = { "Pending Approval": ["warn", "Pending"], Approved: ["ok", "Approved"], Rejected: ["crit", "Rejected"] };
  const [cls, label] = map[s] || ["", s];
  return <span className={`ks-pill ${cls}`}>{label}</span>;
};

export default function Invoices() {
  const [invoices, setInvoices] = useState([]);
  const [recon, setRecon] = useState(null);
  const [sel, setSel] = useState(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(null); // { kind: "ok" | "warn", text }

  const load = () => axios.get(`${API}/invoices`).then((r) => setInvoices(r.data.invoices)).catch(() => {});
  useEffect(() => { load(); }, []);

  const inspect = (id) => {
    setSel(id); setRecon(null); setNotice(null);
    axios.get(`${API}/invoices/${id}/reconcile`).then((r) => setRecon(r.data)).catch(() => {});
  };

  const resolve = async (id, decision) => {
    const reason = decision === "rejected" ? (window.prompt("Reason (optional):") || "") : "";
    setBusy(true); setNotice(null);
    try {
      const { data } = await axios.post(`${API}/invoices/${id}/resolve`, { decision, reason });
      const verb = data.status === "approved" ? "approved and posted" : "rejected";
      setNotice({ kind: "ok", text: `Invoice ${id} ${verb}. Recorded in the ledger and audit trail.` });
      await load();
      inspect(id);
    } catch (e) {
      const status = e?.response?.status;
      if (status === 409) {
        setNotice({ kind: "warn", text: `Invoice ${id} was already actioned, so no change was made.` });
        await load();
      } else {
        const detail = e?.response?.data?.error || e.message;
        setNotice({ kind: "warn", text: `Could not complete the action: ${detail}` });
      }
    } finally { setBusy(false); }
  };

  const selInv = invoices.find((i) => i.id === sel);
  const isPending = selInv ? selInv.status === "Pending Approval" : true;

  return (
    <div>
      <div className="ks-eyebrow">Invoice Automation</div>
      <h2 className="ks-h2" style={{ margin: "8px 0 20px" }}>Read, reconcile, and post invoices</h2>

      <div className="ks-grid-2">
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {invoices.map((inv) => (
            <div key={inv.id} className={`ks-card clickable ${sel === inv.id ? "sel" : ""}`} onClick={() => inspect(inv.id)}>
              <div className="ks-row">
                <span style={{ fontSize: ".95rem" }}>{inv.id} — {inv.contractor}</span>
                {statusPill(inv.status)}
              </div>
              <div className="ks-row" style={{ marginTop: 8 }}>
                <span className="ks-muted" style={{ fontSize: ".85rem" }}>{inv.project_id}</span>
                <span className="ks-num" style={{ fontSize: "1.1rem" }}>{money(inv.amount)}</span>
              </div>
            </div>
          ))}
          {!invoices.length && <div className="ks-empty">No invoices.</div>}
        </div>

        <div>
          {!recon && <div className="ks-empty">Select an invoice to reconcile it against its purchase order and budget.</div>}
          {recon && !recon.error && (
            <div className="ks-card">
              <div className="ks-eyebrow">Reconciliation — {recon.invoice_id}</div>
              <div style={{ margin: "16px 0", display: "flex", flexDirection: "column", gap: 8 }}>
                <div className="ks-row"><span className="ks-muted">Invoice amount</span><span className="ks-num" style={{ fontSize: "1rem" }}>{money(recon.invoice_amount)}</span></div>
                <div className="ks-row"><span className="ks-muted">Purchase order</span><span>{recon.po_id ? `${recon.po_id} — ${money(recon.po_amount)}` : "none"}</span></div>
                {recon.variance != null && (
                  <div className="ks-row"><span className="ks-muted">Variance</span>
                    <span style={{ color: recon.variance > 0 ? "var(--crit)" : "var(--ok)" }}>{money(recon.variance)} ({recon.variance_pct}%)</span></div>
                )}
                <div className="ks-row"><span className="ks-muted">Remaining after post</span>
                  <span style={{ color: recon.remaining_after < 0 ? "var(--crit)" : "var(--teal)" }}>{money(recon.remaining_after)}</span></div>
              </div>

              <div className="ks-flag-list">
                {recon.reconciled
                  ? <div className="ks-flag clean">Reconciles cleanly. Recommendation: Post.</div>
                  : recon.flags.map((f, i) => <div key={i} className="ks-flag">{f}</div>)}
              </div>

              {selInv && (
                <div className="ks-row" style={{ marginTop: 16 }}>
                  <span className="ks-muted" style={{ fontSize: ".85rem" }}>Current status</span>
                  {statusPill(selInv.status)}
                </div>
              )}

              {isPending ? (
                <div style={{ display: "flex", gap: 10, marginTop: 20 }}>
                  <button className="ks-btn solid" disabled={busy} onClick={() => resolve(recon.invoice_id, "approved")}>Approve &amp; Post</button>
                  <button className="ks-btn danger" disabled={busy} onClick={() => resolve(recon.invoice_id, "rejected")}>Reject</button>
                </div>
              ) : (
                <div className="ks-muted" style={{ marginTop: 20, fontSize: ".85rem" }}>
                  This invoice has been resolved. Run init_db.py to reset the demo data.
                </div>
              )}

              {notice && (
                <div className={`ks-flag ${notice.kind === "ok" ? "clean" : ""}`} style={{ marginTop: 16 }}>
                  {notice.text}
                </div>
              )}
            </div>
          )}
          {recon && recon.error && <div className="ks-empty">{recon.error}</div>}
        </div>
      </div>
    </div>
  );
}
