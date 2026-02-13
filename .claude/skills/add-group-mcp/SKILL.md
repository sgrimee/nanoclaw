---
name: add-group-mcp
description: Add per-group MCP (Model Context Protocol) server configurations to NanoClaw. Each group can define its own .mcp.json with MCP servers that get loaded at runtime with env var substitution. Use when user wants per-group MCP tools, group-specific integrations, or custom MCP servers per group. Triggers on "per-group mcp", "group mcp", "mcp per group", "group .mcp.json".
disable-model-invocation: true
---

# Per-Group MCP Configurations

This skill adds support for per-group MCP server configurations. Each group can define a `.mcp.json` file in its group folder, and the agent runner will load those MCP servers at runtime with environment variable substitution.

**What this changes:**
- Agent runner: loads `/workspace/group/.mcp.json` at query time
- MCP servers from group config are spread into the SDK's `mcpServers` option
- Tool patterns (`mcp__{name}__*`) are auto-added to `allowedTools`
- Environment variables in config values (`${VAR}` and `${VAR:-default}`) are substituted
- Customize skill: updated to recommend per-group `.mcp.json` instead of hardcoding

**What stays the same:**
- The built-in `nanoclaw` MCP server
- All other agent runner behavior
- Container mounts and security

## 1. Update Agent Runner

Edit `container/agent-runner/src/index.ts`:

### 1a. Add GROUP_MCP_CONFIG_PATH constant

After the `SDKUserMessage` interface closing brace (around line 55), add the new constant before `IPC_INPUT_DIR`:

```typescript
// Before:
const IPC_INPUT_DIR = '/workspace/ipc/input';

// After:
const GROUP_MCP_CONFIG_PATH = '/workspace/group/.mcp.json';
const IPC_INPUT_DIR = '/workspace/ipc/input';
```

### 1b. Add substituteEnvVars function

Add this function before the `runQuery` function (after `waitForIpcMessage`):

```typescript
/**
 * Substitute ${VAR_NAME} patterns in all string values with process.env.
 */
function substituteEnvVars(obj: unknown): unknown {
  if (typeof obj === 'string') {
    return obj.replace(/\$\{([^}]+)\}/g, (_match, expr) => {
      const [varName, ...rest] = expr.split(':-');
      const defaultVal = rest.length > 0 ? rest.join(':-') : undefined;
      const val = process.env[varName];
      if (val !== undefined) return val;
      if (defaultVal !== undefined) return defaultVal;
      log(`Warning: env var ${varName} not set for MCP config substitution`);
      return '';
    });
  }
  if (Array.isArray(obj)) {
    return obj.map(substituteEnvVars);
  }
  if (obj !== null && typeof obj === 'object') {
    const result: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
      result[key] = substituteEnvVars(value);
    }
    return result;
  }
  return obj;
}
```

### 1c. Add loadGroupMcpServers function

Add this function right after `substituteEnvVars`:

```typescript
/**
 * Load per-group .mcp.json if it exists.
 * Returns MCP server configs (with env vars substituted) and allowed tool patterns.
 */
function loadGroupMcpServers(): { servers: Record<string, unknown>; allowedTools: string[] } {
  if (!fs.existsSync(GROUP_MCP_CONFIG_PATH)) {
    return { servers: {}, allowedTools: [] };
  }

  try {
    const raw = fs.readFileSync(GROUP_MCP_CONFIG_PATH, 'utf-8');
    const config = JSON.parse(raw);
    const mcpServers = config.mcpServers;

    if (!mcpServers || typeof mcpServers !== 'object') {
      log('.mcp.json has no mcpServers object, skipping');
      return { servers: {}, allowedTools: [] };
    }

    const servers = substituteEnvVars(mcpServers) as Record<string, unknown>;
    const allowedTools = Object.keys(mcpServers).map(name => `mcp__${name}__*`);

    log(`Loaded ${Object.keys(servers).length} MCP server(s) from .mcp.json: ${Object.keys(servers).join(', ')}`);
    return { servers, allowedTools };
  } catch (err) {
    log(`Failed to load .mcp.json: ${err instanceof Error ? err.message : String(err)}`);
    return { servers: {}, allowedTools: [] };
  }
}
```

### 1d. Integrate into runQuery

In the `runQuery` function, add the MCP loading call just before the `for await` loop:

```typescript
// Before:
  for await (const message of query({

// After:
  // Load per-group MCP servers from .mcp.json
  const groupMcp = loadGroupMcpServers();

  for await (const message of query({
```

### 1e. Spread group MCP allowed tools

In the `allowedTools` array inside the `query()` call, add the group tools after `'mcp__nanoclaw__*'`:

```typescript
// Before:
        'mcp__nanoclaw__*'
      ],

// After:
        'mcp__nanoclaw__*',
        ...groupMcp.allowedTools,
      ],
```

### 1f. Spread group MCP servers

In the `mcpServers` object inside the `query()` call, spread the group servers after the `nanoclaw` server config's closing brace:

```typescript
// Before:
        },
      },
      hooks: {

// After (spread group servers after the nanoclaw server block):
        },
        ...groupMcp.servers,
      },
      hooks: {
```

The full `mcpServers` block should look like:

```typescript
      mcpServers: {
        nanoclaw: {
          command: 'node',
          args: [mcpServerPath],
          env: {
            NANOCLAW_CHAT_JID: containerInput.chatJid,
            NANOCLAW_GROUP_FOLDER: containerInput.groupFolder,
            NANOCLAW_IS_MAIN: containerInput.isMain ? '1' : '0',
          },
        },
        ...groupMcp.servers,
      },
```

## 2. Update Customize Skill

Edit `.claude/skills/customize/SKILL.md`:

### 2a. Replace the "Adding a New MCP Integration" section

Find the `### Adding a New MCP Integration` section (around line 46) and replace it entirely:

```markdown
// Before:
### Adding a New MCP Integration

Questions to ask:
- What service? (Calendar, Notion, database, etc.)
- What operations needed? (read, write, both)
- Which groups should have access?

Implementation:
1. Add MCP server config to the container settings (see `src/container-runner.ts` for how MCP servers are mounted)
2. Document available tools in `groups/CLAUDE.md`

// After:
### Adding a New MCP Integration

Questions to ask:
- What service? (Calendar, Notion, database, etc.)
- What operations needed? (read, write, both)
- Which groups should have access?

Implementation:
1. Create a `.mcp.json` file in the target group folder (`groups/{folder}/.mcp.json`) with the MCP server config. Use `${VAR_NAME}` syntax for env var substitution (values come from the group's `.env` file). Example:
   ```json
   {
     "mcpServers": {
       "my-service": {
         "command": "npx",
         "args": ["-y", "@my/mcp-server"],
         "env": { "API_KEY": "${MY_SERVICE_API_KEY}" }
       }
     }
   }
   ```
2. Add required env vars to the group's `.env` file (requires `add-group-env` skill)
3. Document available tools in the group's `CLAUDE.md`
4. The agent runner auto-loads `.mcp.json` at startup and adds `mcp__{name}__*` to allowed tools
```

## 3. Verify

```bash
# Rebuild container to pick up agent-runner changes
./container/build.sh

# Verify the build
docker run -i --rm --entrypoint wc nanoclaw-agent:latest -l /app/src/index.ts
```

Test by creating a `.mcp.json` in a group folder and verifying the MCP server loads at runtime.

## Summary of Changed Files

| File | Type of Change |
|------|----------------|
| `container/agent-runner/src/index.ts` | Group MCP loading, env var substitution |
| `.claude/skills/customize/SKILL.md` | Updated MCP integration guidance |
