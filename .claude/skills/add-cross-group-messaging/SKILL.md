---
name: add-cross-group-messaging
description: Allow the main group agent to send messages to other registered WhatsApp groups. Adds a `target_group_jid` parameter to the `send_message` MCP tool so the main group can push messages or images into any registered group. Use when the user wants to broadcast from main, send notifications to specific groups, or have the main agent communicate across groups. Triggers on "send to other group", "message another group", "cross-group messaging", "broadcast from main".
disable-model-invocation: true
---

# Add Cross-Group Messaging

This skill adds the ability for the main group agent to send messages to any other registered WhatsApp group. It extends the existing `send_message` MCP tool with an optional `target_group_jid` parameter. The host-side authorization (`ipc.ts`) already permits the main group to target any registered JID, so only two files change.

**What this adds:**
- `target_group_jid` optional parameter on `mcp__nanoclaw__send_message`
- Works for both text messages and images
- Non-main agents silently ignore the parameter (falls back to their own chat)
- Documentation in `groups/main/CLAUDE.md`

**What stays the same:**
- IPC message format and types — no new types
- Host-side routing and authorization code — unchanged
- All other MCP tools — unchanged

## 1. Update the MCP tool in `container/agent-runner/src/ipc-mcp-stdio.ts`

### 1a. Add `target_group_jid` to the tool schema and update the description

Find the `server.tool('send_message', ...)` call. Replace the description string and the schema object as follows.

**Old description (first argument after tool name):**
```
"Send a message or image to the user immediately while still running. Use ONLY for: (1) intermediate progress updates before your final response, (2) sending images. Do NOT use for your final text answer — your text output is automatically delivered, so calling this AND outputting text will send the user two messages. If you call this for your final answer, wrap your text output in <internal> tags. For scheduled tasks, your text output is NOT sent — use this tool to communicate."
```

**New description:**
```
"Send a message or image to the user immediately while still running. Use ONLY for: (1) intermediate progress updates before your final response, (2) sending images, (3) sending messages to other registered groups (main group only). Do NOT use for your final text answer — your text output is automatically delivered, so calling this AND outputting text will send the user two messages. If you call this for your final answer, wrap your text output in <internal> tags. For scheduled tasks, your text output is NOT sent — use this tool to communicate."
```

**Old schema object:**
```typescript
  {
    text: z.string().describe('The message text to send'),
    image_path: z.string().optional().describe(
      'Absolute path to an image file to send alongside the message (e.g. /tmp/screenshot.png). Supported formats: jpeg, png, webp, gif.'
    ),
    sender: z.string().optional().describe('Your role/identity name (e.g. "Researcher"). When set, messages appear from a dedicated bot in Telegram.'),
  },
```

**New schema object** (add `target_group_jid` as the last field):
```typescript
  {
    text: z.string().describe('The message text to send'),
    image_path: z.string().optional().describe(
      'Absolute path to an image file to send alongside the message (e.g. /tmp/screenshot.png). Supported formats: jpeg, png, webp, gif.'
    ),
    sender: z.string().optional().describe('Your role/identity name (e.g. "Researcher"). When set, messages appear from a dedicated bot in Telegram.'),
    target_group_jid: z.string().optional().describe(
      '(Main group only) JID of the registered group to send to (e.g. "120363336345536173@g.us"). Defaults to the current group. Find JIDs in /workspace/ipc/available_groups.json.'
    ),
  },
```

### 1b. Add `targetJid` resolution at the top of the handler

Find the `async (args) => {` opening of the send_message handler. Insert this line immediately after it, before any other logic:

**Insert after `async (args) => {`:**
```typescript
    const targetJid = (isMain && args.target_group_jid) ? args.target_group_jid : chatJid;
```

### 1c. Replace `chatJid` with `targetJid` in the handler body

The handler uses `chatJid` in two places — the image branch and the text branch. Replace both with `targetJid`:

**Image branch — old:**
```typescript
      writeIpcFile(MESSAGES_DIR, {
        type: 'image',
        chatJid,
```

**Image branch — new:**
```typescript
      writeIpcFile(MESSAGES_DIR, {
        type: 'image',
        chatJid: targetJid,
```

**Text branch — old:**
```typescript
    const data: Record<string, string | undefined> = {
      type: 'message',
      chatJid,
```

**Text branch — new:**
```typescript
    const data: Record<string, string | undefined> = {
      type: 'message',
      chatJid: targetJid,
```

## 2. Document in `groups/main/CLAUDE.md`

Find the "Sending Images" section. Add the following block immediately after it (before the "## Message Formatting" section):

```markdown
### Sending Messages to Other Groups

As the main group, you can send messages to any registered group using `target_group_jid`:

```
mcp__nanoclaw__send_message(text="Hello from main!", target_group_jid="120363336345536173@g.us")
```

Find group JIDs in `/workspace/ipc/available_groups.json` (filter by `isRegistered: true`). Always wrap your own text output in `<internal>` tags when using this for your final action, to avoid sending two messages.
```

## 3. Rebuild the container

The MCP tool runs inside the container, so a rebuild is required:

```bash
# Prune build cache to avoid stale COPY layers
docker buildx prune -f

# Rebuild
./container/build.sh
```

Both `npm run build` (TypeScript compile) and `docker build` must succeed before proceeding.

## 4. Verify

Write a test IPC file directly as the main group, targeting any registered group JID. The IPC watcher will pick it up and send via WhatsApp:

```bash
node -e "
const fs = require('fs'), path = require('path');
const dir = 'data/ipc/main/messages';
fs.mkdirSync(dir, { recursive: true });
const file = path.join(dir, Date.now() + '-xgtest.json');
const tmp = file + '.tmp';
fs.writeFileSync(tmp, JSON.stringify({
  type: 'message',
  chatJid: '<TARGET_JID>',
  text: 'Cross-group messaging test from main.',
  groupFolder: 'main',
  timestamp: new Date().toISOString()
}));
fs.renameSync(tmp, file);
console.log('Written:', file);
"
```

Replace `<TARGET_JID>` with a registered group's JID from `data/ipc/main/available_groups.json`.

After 1–2 seconds the file disappears (consumed by the IPC watcher). Check logs:

```bash
journalctl --user -u nanoclaw --since "30 seconds ago" --no-pager | grep -i "ipc message sent"
```

Expected log line:
```
IPC message sent
    chatJid: "<TARGET_JID>"
    sourceGroup: "main"
```

## Security note

The `isMain` flag is derived from the IPC directory path on the host filesystem — not from anything the container writes. Non-main agents cannot impersonate main: if they pass `target_group_jid`, the MCP tool silently ignores it (falls back to `chatJid`). The host authorization check in `ipc.ts` provides a second layer of defense.

## Summary of changed files

| File | Change |
|------|--------|
| `container/agent-runner/src/ipc-mcp-stdio.ts` | Add `target_group_jid` param to `send_message`; resolve `targetJid` in handler |
| `groups/main/CLAUDE.md` | Document "Sending Messages to Other Groups" |
