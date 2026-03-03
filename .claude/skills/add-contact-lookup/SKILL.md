---
name: add-contact-lookup
description: Allow the main group agent to look up WhatsApp contacts by name and get their JID for sending 1-1 messages. Adds a `lookup_contact` MCP tool, a contacts SQLite table populated from message history and live Baileys events, and a contacts.json snapshot in the IPC directory. Triggers on "look up contact", "find contact", "search contacts", "send message to [name]", "contact lookup".
disable-model-invocation: true
---

# Add Contact Lookup

This skill lets the main group agent find a contact's WhatsApp JID by name — e.g. "send a message to Alice" — without knowing their phone number. It stores contact push names from incoming messages into a `contacts` SQLite table and exposes them via a `contacts.json` IPC snapshot and a `lookup_contact` MCP tool.

**What this adds:**
- `contacts` table in SQLite, populated at startup from existing message history and kept live via Baileys events
- LID-to-phone resolution using Baileys auth mapping files (group contacts use LID JIDs internally)
- `lookup_contact` MCP tool (main group only) that searches contacts by name and returns JIDs
- `contacts.json` snapshot written to `/workspace/ipc/` before each main-group agent run
- Always-sync for agent-runner-src (was copy-once) so new tools reach containers immediately

**What stays the same:**
- All other MCP tools — unchanged
- IPC authorization model — unchanged
- Host-side send/receive routing — unchanged

---

## 1. Add contacts table and functions to `src/db.ts`

### 1a. Add the contacts table to the schema

Find the `CREATE TABLE IF NOT EXISTS registered_groups` block inside `createSchema`. Add the contacts table immediately after the closing `);` of `registered_groups`:

**Old (end of `database.exec(...)` template literal):**
```sql
    CREATE TABLE IF NOT EXISTS registered_groups (
      jid TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      folder TEXT NOT NULL UNIQUE,
      trigger_pattern TEXT NOT NULL,
      added_at TEXT NOT NULL,
      container_config TEXT,
      requires_trigger INTEGER DEFAULT 1
    );
  `);
```

**New:**
```sql
    CREATE TABLE IF NOT EXISTS registered_groups (
      jid TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      folder TEXT NOT NULL UNIQUE,
      trigger_pattern TEXT NOT NULL,
      added_at TEXT NOT NULL,
      container_config TEXT,
      requires_trigger INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS contacts (
      jid TEXT PRIMARY KEY,
      name TEXT,
      notify TEXT
    );
  `);
```

### 1b. Call backfill from `initDatabase`

Find the end of `initDatabase()` where `migrateJsonState()` is called:

**Old:**
```typescript
  // Migrate from JSON files if they exist
  migrateJsonState();
}
```

**New:**
```typescript
  // Migrate from JSON files if they exist
  migrateJsonState();

  // Seed contacts table from existing message history (idempotent)
  backfillContactsFromMessages();
}
```

### 1c. Add contact functions

Find the comment `// --- JSON migration ---` and insert the following block immediately before it:

```typescript
// --- Contact accessors ---

/**
 * Resolve a LID JID (e.g. "281411189743777@lid") to a phone JID
 * (e.g. "352621395646@s.whatsapp.net") using Baileys' auth mapping files.
 * Returns the original JID unchanged if no mapping is found.
 */
function resolveLidToPhone(jid: string): string {
  if (!jid.endsWith('@lid')) return jid;
  const lidNumber = jid.split('@')[0].split(':')[0];
  const mappingFile = path.join(
    STORE_DIR,
    'auth',
    `lid-mapping-${lidNumber}_reverse.json`,
  );
  try {
    const phoneNumber: string = JSON.parse(
      fs.readFileSync(mappingFile, 'utf-8'),
    );
    if (phoneNumber) return `${phoneNumber}@s.whatsapp.net`;
  } catch {
    // No mapping found — keep LID as fallback
  }
  return jid;
}

export function upsertContacts(
  contacts: Array<{ id: string; name?: string; notify?: string }>,
): void {
  const stmt = db.prepare(
    `INSERT INTO contacts (jid, name, notify) VALUES (?, ?, ?)
     ON CONFLICT(jid) DO UPDATE SET
       name = COALESCE(excluded.name, name),
       notify = COALESCE(excluded.notify, notify)`,
  );
  const insert = db.transaction(() => {
    for (const c of contacts) {
      if (!c.name && !c.notify) continue;
      const jid = resolveLidToPhone(c.id);
      stmt.run(jid, c.name ?? null, c.notify ?? null);
    }
  });
  insert();
}

export interface ContactInfo {
  jid: string;
  name: string | null;
  notify: string | null;
}

export function getAllContacts(): ContactInfo[] {
  return db
    .prepare(`SELECT jid, name, notify FROM contacts ORDER BY name`)
    .all() as ContactInfo[];
}

/**
 * Backfill the contacts table from stored message history.
 * Reads sender/sender_name pairs from the messages table and upserts them.
 * Safe to call on every startup — upsert is idempotent.
 */
export function backfillContactsFromMessages(): void {
  const rows = db
    .prepare(
      `SELECT DISTINCT sender AS id, sender_name AS notify
       FROM messages
       WHERE is_from_me = 0
         AND sender_name IS NOT NULL AND sender_name != ''
         AND sender_name NOT LIKE '%@%'`,
    )
    .all() as Array<{ id: string; notify: string }>;
  if (rows.length > 0) {
    upsertContacts(rows);
  }
}

```

---

## 2. Add `OnContactsUpdate` type to `src/types.ts`

Find the `OnInboundMessage` type export and insert the new type immediately after it:

**Old:**
```typescript
// Callback type that channels use to deliver inbound messages
export type OnInboundMessage = (chatJid: string, message: NewMessage) => void;

// Callback for chat metadata discovery.
```

**New:**
```typescript
// Callback type that channels use to deliver inbound messages
export type OnInboundMessage = (chatJid: string, message: NewMessage) => void;

// Callback for contact data received from WhatsApp
export type OnContactsUpdate = (
  contacts: Array<{ id: string; name?: string; notify?: string }>,
) => void;

// Callback for chat metadata discovery.
```

---

## 3. Update `src/channels/whatsapp.ts`

### 3a. Import `OnContactsUpdate`

Find the import block from `'../types.js'`:

**Old:**
```typescript
import {
  Channel,
  OnInboundMessage,
  OnChatMetadata,
  RegisteredGroup,
} from '../types.js';
```

**New:**
```typescript
import {
  Channel,
  OnInboundMessage,
  OnChatMetadata,
  OnContactsUpdate,
  RegisteredGroup,
} from '../types.js';
```

### 3b. Add `onContactsUpdate` to `WhatsAppChannelOpts`

**Old:**
```typescript
export interface WhatsAppChannelOpts {
  onMessage: OnInboundMessage;
  onChatMetadata: OnChatMetadata;
  registeredGroups: () => Record<string, RegisteredGroup>;
}
```

**New:**
```typescript
export interface WhatsAppChannelOpts {
  onMessage: OnInboundMessage;
  onChatMetadata: OnChatMetadata;
  onContactsUpdate?: OnContactsUpdate;
  registeredGroups: () => Record<string, RegisteredGroup>;
}
```

### 3c. Add contact event listeners

Find `this.sock.ev.on('creds.update', saveCreds);` inside `connectInternal`. Insert the three listeners immediately after it:

**Old:**
```typescript
    this.sock.ev.on('creds.update', saveCreds);

    this.sock.ev.on('messages.upsert', async ({ messages }) => {
```

**New:**
```typescript
    this.sock.ev.on('creds.update', saveCreds);

    this.sock.ev.on('messaging-history.set', ({ contacts }) => {
      if (contacts.length > 0) {
        this.opts.onContactsUpdate?.(contacts);
      }
    });

    this.sock.ev.on('contacts.upsert', (contacts) => {
      if (contacts.length > 0) {
        this.opts.onContactsUpdate?.(contacts);
      }
    });

    this.sock.ev.on('contacts.update', (updates) => {
      const contacts = updates.filter(
        (u): u is { id: string; name?: string; notify?: string } =>
          typeof u.id === 'string' && (!!u.name || !!u.notify),
      );
      if (contacts.length > 0) {
        this.opts.onContactsUpdate?.(contacts);
      }
    });

    this.sock.ev.on('messages.upsert', async ({ messages }) => {
```

---

## 4. Update `src/container-runner.ts`

### 4a. Always sync agent-runner-src (was copy-once)

Find the agent-runner source copy block:

**Old:**
```typescript
  // Copy agent-runner source into a per-group writable location so agents
  // can customize it (add tools, change behavior) without affecting other
  // groups. Recompiled on container startup via entrypoint.sh.
  const agentRunnerSrc = path.join(
    projectRoot,
    'container',
    'agent-runner',
    'src',
  );
  const groupAgentRunnerDir = path.join(
    DATA_DIR,
    'sessions',
    group.folder,
    'agent-runner-src',
  );
  if (!fs.existsSync(groupAgentRunnerDir) && fs.existsSync(agentRunnerSrc)) {
    fs.cpSync(agentRunnerSrc, groupAgentRunnerDir, { recursive: true });
  }
```

**New:**
```typescript
  // Sync agent-runner source into a per-group writable location.
  // Always overwrite so every container run gets the latest tool definitions.
  // Recompiled on container startup via entrypoint.sh.
  const agentRunnerSrc = path.join(
    projectRoot,
    'container',
    'agent-runner',
    'src',
  );
  const groupAgentRunnerDir = path.join(
    DATA_DIR,
    'sessions',
    group.folder,
    'agent-runner-src',
  );
  if (fs.existsSync(agentRunnerSrc)) {
    fs.cpSync(agentRunnerSrc, groupAgentRunnerDir, { recursive: true });
  }
```

### 4b. Add `writeContactsSnapshot`

Find `export interface AvailableGroup {` and insert the following function immediately before it:

```typescript
export function writeContactsSnapshot(
  groupFolder: string,
  contacts: Array<{ jid: string; name: string | null; notify: string | null }>,
): void {
  const groupIpcDir = resolveGroupIpcPath(groupFolder);
  fs.mkdirSync(groupIpcDir, { recursive: true });
  fs.writeFileSync(
    path.join(groupIpcDir, 'contacts.json'),
    JSON.stringify(contacts, null, 2),
  );
}

```

---

## 5. Update `src/index.ts`

### 5a. Import `writeContactsSnapshot`

Find the import block from `'./container-runner.js'`:

**Old:**
```typescript
import {
  ContainerOutput,
  runContainerAgent,
  writeGroupsSnapshot,
  writeTasksSnapshot,
} from './container-runner.js';
```

**New:**
```typescript
import {
  ContainerOutput,
  runContainerAgent,
  writeContactsSnapshot,
  writeGroupsSnapshot,
  writeTasksSnapshot,
} from './container-runner.js';
```

### 5b. Import contact DB functions

Find the import block from `'./db.js'`. Add `getAllContacts` and `upsertContacts`:

**Old:**
```typescript
import {
  deleteRegisteredGroup,
  deleteSession,
  getAllChats,
  getAllRegisteredGroups,
```

**New:**
```typescript
import {
  deleteRegisteredGroup,
  deleteSession,
  getAllChats,
  getAllContacts,
  getAllRegisteredGroups,
```

And add `upsertContacts` to the same block (near the end, before the closing `}`):

**Old:**
```typescript
  storeChatMetadata,
  storeMessage,
} from './db.js';
```

**New:**
```typescript
  storeChatMetadata,
  storeMessage,
  upsertContacts,
} from './db.js';
```

### 5c. Add `onContactsUpdate` to `channelOpts`

Find the `channelOpts` object in `main()`:

**Old:**
```typescript
  const channelOpts = {
    onMessage: (_chatJid: string, msg: NewMessage) => storeMessage(msg),
    onChatMetadata: (
      chatJid: string,
      timestamp: string,
      name?: string,
      channel?: string,
      isGroup?: boolean,
    ) => storeChatMetadata(chatJid, timestamp, name, channel, isGroup),
    registeredGroups: () => registeredGroups,
  };
```

**New:**
```typescript
  const channelOpts = {
    onMessage: (_chatJid: string, msg: NewMessage) => storeMessage(msg),
    onChatMetadata: (
      chatJid: string,
      timestamp: string,
      name?: string,
      channel?: string,
      isGroup?: boolean,
    ) => storeChatMetadata(chatJid, timestamp, name, channel, isGroup),
    onContactsUpdate: (
      contacts: Array<{ id: string; name?: string; notify?: string }>,
    ) => upsertContacts(contacts),
    registeredGroups: () => registeredGroups,
  };
```

### 5d. Write contacts snapshot in `runAgent`

Find the `writeGroupsSnapshot` call inside `runAgent`. Insert the contacts snapshot write immediately after it:

**Old:**
```typescript
  // Update available groups snapshot (main group only can see all groups)
  const availableGroups = getAvailableGroups();
  writeGroupsSnapshot(
    group.folder,
    isMain,
    availableGroups,
    new Set(Object.keys(registeredGroups)),
  );

  // Wrap onOutput to track session ID from streamed results
```

**New:**
```typescript
  // Update available groups snapshot (main group only can see all groups)
  const availableGroups = getAvailableGroups();
  writeGroupsSnapshot(
    group.folder,
    isMain,
    availableGroups,
    new Set(Object.keys(registeredGroups)),
  );

  // Write contacts snapshot (main group only)
  if (isMain) {
    const contacts = getAllContacts();
    writeContactsSnapshot(group.folder, contacts);
  }

  // Wrap onOutput to track session ID from streamed results
```

---

## 6. Add `lookup_contact` MCP tool to `container/agent-runner/src/ipc-mcp-stdio.ts`

Find the comment `// Start the stdio transport` near the bottom of the file. Insert the following tool immediately before it:

```typescript
server.tool(
  'lookup_contact',
  'Look up a WhatsApp contact by name to get their JID for sending messages. Returns matching contacts. Then use send_message with the found JID. Main group only.',
  {
    name: z.string().describe('Name or partial name to search for (case-insensitive)'),
  },
  async (args) => {
    if (!isMain) {
      return {
        content: [{ type: 'text' as const, text: 'lookup_contact is only available from the main group.' }],
        isError: true,
      };
    }

    const contactsFile = path.join(IPC_DIR, 'contacts.json');
    if (!fs.existsSync(contactsFile)) {
      return { content: [{ type: 'text' as const, text: 'No contacts available yet. Try again after WhatsApp syncs.' }] };
    }

    const contacts: Array<{ jid: string; name: string | null; notify: string | null }> =
      JSON.parse(fs.readFileSync(contactsFile, 'utf-8'));

    const query = args.name.toLowerCase();
    const matches = contacts.filter(
      (c) =>
        c.name?.toLowerCase().includes(query) ||
        c.notify?.toLowerCase().includes(query),
    );

    if (matches.length === 0) {
      return { content: [{ type: 'text' as const, text: `No contacts found matching "${args.name}".` }] };
    }

    const formatted = matches
      .map((c) => {
        const displayName = c.name || c.notify;
        const notifyPart = c.notify && c.notify !== c.name ? `, known as "${c.notify}"` : '';
        return `- ${displayName}${notifyPart} (JID: ${c.jid})`;
      })
      .join('\n');

    return { content: [{ type: 'text' as const, text: `Matching contacts:\n${formatted}` }] };
  },
);

```

---

## 7. Build and verify

```bash
npm run build
```

Build must be clean (no TypeScript errors).

### Verify contacts are populated

After restarting NanoClaw, the startup backfill runs automatically:

```bash
systemctl --user restart nanoclaw
node -e "
const DB = require('./node_modules/better-sqlite3');
const db = new DB('store/messages.db');
console.log('Contacts:', db.prepare('SELECT * FROM contacts ORDER BY notify').all());
"
```

Expect to see contacts with names populated from existing message history. Contacts whose senders were LID JIDs will be resolved to phone number JIDs via `store/auth/lid-mapping-*_reverse.json`.

### Test the lookup tool

Trigger an agent run from the main group, then ask it to look up a contact by name. The agent should call `mcp__nanoclaw__lookup_contact` and return a JID that can be passed directly to `mcp__nanoclaw__send_message`.

---

## Notes

**LID JIDs:** WhatsApp group messages use LID (Linked ID) JIDs internally (e.g. `281411189743777@lid`). This skill resolves them to phone JIDs (e.g. `352621395646@s.whatsapp.net`) using Baileys' auth mapping files at `store/auth/lid-mapping-{lid}_reverse.json`. Contacts without a mapping file keep their LID JID as a fallback.

**Contacts that still show LID JIDs** will be resolved automatically once they send any message (the `contacts.update` event fires with their JID and name on every incoming message).

**No container rebuild needed:** The `lookup_contact` tool runs inside the container's agent-runner, which is recompiled from source on every container start. The always-sync change (step 4a) ensures new tool definitions reach the container without a Docker rebuild.

---

## Summary of changed files

| File | Change |
|------|--------|
| `src/db.ts` | Add `contacts` table; `resolveLidToPhone()`; `upsertContacts()`; `getAllContacts()`; `backfillContactsFromMessages()` called from `initDatabase()` |
| `src/types.ts` | Add `OnContactsUpdate` callback type |
| `src/channels/whatsapp.ts` | Add `onContactsUpdate` to opts; listen to `messaging-history.set`, `contacts.upsert`, `contacts.update` |
| `src/container-runner.ts` | Always-sync agent-runner-src (was copy-once); add `writeContactsSnapshot()` |
| `src/index.ts` | Import new functions; wire `onContactsUpdate` callback; call `writeContactsSnapshot` in `runAgent` |
| `container/agent-runner/src/ipc-mcp-stdio.ts` | Add `lookup_contact` MCP tool |
