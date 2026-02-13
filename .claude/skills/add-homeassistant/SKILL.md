---
name: add-homeassistant
description: Add Home Assistant smart home control via MCP server integration. Enables controlling lights, switches, sensors, automations, and scenes. Use when user wants smart home control, Home Assistant integration, or home automation. Triggers on "home assistant", "smart home", "hass", "home automation".
disable-model-invocation: true
---

# Home Assistant via MCP

This skill adds Home Assistant smart home control to NanoClaw via the MCP server integration. It creates a container skill documenting the available tools and setup process.

**What this changes:**
- Creates `container/skills/homeassistant/SKILL.md` with tool documentation and setup instructions

**What stays the same:**
- No source code changes
- No container rebuild needed (MCP is configured per-group)

## Prerequisites

This skill requires two other skills to be installed first:

1. **add-group-env** — for per-group `.env` files (stores `HASS_API_KEY` and `HASS_API_ENDPOINT`)
2. **add-group-mcp** — for per-group `.mcp.json` support (configures the Home Assistant MCP server)

Verify these are present:
- Check that `src/container-runner.ts` has per-group env handling (look for `groups/{folder}/.env` pattern)
- Check that `container/agent-runner/src/index.ts` has `loadGroupMcpServers` function

## 1. Create Container Skill

Create the file `container/skills/homeassistant/SKILL.md` with the following content:

```markdown
# Home Assistant Skill

Control smart home devices via the Home Assistant MCP server integration.

## Available Tools

All tools are prefixed with `mcp__homeassistant__` (the name comes from `.mcp.json`).

Common operations:
- List entities and their current states
- Turn devices on/off (lights, switches, fans, etc.)
- Set specific values (brightness, temperature, color)
- Check sensor readings (temperature, humidity, energy)
- Trigger automations and scenes

## Setup

1. Add env vars to the group's `.env` file:
   ```
   HASS_API_KEY=your_long_lived_access_token
   HASS_API_ENDPOINT=http://homeassistant.local:8123/mcp/sse
   ```

2. Create `.mcp.json` in the group folder:
   ```json
   {
     "mcpServers": {
       "homeassistant": {
         "type": "http",
         "url": "${HASS_API_ENDPOINT}",
         "headers": {
           "Authorization": "Bearer ${HASS_API_KEY}"
         }
       }
     }
   }
   ```

3. Rebuild the container: `./container/build.sh`

The `${...}` placeholders are substituted at runtime with values from the group's `.env` file.
```

## 2. Verify

```bash
# Confirm the file was created
cat container/skills/homeassistant/SKILL.md
```

No build or container rebuild is needed — this skill only adds documentation. The actual MCP server is configured per-group via `.mcp.json`.

## Summary of Changed Files

| File | Type of Change |
|------|----------------|
| `container/skills/homeassistant/SKILL.md` | New file — skill documentation |
