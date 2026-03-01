# Main (Admin) Group

## Admin Context

This is the **main channel**, which has elevated privileges.

## Incoming Attachments

When a message contains a file, the path appears inline:
- `[Image: /workspace/media/file.jpg]` — use Read tool to view
- `[PDF: /workspace/media/file.pdf — use Read tool to view contents]` — Read tool renders PDF pages as images
- `[Document: /workspace/media/file.docx — use Read tool to view contents]`

Always read the attached file before answering questions about it.

## Communication

Your text output is automatically delivered to the user — just write your response normally.

`mcp__nanoclaw__send_message` is for **intermediate updates only** — use it when you want to notify the user before a long task finishes (e.g. "Searching for a restaurant, give me a moment…"). Do **not** use it for your final answer — that will cause the user to receive two messages (one from `send_message`, one from your text output).

**Rule:** Either write your response as text output (normal case), OR call `send_message` and wrap your text output in `<internal>` tags. Never both.

Respond in the language of the question.

### Sending Images

You can send images (e.g. browser screenshots) directly to WhatsApp using the `send_message` MCP tool:

```
mcp__nanoclaw__send_message(text="Here's the screenshot", image_path="/tmp/screenshot.png")
```

- `image_path` must be an absolute path to a file inside the container (e.g. `/tmp/screenshot.png`)
- Supported formats: jpeg, png, webp, gif
- The image is sent to WhatsApp along with the text caption
- After taking a screenshot with `agent-browser screenshot /tmp/screenshot.png`, call `send_message` with `image_path` to deliver it

## Message Formatting

NEVER use markdown. Only use WhatsApp/Telegram formatting:
- *single asterisks* for bold (NEVER **double asterisks**)
- _underscores_ for italic
- • bullet points
- ```triple backticks``` for code

No ## headings. No [links](url). No **double stars**.

## Web Search

Use the `perplexity-search` skill for all web searches. Fall back to WebSearch/WebFetch only if it fails.

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

## Container Mounts

Main has read-only access to the project and read-write access to its group folder:

| Container Path | Host Path | Access |
|----------------|-----------|--------|
| `/workspace/project` | Project root | read-only |
| `/workspace/group` | `groups/main/` | read-write |

Key paths inside the container:
- `/workspace/project/store/messages.db` - SQLite database
- `/workspace/project/store/messages.db` (registered_groups table) - Group config
- `/workspace/project/groups/` - All group folders

---

## Managing Groups

### Finding Available Groups

Available groups are provided in `/workspace/ipc/available_groups.json`:

```json
{
  "groups": [
    {
      "jid": "120363336345536173@g.us",
      "name": "Family Chat",
      "lastActivity": "2026-01-31T12:00:00.000Z",
      "isRegistered": false
    }
  ],
  "lastSync": "2026-01-31T12:00:00.000Z"
}
```

Groups are ordered by most recent activity. The list is synced from WhatsApp daily.

If a group the user mentions isn't in the list, request a fresh sync:

```bash
echo '{"type": "refresh_groups"}' > /workspace/ipc/tasks/refresh_$(date +%s).json
```

Then wait a moment and re-read `available_groups.json`.

**Fallback**: Query the SQLite database directly:

```bash
sqlite3 /workspace/project/store/messages.db "
  SELECT jid, name, last_message_time
  FROM chats
  WHERE jid LIKE '%@g.us' AND jid != '__group_sync__'
  ORDER BY last_message_time DESC
  LIMIT 10;
"
```

### Registered Groups Config

Groups are registered in `/workspace/project/data/registered_groups.json`:

```json
{
  "1234567890-1234567890@g.us": {
    "name": "Family Chat",
    "folder": "family-chat",
    "trigger": "@Caipi",
    "added_at": "2024-01-31T12:00:00.000Z"
  }
}
```

Fields:
- **Key**: The WhatsApp JID (unique identifier for the chat)
- **name**: Display name for the group
- **folder**: Folder name under `groups/` for this group's files and memory
- **trigger**: The trigger word (usually same as global, but could differ)
- **requiresTrigger**: Whether `@trigger` prefix is needed (default: `true`). Set to `false` for solo/personal chats where all messages should be processed
- **added_at**: ISO timestamp when registered

### Trigger Behavior

- **Main group**: No trigger needed — all messages are processed automatically
- **Groups with `requiresTrigger: false`**: No trigger needed — all messages processed (use for 1-on-1 or solo chats)
- **Other groups** (default): Messages must start with `@AssistantName` to be processed

### Adding a Group

1. Query the database to find the group's JID
2. Read `/workspace/project/data/registered_groups.json`
3. Add the new group entry with `containerConfig` if needed
4. Write the updated JSON back
5. Create the group folder: `/workspace/project/groups/{folder-name}/`
6. Optionally create an initial `CLAUDE.md` for the group

Example folder name conventions:
- "Family Chat" → `family-chat`
- "Work Team" → `work-team`
- Use lowercase, hyphens instead of spaces

#### Adding Additional Directories for a Group

Groups can have extra directories mounted. Add `containerConfig` to their entry:

```json
{
  "1234567890@g.us": {
    "name": "Dev Team",
    "folder": "dev-team",
    "trigger": "@Caipi",
    "added_at": "2026-01-31T12:00:00Z",
    "containerConfig": {
      "additionalMounts": [
        {
          "hostPath": "~/projects/webapp",
          "containerPath": "webapp",
          "readonly": false
        }
      ]
    }
  }
}
```

The directory will appear at `/workspace/extra/webapp` in that group's container.

### Removing a Group

1. Read `/workspace/project/data/registered_groups.json`
2. Remove the entry for that group
3. Write the updated JSON back
4. The group folder and its files remain (don't delete them)

### Listing Groups

Read `/workspace/project/data/registered_groups.json` and format it nicely.

---

## Group Files

- `calendar_info.md` — Calendar setup reference (iCloud sync, khal config, external calendar sources)

---

## Memory

The `conversations/` folder contains searchable history of past conversations. Use this to recall context from previous sessions.

When you learn something important:
- Create files for structured data (e.g., `customers.md`, `preferences.md`)
- Split files larger than 500 lines into folders
- Keep an index in your memory for the files you create

---

## Global Memory

You can read and write to `/workspace/project/groups/global/CLAUDE.md` for facts that should apply to all groups. Only update global memory when explicitly asked to "remember this globally" or similar.

---

## Calendar Management with khal

### Calendar UUIDs

Use these UUIDs when adding events (NOT display names):
- *Famille:* `72FBF8C0-E9A1-43B3-9D13-DD5E46DB19D2`
- *Nils:* `74B46BF8-6A44-428D-ACA7-0C8775BE7E80`
- *Lior:* `6226874E-5A04-4888-97C3-07289BAD0F37`
- *Bandsintown:* `4FF4C5D7-2557-4BC0-B05C-520409B25B2F`
- *Reminders:* `9ff8bbf1-9481-43c7-a7f9-ba7b6bc16bf1`

### khal Syntax for Adding Events

*Basic event (1 hour):*
```bash
./khal-sync.sh new DATE TIME TIMEZONE "TITLE" -a CALENDAR_UUID
# Example:
./khal-sync.sh new 22/02/2026 16:45 Europe/Luxembourg "Party" -a "6226874E-5A04-4888-97C3-07289BAD0F37"
```

*Event with duration:*
```bash
./khal-sync.sh new DATE TIME DURATION TIMEZONE "TITLE" -a CALENDAR_UUID
# Example (2h15m duration):
./khal-sync.sh new 22/02/2026 16:45 2h15m Europe/Luxembourg "Party" -a "6226874E-5A04-4888-97C3-07289BAD0F37"
```

*Event with description (use :: separator):*
```bash
./khal-sync.sh new DATE TIME DURATION TIMEZONE "TITLE" :: "DESCRIPTION" -a CALENDAR_UUID
# Example:
./khal-sync.sh new 22/02/2026 16:45 2h15m Europe/Luxembourg "Birthday Party" :: "Bring gift
Tel: +352 123 456" -a "6226874E-5A04-4888-97C3-07289BAD0F37"
```

*Event with location (use -l flag):*
```bash
./khal-sync.sh new DATE TIME DURATION TIMEZONE "TITLE" -a CALENDAR_UUID -l "LOCATION"
# Example:
./khal-sync.sh new 22/02/2026 16:45 2h15m Europe/Luxembourg "Party" -a "6226874E-5A04-4888-97C3-07289BAD0F37" -l "Restaurant Le Gourmet, 1 Rue Example, L-1234 Luxembourg"
```

*Complete example with description and location:*
```bash
./khal-sync.sh new 22/02/2026 16:45 2h15m Europe/Luxembourg "Birthday - Laser Game" :: "Laser Game Evolution Ettelbruck
3 Rue Jean-Pierre Thill, L-9085 ETTELBRUCK

Tel: +352 661 500 106" -a "6226874E-5A04-4888-97C3-07289BAD0F37" -l "Laser Game Evolution Ettelbruck, 3 Rue Jean-Pierre Thill, L-9085 ETTELBRUCK"
```

*Notes:*
- Always use `./khal-sync.sh` instead of khal directly (auto-syncs to iCloud)
- Date format: DD/MM/YYYY
- Time format: HH:MM (24h)
- Duration: examples: `1h`, `30m`, `2h15m`
- Timezone: Always use `Europe/Luxembourg`
- Multi-line descriptions work in the :: section

---

## Scheduling for Other Groups

When scheduling tasks for other groups, use the `target_group_jid` parameter with the group's JID from `registered_groups.json`:
- `schedule_task(prompt: "...", schedule_type: "cron", schedule_value: "0 9 * * 1", target_group_jid: "120363336345536173@g.us")`

The task will run in that group's context with access to their files and memory.

---

## Music Control

**CRITICAL: NEVER use Home Assistant tools (`mcp__homeassistant__*`) for music. They are broken for this purpose.**

Always run music commands directly via Bash using the music-assistant script:

```bash
cd /home/node/.claude/skills/music-assistant

# Play music on a specific player — ALWAYS specify --player
./music-assistant.sh play "Queen" --player parents
./music-assistant.sh play "Europa Santana" --player cuisine
./music-assistant.sh pause --player parents
./music-assistant.sh resume --player parents
./music-assistant.sh volume 50 --player parents
./music-assistant.sh players   # list all players
```

**Player rules:**
- Always pass `--player <name-substring>` when the user names a room or speaker
- Never auto-select a player — playing in the wrong room is unacceptable
- If no player is specified, ask before playing

Available players (use name substring for `--player`):
- Sonos salon → `--player salon`
- Sonos Cuisine → `--player cuisine`
- Sonos Sal Manger → `--player manger`
- Sonos Nils → `--player nils`
- Sonos Lior → `--player lior`
- Sonos Parents → `--player parents`
- Sonos Salle Bain → `--player bain`
- Denon salle cinema → `--player denon`
- Sejour (group) → `--player sejour`
- Chambres enfants (group) → `--player chambres`
