# Add /clear Command Skill

Add a `/clear` command to your NanoClaw installation that resets conversation context while preserving all files and memory.

## What It Does

This skill adds a `/clear` command that users can send via WhatsApp to:
- Reset the conversation context (clear session history)
- Start fresh without historical context
- Optionally provide a new prompt in the same message
- Keep all CLAUDE.md files, documents, and workspace files intact

## Installation

From your NanoClaw directory with Claude Code:

```
/add-clear-command
```

Claude Code will guide you through the installation step-by-step.

## Usage After Installation

**Clear context only:**
```
@YourAssistant /clear
```

**Clear context and ask new question:**
```
@YourAssistant /clear What's the weather today?
```

**Mixed with other text:**
```
@YourAssistant hey can you /clear and help me with something new
```

## What Gets Changed

- `src/db.ts` - Adds `deleteSession()` function
- `src/index.ts` - Adds `/clear` command detection logic
- `groups/main/CLAUDE.md` - Adds command documentation
- `groups/global/CLAUDE.md` - Adds command documentation

## Benefits

- **Avoid context confusion**: Old conversations won't interfere with new requests
- **Save tokens**: Start fresh without long context history
- **Better responses**: Assistant focuses only on current task
- **Flexible usage**: Use alone or combine with new prompt
- **Safe**: All files, documents, and memory preserved

## Why This Matters

Over time, conversation context can accumulate irrelevant information, causing the assistant to:
- Reference old, unrelated conversations
- Mix up tasks from different days
- Use up context window with outdated information

The `/clear` command solves this by giving you a clean slate while keeping all persistent data (CLAUDE.md, documents, calendar, etc.) intact.

## Requirements

- NanoClaw installation (basic setup complete)
- TypeScript compilation (`npm run build`) after changes
- Restart of NanoClaw service

## Related

- See `/customize` for other customization options
- See `/setup` for initial NanoClaw configuration
