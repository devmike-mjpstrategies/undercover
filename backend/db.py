"""The UnderCover database."""

import os
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE plans (plan TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE add_ons (add_on TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE policies (policy_id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE customers (customer_id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE handlers (handler_id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE claims (
    claim_id TEXT PRIMARY KEY,
    position INTEGER NOT NULL,
    data TEXT NOT NULL,
    status TEXT NOT NULL,
    decision TEXT,
    payout REAL,
    reason TEXT,
    policy_section TEXT,
    decided_at TEXT,
    paid_amount REAL,
    paid_by TEXT,
    paid_at TEXT,
    signed_off_by TEXT,
    signed_off_at TEXT
);
CREATE TABLE steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def path() -> Path:
    """Return the database file, from UNDERCOVER_DB or undercover.db."""
    return Path(os.getenv("UNDERCOVER_DB", "undercover.db"))


def connect() -> sqlite3.Connection:
    """Open a connection that returns rows by column name."""
    connection = sqlite3.connect(path(), check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection
