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
