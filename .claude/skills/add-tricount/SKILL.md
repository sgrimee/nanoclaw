---
name: add-tricount
description: Add Tricount shared expense tracking to NanoClaw. Read-only access to Tricount registries — view summaries, expenses, members, and balances. Use when user wants expense tracking, Tricount integration, or shared expense queries. Triggers on "tricount", "shared expenses", "expense tracker", "who owes what".
disable-model-invocation: true
---

# Tricount Expense Tracking

> **Note:** This skill uses `docker` commands for container operations. On macOS, use the equivalent `launchctl` commands for service management.

This skill adds read-only Tricount expense tracking to NanoClaw. It creates a container skill with a Python API client, CLI wrapper, and shell script that auto-installs dependencies on first use.

**What this changes:**
- Creates `container/skills/tricount/SKILL.md` — skill documentation
- Creates `container/skills/tricount/tricnt.py` — API client (~300 lines, RSA auth, httpx)
- Creates `container/skills/tricount/tricount_cli.py` — CLI wrapper (summary, expenses, members, balances)
- Creates `container/skills/tricount/tricount.sh` — shell wrapper (auto-installs deps via uv)

**What stays the same:**
- No source code modifications
- Container rebuild needed only to include the new files

## Prerequisites

1. **add-python** — Python3 + uv in the container. Verify:

   ```bash
   docker run --rm --entrypoint python3 nanoclaw-agent:latest --version
   docker run --rm --entrypoint uv nanoclaw-agent:latest --version
   ```

   If either fails, apply the `add-python` skill first.

2. **add-group-env** — Per-group environment variables. Required so each group can have its own Tricount credentials in `groups/{folder}/.env`. If not yet applied, apply it first.

## 1. Create Skill Documentation

Create `container/skills/tricount/SKILL.md`:

````markdown
---
name: tricount
description: Query Tricount shared expense data — view summaries, expenses, members, and balances. Use when the user asks about shared expenses, who owes what, or expense history.
allowed-tools: Bash(tricount:*)
---

# Tricount Expense Tracker

Read-only access to Tricount shared expense registries.

## Quick start

```bash
tricount.sh summary                    # Registry overview with recent expenses and balances
tricount.sh expenses --limit 10        # List recent expenses
tricount.sh members                    # List all members
tricount.sh balances                   # Show who owes what
```

## Commands

### summary

Show registry overview including title, total expenses, recent expenses, and member balances.

```bash
tricount.sh summary                    # Use default registry
tricount.sh summary TOKEN              # Use specific registry token
```

### expenses

List expenses with optional limit.

```bash
tricount.sh expenses                   # All expenses (default registry)
tricount.sh expenses --limit 5         # Last 5 expenses
tricount.sh expenses TOKEN             # Specific registry
tricount.sh expenses TOKEN --limit 10  # Specific registry, limited
```

### members

List all members and their status.

```bash
tricount.sh members                    # Default registry
tricount.sh members TOKEN              # Specific registry
```

### balances

Show current balance for each member (positive = is owed, negative = owes money).

```bash
tricount.sh balances                   # Default registry
tricount.sh balances TOKEN             # Specific registry
```

## Notes

- **Read-only**: Expenses cannot be created via this tool. Direct users to the Tricount app or web interface.
- The default registry token comes from `TRICOUNT_DEFAULT_REGISTRY_ID` environment variable.
- Authentication keys are auto-generated on first run.
````

## 2. Create API Client

Create `container/skills/tricount/tricnt.py`:

```python
"""
Tricount API client for read-only access to shared registries.

Usage:
    client = TricntClient(
        app_id="your_app_id",
        client_request_id="your_client_request_id",
        private_key_path="/path/to/private_key.pem"
    )
    client.authenticate()
    info = client.get_registry_info("your_registry_token")
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

logger = logging.getLogger(__name__)


@dataclass
class RegistryInfo:
    id: int
    title: str
    currency: str
    emoji: str
    web_link: str
    member_count: int
    expense_count: int


@dataclass
class Member:
    id: int
    name: str
    status: str


@dataclass
class Expense:
    id: int
    description: str
    amount: float
    currency: str
    date: str
    payer: str
    category: str
    beneficiaries: List[str]


class TricntError(Exception):
    pass


class TricntClient:
    def __init__(
        self,
        app_id: str,
        client_request_id: str,
        private_key_path: str,
    ):
        self.base_url = "https://api.tricount.bunq.com"
        self.app_id = app_id
        self.client_request_id = client_request_id
        self.private_key_path = private_key_path

        self._session_token: Optional[str] = None
        self._user_id: Optional[int] = None
        self._http_client: Optional[httpx.Client] = None

    def _get_http_client(self) -> httpx.Client:
        if not self._http_client:
            self._http_client = httpx.Client(
                headers={
                    "User-Agent": "com.bunq.tricount.android:RELEASE:7.0.7:3174:ANDROID:13:C",
                    "app-id": self.app_id,
                    "X-Bunq-Client-Request-Id": self.client_request_id,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._http_client

    def _load_or_generate_key(self) -> RSAPrivateKey:
        try:
            with open(self.private_key_path, "rb") as f:
                key = serialization.load_pem_private_key(
                    f.read(), password=None, backend=default_backend()
                )
                if not isinstance(key, rsa.RSAPrivateKey):
                    raise TricntError("Key file contains non-RSA key")
                return key
        except FileNotFoundError:
            key_dir = os.path.dirname(self.private_key_path)
            if key_dir:
                os.makedirs(key_dir, exist_ok=True)

            private_key = rsa.generate_private_key(
                public_exponent=65537, key_size=2048, backend=default_backend()
            )

            pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )

            with open(self.private_key_path, "wb") as f:
                f.write(pem)
            os.chmod(self.private_key_path, 0o600)

            logger.info(f"Generated new private key at {self.private_key_path}")
            return private_key

    def _get_public_key_pem(self) -> str:
        private_key = self._load_or_generate_key()
        public_key = private_key.public_key()
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return pem.decode("utf-8")

    def authenticate(self) -> bool:
        """Authenticate with the Tricount API. Generates a new key pair if needed."""
        try:
            public_key = self._get_public_key_pem()

            response = self._get_http_client().post(
                f"{self.base_url}/v1/session-registry-installation",
                json={
                    "app_installation_uuid": self.app_id,
                    "client_public_key": public_key,
                    "device_description": "Android",
                },
            )

            if response.status_code != 200:
                raise TricntError(f"Authentication failed: HTTP {response.status_code}")

            data = response.json()

            self._session_token = None
            self._user_id = None

            for item in data.get("Response", []):
                if "Token" in item and not self._session_token:
                    self._session_token = item["Token"]["token"]
                elif "UserPerson" in item and not self._user_id:
                    self._user_id = item["UserPerson"]["id"]

            if not self._session_token or not self._user_id:
                raise TricntError("Authentication response missing token or user ID")

            self._get_http_client().headers["X-Bunq-Client-Authentication"] = (
                self._session_token
            )

            logger.info("Successfully authenticated with Tricount API")
            return True

        except httpx.RequestError as e:
            raise TricntError(f"Network error during authentication: {e}")

    def _get_registry_data(self, registry_token: str) -> Dict[str, Any]:
        if not self._user_id:
            raise TricntError("Not authenticated - call authenticate() first")

        try:
            response = self._get_http_client().get(
                f"{self.base_url}/v1/user/{self._user_id}/registry",
                params={"public_identifier_token": registry_token},
            )
            response.raise_for_status()

            data = response.json()
            if not data.get("Response"):
                raise TricntError(f"Registry {registry_token} not found")

            return data["Response"][0]["Registry"]

        except httpx.HTTPStatusError as e:
            raise TricntError(
                f"HTTP error getting registry data: {e.response.status_code}"
            )

    def get_registry_info(self, registry_token: str) -> RegistryInfo:
        if not self._user_id:
            raise TricntError("Not authenticated - call authenticate() first")

        try:
            response = self._get_http_client().get(
                f"{self.base_url}/v1/user/{self._user_id}/registry",
                params={"public_identifier_token": registry_token},
            )
            response.raise_for_status()

            data = response.json()
            if not data.get("Response"):
                raise TricntError(f"Registry {registry_token} not found")

            registry = data["Response"][0]["Registry"]

            return RegistryInfo(
                id=registry["id"],
                title=registry["title"],
                currency=registry["currency"],
                emoji=registry.get("emoji", ""),
                web_link=f"https://tricount.com/{registry_token}",
                member_count=len(registry.get("memberships", [])),
                expense_count=len(registry.get("all_registry_entry", [])),
            )

        except httpx.HTTPStatusError as e:
            raise TricntError(
                f"HTTP error getting registry info: {e.response.status_code}"
            )

    def get_members(self, registry_token: str) -> List[Member]:
        registry_data = self._get_registry_data(registry_token)
        members = []

        for membership in registry_data.get("memberships", []):
            member_data = membership["RegistryMembershipNonUser"]
            members.append(
                Member(
                    id=member_data["id"],
                    name=member_data["alias"]["display_name"],
                    status=member_data["status"],
                )
            )

        return members

    def get_expenses(self, registry_token: str) -> List[Expense]:
        registry_data = self._get_registry_data(registry_token)
        expenses = []

        for entry in registry_data.get("all_registry_entry", []):
            expense_data = entry["RegistryEntry"]

            payer = expense_data["membership_owned"]["RegistryMembershipNonUser"]
            payer_name = payer["alias"]["display_name"]

            beneficiaries = []
            for alloc in expense_data.get("allocations", []):
                if alloc.get("membership", {}).get("RegistryMembershipNonUser"):
                    member = alloc["membership"]["RegistryMembershipNonUser"]
                    beneficiaries.append(member["alias"]["display_name"])

            expenses.append(
                Expense(
                    id=expense_data["id"],
                    description=expense_data["description"],
                    amount=abs(float(expense_data["amount"]["value"])),
                    currency=expense_data["amount"]["currency"],
                    date=expense_data["date"],
                    payer=payer_name,
                    category=expense_data.get("category", "UNCATEGORIZED"),
                    beneficiaries=beneficiaries,
                )
            )

        return expenses

    def calculate_balances(self, registry_token: str) -> Dict[str, float]:
        members = self.get_members(registry_token)
        expenses = self.get_expenses(registry_token)

        balances = {member.name: 0.0 for member in members}

        for expense in expenses:
            if expense.payer in balances:
                balances[expense.payer] += expense.amount

            if expense.beneficiaries:
                per_person = expense.amount / len(expense.beneficiaries)
                for beneficiary in expense.beneficiaries:
                    if beneficiary in balances:
                        balances[beneficiary] -= per_person

        return balances

    def close(self) -> None:
        if self._http_client:
            self._http_client.close()
            self._http_client = None

    def __enter__(self) -> "TricntClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
```

## 3. Create CLI Wrapper

Create `container/skills/tricount/tricount_cli.py`:

```python
#!/usr/bin/env python3
"""CLI for querying Tricount expense data."""

import argparse
import os
import sys

from tricnt import TricntClient, TricntError


def get_client() -> TricntClient:
    app_id = os.environ.get("TRICOUNT_APP_ID")
    client_request_id = os.environ.get("TRICOUNT_CLIENT_REQUEST_ID")
    private_key_path = os.environ.get("TRICOUNT_PRIVATE_KEY_PATH")

    if not all([app_id, client_request_id, private_key_path]):
        print(
            "Error: Missing environment variables. Need TRICOUNT_APP_ID, "
            "TRICOUNT_CLIENT_REQUEST_ID, TRICOUNT_PRIVATE_KEY_PATH",
            file=sys.stderr,
        )
        sys.exit(1)

    return TricntClient(
        app_id=app_id,
        client_request_id=client_request_id,
        private_key_path=private_key_path,
    )


def get_token(args_token: str | None) -> str:
    token = args_token or os.environ.get("TRICOUNT_DEFAULT_REGISTRY_ID")
    if not token:
        print(
            "Error: No registry token provided and TRICOUNT_DEFAULT_REGISTRY_ID not set",
            file=sys.stderr,
        )
        sys.exit(1)
    return token


def cmd_summary(client: TricntClient, token: str, _args: argparse.Namespace) -> None:
    info = client.get_registry_info(token)
    members = client.get_members(token)
    expenses = client.get_expenses(token)
    balances = client.calculate_balances(token)

    total = sum(e.amount for e in expenses)

    print(f"{info.emoji} {info.title}")
    print(f"Currency: {info.currency}")
    print(f"Link: {info.web_link}")
    print(f"Members: {info.member_count} | Expenses: {info.expense_count} | Total: {total:.2f} {info.currency}")
    print()

    # Recent expenses
    recent = expenses[-5:]
    if recent:
        print("Recent expenses:")
        for e in reversed(recent):
            beneficiary_str = f" (for {', '.join(e.beneficiaries)})" if e.beneficiaries else ""
            print(f"  {e.date} | {e.amount:.2f} {e.currency} | {e.description} — paid by {e.payer}{beneficiary_str}")
        print()

    # Balances
    print("Balances:")
    for name, balance in sorted(balances.items(), key=lambda x: x[1]):
        status = "owes" if balance < 0 else "is owed"
        print(f"  {name}: {balance:+.2f} {info.currency} ({status})")


def cmd_expenses(client: TricntClient, token: str, args: argparse.Namespace) -> None:
    expenses = client.get_expenses(token)
    info = client.get_registry_info(token)

    if args.limit:
        expenses = expenses[-args.limit:]

    print(f"Expenses for {info.title} ({len(expenses)} shown):")
    print()
    for e in reversed(expenses):
        beneficiary_str = f" (for {', '.join(e.beneficiaries)})" if e.beneficiaries else ""
        cat = f" [{e.category}]" if e.category != "UNCATEGORIZED" else ""
        print(f"  {e.date} | {e.amount:.2f} {e.currency} | {e.description}{cat} — paid by {e.payer}{beneficiary_str}")


def cmd_members(client: TricntClient, token: str, _args: argparse.Namespace) -> None:
    members = client.get_members(token)
    info = client.get_registry_info(token)

    print(f"Members of {info.title}:")
    for m in members:
        print(f"  {m.name} ({m.status})")


def cmd_balances(client: TricntClient, token: str, _args: argparse.Namespace) -> None:
    balances = client.calculate_balances(token)
    info = client.get_registry_info(token)

    print(f"Balances for {info.title}:")
    for name, balance in sorted(balances.items(), key=lambda x: x[1]):
        status = "owes" if balance < 0 else "is owed"
        print(f"  {name}: {balance:+.2f} {info.currency} ({status})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Query Tricount expense data")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # summary
    p_summary = subparsers.add_parser("summary", help="Registry overview")
    p_summary.add_argument("token", nargs="?", help="Registry token (optional)")

    # expenses
    p_expenses = subparsers.add_parser("expenses", help="List expenses")
    p_expenses.add_argument("token", nargs="?", help="Registry token (optional)")
    p_expenses.add_argument("--limit", type=int, help="Number of recent expenses to show")

    # members
    p_members = subparsers.add_parser("members", help="List members")
    p_members.add_argument("token", nargs="?", help="Registry token (optional)")

    # balances
    p_balances = subparsers.add_parser("balances", help="Show member balances")
    p_balances.add_argument("token", nargs="?", help="Registry token (optional)")

    args = parser.parse_args()

    commands = {
        "summary": cmd_summary,
        "expenses": cmd_expenses,
        "members": cmd_members,
        "balances": cmd_balances,
    }

    with get_client() as client:
        client.authenticate()
        token = get_token(getattr(args, "token", None))
        commands[args.command](client, token, args)


if __name__ == "__main__":
    main()
```

## 4. Create Shell Wrapper

Create `container/skills/tricount/tricount.sh` (make it executable):

```bash
#!/bin/bash
# Auto-install tricount deps into persistent group venv on first use
VENV=/workspace/group/.venv
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"

if ! "$VENV/bin/python" -c "import httpx, cryptography" 2>/dev/null; then
  uv venv "$VENV" 2>/dev/null
  uv pip install --python "$VENV/bin/python" httpx cryptography >&2
fi

PYTHONPATH="$SKILL_DIR" "$VENV/bin/python" "$SKILL_DIR/tricount_cli.py" "$@"
```

After creating the file, make it executable:

```bash
chmod +x container/skills/tricount/tricount.sh
```

## 5. Setup (Per Group)

To enable Tricount for a group, add these env vars to the group's `.env` file:

```
TRICOUNT_APP_ID=<uuid>
TRICOUNT_CLIENT_REQUEST_ID=<uuid>
TRICOUNT_PRIVATE_KEY_PATH=/workspace/group/.tricount_key.pem
TRICOUNT_DEFAULT_REGISTRY_ID=<registry-token>
```

The `APP_ID` and `CLIENT_REQUEST_ID` are UUIDs that identify the API client. Generate them with `uuidgen` or similar.

## 6. Rebuild and Verify

```bash
# Rebuild container to include the new files
./container/build.sh

# Verify files are in the container image
docker run --rm --entrypoint ls nanoclaw-agent:latest -la /app/skills/tricount/
```

Restart the NanoClaw service so the new container image is used.

## Summary of Changed Files

| File | Type of Change |
|------|----------------|
| `container/skills/tricount/SKILL.md` | New file — skill documentation |
| `container/skills/tricount/tricnt.py` | New file — Tricount API client |
| `container/skills/tricount/tricount_cli.py` | New file — CLI wrapper |
| `container/skills/tricount/tricount.sh` | New file — shell wrapper (executable) |
