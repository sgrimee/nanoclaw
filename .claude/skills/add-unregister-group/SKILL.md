---
name: add-unregister-group
description: Add an unregister_group MCP tool so the main group agent can completely remove a group from NanoClaw via a WhatsApp command. The group stops receiving messages immediately; its files are preserved. Triggers on "unregister group", "remove group", "delete group", "stop responding to group".
disable-model-invocation: true
---

# Add Unregister Group Tool

This skill adds `mcp__nanoclaw__unregister_group` to the main group agent. The main agent can call it to remove any registered group from the database, stopping message processing for that group immediately. The group folder and its files are preserved on disk.

**What this adds:**
- `deleteRegisteredGroup(jid)` DB function in `src/db.ts`
- `unregisterGroup` callback in `IpcDeps` and a matching handler in `src/ipc.ts`
- `unregisterGroup()` orchestrator function in `src/index.ts`, wired into `startIpcWatcher`
- `unregister_group` MCP tool in `container/agent-runner/src/ipc-mcp-stdio.ts`
- Updated "Removing a Group" docs in `groups/main/CLAUDE.md`

**What stays the same:**
- Group folder and files — untouched
- All other MCP tools — unchanged
- IPC authorization model — unchanged (main-only, same pattern as `register_group`)

---

## 1. Add `deleteRegisteredGroup` to `src/db.ts`

Find `export function getAllRegisteredGroups()` and insert the following function immediately before it:

```typescript
export function deleteRegisteredGroup(jid: string): void {
  db.prepare('DELETE FROM registered_groups WHERE jid = ?').run(jid);
}
```

---

## 2. Update `src/ipc.ts`

### 2a. Import `deleteRegisteredGroup`

Find the import block that imports from `'./db.js'`. Add `deleteRegisteredGroup` to it:

**Old:**
```typescript
import {
  createTask,
  deleteTask,
```

**New:**
```typescript
import {
  createTask,
  deleteRegisteredGroup,
  deleteTask,
```

### 2b. Add `unregisterGroup` to `IpcDeps`

Find the `IpcDeps` interface. Add the new field before the `pipeToActiveContainer` comment:

**Old:**
```typescript
  /** Try to pipe a message to an active container. Returns true if sent. */
  pipeToActiveContainer?: (chatJid: string, message: string) => boolean;
```

**New:**
```typescript
  unregisterGroup: (jid: string) => void;
  /** Try to pipe a message to an active container. Returns true if sent. */
  pipeToActiveContainer?: (chatJid: string, message: string) => boolean;
```

### 2c. Add `unregister_group` IPC handler

In `processTaskIpc`, find the `case 'calendar_sync':` block and insert the following case immediately before it:

```typescript
    case 'unregister_group':
      // Only main group can unregister groups
      if (!isMain) {
        logger.warn(
          { sourceGroup },
          'Unauthorized unregister_group attempt blocked',
        );
        break;
      }
      if (data.jid) {
        if (!registeredGroups[data.jid]) {
          logger.warn(
            { jid: data.jid },
            'unregister_group: JID not found in registered groups',
          );
          break;
        }
        deps.unregisterGroup(data.jid);
        logger.info(
          { jid: data.jid, sourceGroup },
          'Group unregistered via IPC',
        );
      } else {
        logger.warn({ data }, 'Invalid unregister_group request - missing jid');
      }
      break;

```

### 2d. Update the `data` parameter type (optional, for clarity)

In `processTaskIpc`, find the comment on the `jid` field of the data parameter:

**Old:**
```typescript
    // For register_group
    jid?: string;
```

**New:**
```typescript
    // For register_group / unregister_group
    jid?: string;
```

---

## 3. Update `src/index.ts`

### 3a. Import `deleteRegisteredGroup`

Find the import block from `'./db.js'`. Add `deleteRegisteredGroup` to it:

**Old:**
```typescript
import {
  deleteSession,
```

**New:**
```typescript
import {
  deleteRegisteredGroup,
  deleteSession,
```

### 3b. Add `unregisterGroup` function

Find the closing brace of `registerGroup()`. Add the following function immediately after it:

```typescript
function unregisterGroup(jid: string): void {
  const group = registeredGroups[jid];
  deleteRegisteredGroup(jid);
  delete registeredGroups[jid];
  logger.info(
    { jid, name: group?.name, folder: group?.folder },
    'Group unregistered',
  );
}
```

### 3c. Wire into `startIpcWatcher`

Find the `startIpcWatcher({...})` call. Add `unregisterGroup` after `registerGroup`:

**Old:**
```typescript
    registeredGroups: () => registeredGroups,
    registerGroup,
    syncGroupMetadata: (force) =>
```

**New:**
```typescript
    registeredGroups: () => registeredGroups,
    registerGroup,
    unregisterGroup,
    syncGroupMetadata: (force) =>
```

---

## 4. Add the MCP tool to `container/agent-runner/src/ipc-mcp-stdio.ts`

Find the comment `// Start the stdio transport` near the bottom of the file. Insert the following `server.tool(...)` call immediately before it:

```typescript
server.tool(
  'unregister_group',
  'Unregister a WhatsApp group so the agent stops responding to messages there. Main group only. The group folder and its files are kept intact.',
  {
    jid: z.string().describe('The WhatsApp JID of the group to unregister (e.g., "120363336345536173@g.us")'),
    name: z.string().describe('Display name of the group (for confirmation in logs)'),
  },
  async (args) => {
    if (!isMain) {
      return {
        content: [{ type: 'text' as const, text: 'Only the main group can unregister groups.' }],
        isError: true,
      };
    }

    const data = {
      type: 'unregister_group',
      jid: args.jid,
      name: args.name,
      timestamp: new Date().toISOString(),
    };

    writeIpcFile(TASKS_DIR, data);

    return {
      content: [{ type: 'text' as const, text: `Group "${args.name}" unregistration requested. It will stop receiving messages shortly. Group files are preserved.` }],
    };
  },
);

```

---

## 5. Update `groups/main/CLAUDE.md`

Find the "### Removing a Group" section and replace its content:

**Old:**
```markdown
### Removing a Group

1. Read `/workspace/project/data/registered_groups.json`
2. Remove the entry for that group
3. Write the updated JSON back
4. The group folder and its files remain (don't delete them)

### Listing Groups

Read `/workspace/project/data/registered_groups.json` and format it nicely.
```

**New:**
```markdown
### Removing a Group

Use the `unregister_group` MCP tool:

```
mcp__nanoclaw__unregister_group(jid="120363336345536173@g.us", name="Testing")
```

Find the JID from `/workspace/ipc/available_groups.json` (filter by `isRegistered: true`) or query the database. The group folder and its files are preserved.

### Listing Groups

Read `/workspace/ipc/available_groups.json` (filter by `isRegistered: true`) or query the database directly:

```bash
sqlite3 /workspace/project/store/messages.db "SELECT jid, name, folder, trigger_pattern FROM registered_groups;"
```
```

---

## 6. Update `src/ipc-auth.test.ts`

Find the mock `deps` object in `beforeEach`. Add `unregisterGroup` after `registerGroup`:

**Old:**
```typescript
    registerGroup: (jid, group) => {
      groups[jid] = group;
      setRegisteredGroup(jid, group);
      // Mock the fs.mkdirSync that registerGroup does
    },
    syncGroupMetadata: async () => {},
```

**New:**
```typescript
    registerGroup: (jid, group) => {
      groups[jid] = group;
      setRegisteredGroup(jid, group);
      // Mock the fs.mkdirSync that registerGroup does
    },
    unregisterGroup: (jid) => {
      delete groups[jid];
    },
    syncGroupMetadata: async () => {},
```

---

## 7. Build and verify

```bash
npm run build
./container/build.sh
```

Both must succeed. If `npm run build` fails with a missing `unregisterGroup` property, check the test file update in step 6.

---

## 8. Verify the feature

Write a test IPC file as the main group and confirm the target is removed from the database:

```bash
# 1. Note the current registered groups
node -e "const Database = require('./node_modules/better-sqlite3'); const db = new Database('store/messages.db'); console.log(db.prepare('SELECT jid, name FROM registered_groups').all());"

# 2. Write the IPC file
node -e "
const fs = require('fs'), path = require('path');
const dir = 'data/ipc/main/tasks';
fs.mkdirSync(dir, { recursive: true });
const file = path.join(dir, Date.now() + '-unreg-test.json');
const tmp = file + '.tmp';
fs.writeFileSync(tmp, JSON.stringify({
  type: 'unregister_group',
  jid: '<TARGET_JID>',
  name: '<GROUP_NAME>',
  timestamp: new Date().toISOString()
}));
fs.renameSync(tmp, file);
console.log('Written:', file);
"

# 3. Wait ~2 seconds, then check it was consumed and removed from DB
node -e "const Database = require('./node_modules/better-sqlite3'); const db = new Database('store/messages.db'); console.log(db.prepare('SELECT jid, name FROM registered_groups').all());"
```

Check logs:
```bash
journalctl --user -u nanoclaw --since "30 seconds ago" --no-pager | grep -i "unregistered"
```

Expected log line:
```
Group unregistered via IPC
    jid: "<TARGET_JID>"
    sourceGroup: "main"
```

---

## Summary of changed files

| File | Change |
|------|--------|
| `src/db.ts` | Add `deleteRegisteredGroup(jid)` |
| `src/ipc.ts` | Import `deleteRegisteredGroup`; add `unregisterGroup` to `IpcDeps`; add `unregister_group` IPC handler |
| `src/index.ts` | Import `deleteRegisteredGroup`; add `unregisterGroup()` function; wire into `startIpcWatcher` |
| `src/ipc-auth.test.ts` | Add `unregisterGroup` mock to test deps |
| `container/agent-runner/src/ipc-mcp-stdio.ts` | Add `unregister_group` MCP tool |
| `groups/main/CLAUDE.md` | Update "Removing a Group" and "Listing Groups" sections |
