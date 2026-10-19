"""Rebuild the UnderCover database from the records in data/."""

import json
from contextlib import closing
from pathlib import Path
from typing import Any

from backend import db

DATA = Path(__file__).parent.parent / "data"


def load(name: str) -> Any:
    """Read one JSON file from data/."""
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def seed() -> dict[str, int]:
    """Replace the database with a fresh copy of the records and return the counts."""
    db.path().unlink(missing_ok=True)
    claims = load("claims.json")
    policies = load("policies.json")
    customers = load("customers.json")
    plans = load("plans.json")
    handlers = load("handlers.json")
    company = load("company.json")
    with closing(db.connect()) as connection, connection:
        connection.executescript(db.SCHEMA)
        connection.executemany(
            "INSERT INTO settings VALUES (?, ?)",
            [(key, json.dumps(value)) for key, value in company.items()],
        )
        connection.executemany(
            "INSERT INTO plans VALUES (?, ?)",
            [(plan["plan"], json.dumps(plan)) for plan in plans["plans"]],
        )
        connection.executemany(
            "INSERT INTO add_ons VALUES (?, ?)",
            [(add_on["add_on"], json.dumps(add_on)) for add_on in plans["add_ons"]],
        )
        connection.executemany(
            "INSERT INTO policies VALUES (?, ?)",
            [(policy["policy_id"], json.dumps(policy)) for policy in policies],
        )
        connection.executemany(
            "INSERT INTO customers VALUES (?, ?)",
            [(customer["customer_id"], json.dumps(customer)) for customer in customers],
        )
        connection.executemany(
            "INSERT INTO handlers VALUES (?, ?)",
            [(handler["handler_id"], json.dumps(handler)) for handler in handlers],
        )
        connection.executemany(
            "INSERT INTO claims (claim_id, position, data, status)"
            " VALUES (?, ?, ?, 'waiting')",
            [
                (claim["claim_id"], position, json.dumps(claim))
                for position, claim in enumerate(claims)
            ],
        )
    return {
        "claims": len(claims),
        "policies": len(policies),
        "customers": len(customers),
        "handlers": len(handlers),
    }


if __name__ == "__main__":
    counts = seed()
    print(f"Loaded {', '.join(f'{n} {name}' for name, n in counts.items())}")
