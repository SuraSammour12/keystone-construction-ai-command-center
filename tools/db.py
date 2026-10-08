"""
Keystone system of record.

A real SQLite database that the automation READS and WRITES. Unlike the old
static JSON, state here changes when an action is approved: a transfer posts
ledger entries, an approved invoice is posted, and every change is audited.

Connection handling is safe for Flask's threaded server: each call opens its
own short-lived connection (sqlite3 connections are not shareable across
threads). WAL mode keeps readers and the single writer from blocking.
"""
import os
import sqlite3

DB_PATH = os.environ.get(
    "KEYSTONE_DB",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "keystone.db"),
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    type          TEXT,
    location      TEXT,
    status        TEXT,
    project_manager TEXT,
    client        TEXT
);

CREATE TABLE IF NOT EXISTS budget_lines (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  TEXT NOT NULL REFERENCES projects(id),
    category    TEXT NOT NULL,
    budgeted    REAL NOT NULL,
    actual      REAL NOT NULL,
    note        TEXT
);

CREATE TABLE IF NOT EXISTS purchase_orders (
    id          TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL REFERENCES projects(id),
    contractor  TEXT NOT NULL,
    category    TEXT,
    amount      REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS invoices (
    id          TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL REFERENCES projects(id),
    po_id       TEXT REFERENCES purchase_orders(id),
    contractor  TEXT NOT NULL,
    category    TEXT,
    amount      REAL NOT NULL,
    due_date    TEXT,
    status      TEXT NOT NULL DEFAULT 'Pending Approval'   -- Pending Approval | Approved | Rejected
);

-- Every budget-changing event. The ledger, not a field, is the source of
-- truth for adjustments and postings.
CREATE TABLE IF NOT EXISTS ledger_entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL DEFAULT (datetime('now')),
    project_id  TEXT NOT NULL REFERENCES projects(id),
    entry_type  TEXT NOT NULL,       -- transfer_in | transfer_out | invoice_post
    amount      REAL NOT NULL,
    memo        TEXT,
    ref         TEXT                 -- thread_id or invoice id that caused it
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL DEFAULT (datetime('now')),
    actor       TEXT NOT NULL,
    action      TEXT NOT NULL,
    thread_id   TEXT,
    detail      TEXT                 -- JSON string
);

CREATE TABLE IF NOT EXISTS roi_events (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    ts             TEXT NOT NULL DEFAULT (datetime('now')),
    kind           TEXT NOT NULL,
    minutes_saved  REAL NOT NULL DEFAULT 0,
    dollars_flagged REAL NOT NULL DEFAULT 0,
    doc_count      INTEGER NOT NULL DEFAULT 0,
    detail         TEXT
);

CREATE INDEX IF NOT EXISTS idx_ledger_project ON ledger_entries(project_id);
CREATE INDEX IF NOT EXISTS idx_invoice_project ON invoices(project_id);
CREATE INDEX IF NOT EXISTS idx_audit_thread ON audit_log(thread_id);
"""


def get_conn():
    """Open a short-lived connection. Caller closes it (use `with closing(...)`)."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_schema(conn):
    conn.executescript(SCHEMA)
    conn.commit()
