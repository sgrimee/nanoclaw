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
