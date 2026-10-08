import React, { useState, useRef, useEffect } from "react";
import axios from "axios";

const API = "http://localhost:5000/api";

// Render agent Markdown (headings, tables, bold) safely. The backend wraps
// reports in rows of "=", which we turn into rules so they render cleanly.
function renderMd(text) {
  try {
    if (window.marked && window.DOMPurify) {
      const pre = (text || "").replace(/^={3,}\s*$/gm, "---");
      return { __html: window.DOMPurify.sanitize(window.marked.parse(pre)) };
    }
  } catch (e) {}
  return null;
}

// Direct PDF download, built client-side with jsPDF (crisp text, real tables,
// no print dialog). Markdown headings, tables, bullets and paragraphs are
// parsed and laid out in a clean light theme.
// Normalize unicode the standard PDF font cannot render (non-breaking spaces,
// figure dashes, smart quotes) so no stray glyphs like "/" appear.
function clean(s) {
  return (s || "")
    .replace(/[‐‑‒–—―]/g, "-")
    .replace(/[      ⁠]/g, " ")
    .replace(/[‘’′]/g, "'")
    .replace(/[“”″]/g, '"')
    .replace(/…/g, "...");
}
function stripInline(s) {
  return clean(s).replace(/\*\*/g, "").replace(/\*/g, "").replace(/`/g, "").replace(/^#{1,6}\s*/, "").trim();
}
function rowCells(row) {
  let parts = row.split("|").map((s) => stripInline(s));
  if (parts.length && parts[0] === "") parts.shift();
  if (parts.length && parts[parts.length - 1] === "") parts.pop();
  return parts;
}
function downloadPdf(text) {
  const J = window.jspdf && window.jspdf.jsPDF;
  if (!J) { alert("Export is still loading, please try again in a moment."); return; }
  const doc = new J({ unit: "pt", format: "a4" });
  const M = 46, W = doc.internal.pageSize.getWidth(), PH = doc.internal.pageSize.getHeight();
  const GOLD = [138, 106, 40], INK = [20, 32, 46], MUTE = [120, 120, 120];
  let y = M;
  const ensure = (h) => { if (y + h > PH - M - 24) { doc.addPage(); y = M; } };

  // Masthead
  doc.setFont("times", "bold"); doc.setTextColor(...GOLD); doc.setFontSize(18);
  doc.text("KEYSTONE", M, y);
  doc.setFont("times", "normal"); doc.setFontSize(8); doc.setTextColor(...MUTE);
  doc.text("CONSTRUCTION COMMAND CENTER", M, y + 12);
  doc.text(new Date().toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }),
    W - M, y, { align: "right" });
  y += 20;
  doc.setDrawColor(...GOLD); doc.setLineWidth(1); doc.line(M, y, W - M, y);
  doc.setLineWidth(0.5); doc.setDrawColor(216, 201, 159); doc.line(M, y + 2.5, W - M, y + 2.5);
  y += 24;
  doc.setTextColor(...INK); doc.setFont("times", "normal"); doc.setFontSize(10.5);

  const lines = clean(text).replace(/\r/g, "").split("\n");
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (/^={3,}\s*$/.test(line)) { i++; continue; }
    // Horizontal rule.
    if (/^\s*-{3,}\s*$/.test(line)) {
      ensure(14); y += 4; doc.setDrawColor(222, 212, 190); doc.setLineWidth(0.5);
      doc.line(M, y, W - M, y); y += 12; i++; continue;
    }
    if (!line.trim()) { y += 5; i++; continue; }

    // Document title line.
    if (/^PROJECT REPORT|^EMAIL DRAFT|^BUDGET TRANSFER/i.test(line.trim())) {
      ensure(26); doc.setFont("times", "bold"); doc.setFontSize(15); doc.setTextColor(...INK);
      doc.text(stripInline(line), M, y); y += 20;
      doc.setFont("times", "normal"); doc.setFontSize(10.5);
      i++; continue;
    }

    // Table.
    if (line.includes("|") && i + 1 < lines.length &&
        /-/.test(lines[i + 1]) && /^[\s|:\-]+$/.test(lines[i + 1])) {
      const head = [rowCells(line)];
      i += 2;
      const body = [];
      while (i < lines.length && lines[i].includes("|")) { body.push(rowCells(lines[i])); i++; }
      ensure(44);
      doc.autoTable({
        head, body, startY: y, margin: { left: M, right: M },
        styles: { fontSize: 8, cellPadding: 4, textColor: INK, lineColor: [222, 216, 198], lineWidth: 0.5, font: "times" },
        headStyles: { fillColor: [244, 238, 223], textColor: GOLD, fontStyle: "bold" },
        alternateRowStyles: { fillColor: [250, 247, 240] },
        theme: "grid",
      });
      y = doc.lastAutoTable.finalY + 16;
      continue;
    }

    // Section heading: markdown # or a numbered title like "2. BUDGET STATUS".
    if (/^#{1,6}\s/.test(line) || /^\d+\.\s+[A-Z]/.test(line.trim())) {
      ensure(30); y += 8;
      doc.setFont("times", "bold"); doc.setFontSize(12); doc.setTextColor(...GOLD);
      const t = stripInline(line); doc.text(t, M, y);
      doc.setDrawColor(222, 212, 190); doc.setLineWidth(0.5); doc.line(M, y + 4, W - M, y + 4);
      y += 18; doc.setFont("times", "normal"); doc.setFontSize(10.5); doc.setTextColor(...INK);
      i++; continue;
    }

    // Bullet (drawn dot).
    if (/^\s*[-*•]\s+/.test(line)) {
      const t = stripInline(line.replace(/^\s*[-*•]\s+/, ""));
      const wrapped = doc.splitTextToSize(t, W - 2 * M - 16);
      ensure(wrapped.length * 13 + 2);
      doc.setFillColor(...GOLD); doc.circle(M + 4, y - 3, 1.4, "F");
      doc.text(wrapped, M + 14, y); y += wrapped.length * 13 + 3;
      i++; continue;
    }

    // Paragraph.
    const wrapped = doc.splitTextToSize(stripInline(line), W - 2 * M);
    ensure(wrapped.length * 13 + 3);
    doc.text(wrapped, M, y); y += wrapped.length * 13 + 5;
    i++;
  }

  // Footer page numbers.
  const pages = doc.internal.getNumberOfPages();
  for (let p = 1; p <= pages; p++) {
    doc.setPage(p);
    doc.setFont("times", "normal"); doc.setFontSize(8); doc.setTextColor(...MUTE);
    doc.text("KEYSTONE", M, PH - 20);
    doc.text(`Page ${p} of ${pages}`, W - M, PH - 20, { align: "right" });
  }

  doc.save("keystone-report.pdf");
}

export default function ChatInterface() {
  const [messages, setMessages] = useState([
    { role: "system", text:
      "Keystone Command Center. Ask for a project status report, draft an email, " +
      "transfer budget between projects, or request an overview of all projects." },
  ]);
  const [input, setInput] = useState("");
  const [threadId, setThreadId] = useState(null);
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  async function send() {
    const msg = input.trim();
    if (!msg || busy) return;
    setMessages((m) => [...m, { role: "user", text: msg }]);
    setInput(""); setBusy(true);
    try {
      const { data } = await axios.post(`${API}/chat`, { message: msg, thread_id: threadId });
      setThreadId(data.thread_id);
      if (data.status === "awaiting_approval") {
        const kind = data.interrupt?.kind || "approval";
        setMessages((m) => [...m, { role: "agent",
          text: `Paused for human approval (${kind}). Open the Approvals tab to review.` }]);
      } else {
        setMessages((m) => [...m, { role: "agent", text: data.response }]);
      }
    } catch (e) {
      const detail = e?.response?.data?.error || e.message;
      setMessages((m) => [...m, { role: "agent", text: `Error: ${detail}` }]);
    } finally { setBusy(false); }
  }

  return (
    <div className="ks-chat">
      <div className="ks-messages">
        {messages.map((m, i) => {
          if (m.role === "user") return <div key={i} className="ks-msg user">{m.text}</div>;
          const md = renderMd(m.text);
          if (!md) return <div key={i} className={`ks-msg ${m.role}`}>{m.text}</div>;
          const isReport = /PROJECT REPORT|EXECUTIVE SUMMARY|BUDGET TRANSFER|EMAIL DRAFT/.test(m.text);
          return (
            <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 6, maxWidth: "94%" }}>
              <div className={`ks-msg ${m.role} ks-md`} style={{ maxWidth: "100%" }} dangerouslySetInnerHTML={md} />
              {isReport && <button className="ks-pdf-btn" onClick={() => downloadPdf(m.text)}>Download PDF</button>}
            </div>
          );
        })}
        <div ref={endRef} />
      </div>
      <div className="ks-input-row">
        <input className="ks-input" value={input} onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()} placeholder="Ask about your projects..." disabled={busy} />
        <button className="ks-btn solid" onClick={send} disabled={busy || !input.trim()}>
          {busy ? "Working" : "Send"}
        </button>
      </div>
      {threadId && <div className="ks-muted" style={{ fontSize: ".75rem", marginTop: 6 }}>thread: {threadId.slice(0, 8)}…</div>}
    </div>
  );
}
