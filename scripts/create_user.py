"""Creates a pre-approved user directly in Firestore.

Registration is intentionally NOT exposed over HTTP (no public /register) — this app is a
closed roster of pre-made accounts, run by the owner locally against real GCP credentials:

    PYTHONPATH=. .venv/bin/python scripts/create_user.py <username> <password>
"""

from __future__ import annotations

import sys

from backend.auth.service import UsernameTakenError, register


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} <username> <password>", file=sys.stderr)
        raise SystemExit(1)

    username, password = sys.argv[1], sys.argv[2]
    try:
        register(username, password)
    except UsernameTakenError:
        print(f"'{username}' already exists — skipping.")
        return
    print(f"Created user '{username}'.")


if __name__ == "__main__":
    main()
