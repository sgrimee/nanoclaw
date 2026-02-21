---
name: add-clear-command
description: Add a /clear command to reset conversation context without losing files or memory. Use when user wants to add context reset functionality, clear command, or fresh session feature. Triggers on "clear command", "reset context", "clear conversation", or "add /clear".
disable-model-invocation: true
---

# Add /clear Command

This skill adds a `/clear` command that allows users to reset their conversation context while preserving all files, memory (CLAUDE.md), and documents.

**What this adds:**
- `/clear` command to delete current session and start fresh
- `/clear <prompt>` to reset context and immediately process a new prompt
- Confirmation message when context is cleared
- Documentation in CLAUDE.md files

**What stays the same:**
- All CLAUDE.md files remain accessible
- All documents and workspace files are preserved
- Calendar, tasks, and other data unchanged
- Only the conversation transcript is cleared

## Use Cases

- Context becomes too long or confusing
- Mixing old conversations with new ones
- Want to start fresh without historical context
- Testing with clean slate
- Separating different topics/tasks

## 1. Add Database Function

Edit `src/db.ts`:

### 1a. Add deleteSession function

After the `getAllSessions()` function (around line 472), add:

```typescript
export function deleteSession(groupFolder: string): void {
  db.prepare('DELETE FROM sessions WHERE group_folder = ?').run(groupFolder);
}
```

This function removes the session ID from the database for a specific group.

## 2. Update Index to Import Function

Edit `src/index.ts`:

### 2a. Add deleteSession to imports

Find the import block from './db.js' (around line 20-34) and add `deleteSession` to the list:

```typescript
import {
  deleteSession,  // Add this line
  getAllChats,
  getAllRegisteredGroups,
  getAllSessions,
  getAllTasks,
  getMessagesSince,
  getNewMessages,
  getRouterState,
  initDatabase,
  setRegisteredGroup,
  setRouterState,
  setSession,
  storeChatMetadata,
  storeMessage,
} from './db.js';
```

## 3. Add Command Detection Logic

Edit `src/index.ts`:

### 3a. Add /clear detection in processGroupMessages

Find the section in `processGroupMessages()` after the trigger check (around line 134-144) and before `const prompt = formatMessages(missedMessages);`.

Insert this block:

```typescript
  // Check if the last message contains /clear command
  const lastMessage = missedMessages[missedMessages.length - 1];
  const clearMatch = lastMessage.content.match(/^(.*?)\/clear\s*([\s\S]*)$/i);

  if (clearMatch) {
    // Clear the session
    delete sessions[group.folder];
    deleteSession(group.folder);
    logger.info({ group: group.name }, 'Session cleared by user command');

    // Extract the remaining prompt after /clear (if any)
    const remainingPrompt = clearMatch[2].trim();

    if (remainingPrompt) {
      // Replace the last message content with the remaining prompt
      missedMessages[missedMessages.length - 1] = {
        ...lastMessage,
        content: remainingPrompt,
      };
    } else {
      // If no prompt after /clear, send confirmation and return
      await whatsapp.sendMessage(
        chatJid,
        `${ASSISTANT_NAME}: ✅ Context cleared! Starting fresh conversation. All files and memory (CLAUDE.md, documents) are still accessible.`,
      );

      // Update cursor to mark this message as processed
      lastAgentTimestamp[chatJid] = lastMessage.timestamp;
      saveState();
      return true;
    }
  }

  const prompt = formatMessages(missedMessages);
```

**How it works:**
- Detects `/clear` anywhere in the last message (before or after trigger)
- Deletes the session from both memory and database
- If text follows `/clear`, it becomes the new prompt with fresh context
- If `/clear` is alone, sends confirmation and exits

## 4. Update Documentation

### 4a. Update main group CLAUDE.md

Add to the top of `/workspace/project/groups/main/CLAUDE.md` (after the "Admin Context" section):

```markdown
## Commands

### /clear - Reset Conversation Context

Clear the conversation history and start with a fresh context while keeping all files and memory intact.

**Usage:**
```
/clear
```
or
```
/clear What's the weather today?
```

- Deletes the current session ID to start fresh
- All CLAUDE.md files, documents, and local files remain accessible
- Useful when the context gets confusing or mixes old conversations
- Can include a new prompt after `/clear` in the same message

**Example:**
```
/clear Help me plan tomorrow's meetings
```

This clears the context, then immediately processes "Help me plan tomorrow's meetings" with a fresh session.
```

### 4b. Update global CLAUDE.md

Add to `/workspace/project/groups/global/CLAUDE.md` (after "What You Can Do" section):

```markdown
## Commands

### /clear - Reset Context

Users can type `/clear` to reset the conversation context and start fresh. This:
- Deletes the current session ID
- Starts a new conversation with clean context
- Keeps all CLAUDE.md files, documents, and workspace files accessible
- Can be combined with a prompt: `/clear <new prompt>`

Example: `/clear What's the weather today?`

When you see `/clear` has been used, you'll start with a fresh session but still have access to all files and memory.
```

## 5. Build and Test

After making all changes:

```bash
# Compile TypeScript
npm run build

# Restart nanoclaw (if running as systemd service)
sudo systemctl restart nanoclaw

# Or restart manually
# Kill the current process and start again:
npm run dev
```

## 6. Verify the Feature

### 6a. Test basic /clear

Send via WhatsApp:
```
@AssistantName /clear
```

Expected response:
```
AssistantName: ✅ Context cleared! Starting fresh conversation. All files and memory (CLAUDE.md, documents) are still accessible.
```

### 6b. Test /clear with prompt

Send via WhatsApp:
```
@AssistantName /clear What's the weather today?
```

Expected: Context clears, then assistant responds to weather question with fresh context (no reference to previous conversation).

### 6c. Test files remain accessible

1. Create a test file: `echo "test data" > /workspace/group/test.txt`
2. Send: `@AssistantName Read test.txt`
3. Send: `@AssistantName /clear Read test.txt again`
4. Verify: File is still readable after context clear

### 6d. Test in different groups

Test in both main group and a secondary group to ensure it works across all contexts.

## Troubleshooting

**Compilation errors:**
- Check that `deleteSession` is properly exported in `src/db.ts`
- Verify the import statement in `src/index.ts` includes `deleteSession`
- Run `npm run build` to see specific TypeScript errors

**Command not detected:**
- Verify the regex pattern matches your trigger format
- Check logs with `journalctl -u nanoclaw -f` (if systemd) or console output
- The pattern should match: `@Trigger /clear` or `/clear` or `@Trigger /clear prompt`

**/clear runs but context not cleared:**
- Check database: `sqlite3 /workspace/project/store/messages.db "SELECT * FROM sessions;"`
- Verify session was deleted after `/clear`
- Check that `sessions[group.folder]` is properly deleted in memory

**Confirmation message not sent:**
- Ensure `whatsapp.sendMessage()` is awaited
- Check that `ASSISTANT_NAME` constant is defined
- Verify the return statement executes after sending confirmation

## Summary of Changed Files

| File | Type of Change |
|------|----------------|
| `src/db.ts` | Added `deleteSession()` function |
| `src/index.ts` | Import `deleteSession`, add `/clear` detection logic |
| `groups/main/CLAUDE.md` | Added command documentation |
| `groups/global/CLAUDE.md` | Added command documentation |

## Examples

**Clear without prompt:**
```
User: @Andy /clear
Andy: ✅ Context cleared! Starting fresh conversation. All files and memory (CLAUDE.md, documents) are still accessible.
```

**Clear with prompt:**
```
User: @Andy /clear What's the capital of France?
Andy: The capital of France is Paris.
```
(Note: No reference to any previous conversation context)

**Mixed with trigger:**
```
User: @Andy hey can you /clear and then tell me about the weather
Andy: [responds about weather with fresh context]
```

The command is flexible and works with various message formats!
