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
