---
name: add-group-env
description: Add per-group and shared environment variables to NanoClaw. Supports three tiers — root .env (auth only), groups/global/.env (shared across all groups), groups/{folder}/.env (per-group). Variables are available to both the Claude SDK and Bash subprocesses (skills, tools). Use when the user wants per-group secrets, API keys per group, shared env vars, or isolated environment variables. Triggers on "per-group env", "group environment", "group secrets", "group .env", "shared env", "env vars".
disable-model-invocation: true
---

# Per-Group and Shared Environment Variables

This skill modifies three files so that environment variables are available to both the Claude Agent SDK and Bash subprocesses (skills and tools) inside containers.

**Three-tier env loading (lowest to highest priority):**

| Source | Path | Allowlist | Scope |
|--------|------|-----------|-------|
| Root `.env` | `<project>/.env` | Auth vars only (`CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_API_KEY`) | All groups |
| Shared group env | `groups/global/.env` | None (all vars) | All groups |
| Per-group env | `groups/{folder}/.env` | None (all vars, overrides global) | That group only |

All three sources are merged into a single `env` file per group at `data/env/{group.folder}/env`, then mounted read-only into the container at `/workspace/env-dir/env`.

**Why three files are changed:**
- `src/container-runner.ts` — builds and mounts the per-group env file
- `container/agent-runner/src/index.ts` — loads non-auth vars into `process.env` at Node startup so Bash subprocesses spawned by the SDK inherit them
- `container/Dockerfile` — sources the env file in the shell entrypoint so all Bash processes (not just Node-spawned ones) also inherit the vars; auth secrets are stripped by the existing PreToolUse hook

## 1. Update `src/container-runner.ts`

Find the comment `// Per-group IPC namespace` (around line 164). Insert the following block **before** it:

```typescript
  // Environment file directory (keeps credentials out of process listings)
  // Each group gets its own env dir to prevent cross-group secret leakage
  const envDir = path.join(DATA_DIR, 'env', group.folder);
  fs.mkdirSync(envDir, { recursive: true });
  const envLines: string[] = [];

  // Global env: only expose specific auth variables needed by Claude Code
  const globalEnvFile = path.join(projectRoot, '.env');
  if (fs.existsSync(globalEnvFile)) {
    const envContent = fs.readFileSync(globalEnvFile, 'utf-8');
    const allowedVars = ['CLAUDE_CODE_OAUTH_TOKEN', 'ANTHROPIC_API_KEY'];
    for (const line of envContent.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) continue;
      if (allowedVars.some((v) => trimmed.startsWith(`${v}=`))) {
        envLines.push(trimmed);
      }
    }
  }

  // Shared env: all vars from groups/global/.env apply to every group (no allowlist)
  const globalGroupEnvFile = path.join(GROUPS_DIR, 'global', '.env');
  if (fs.existsSync(globalGroupEnvFile)) {
    const globalGroupEnvContent = fs.readFileSync(globalGroupEnvFile, 'utf-8');
    for (const line of globalGroupEnvContent.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) continue;
      envLines.push(trimmed);
    }
  }

  // Per-group env: append all vars from groups/{folder}/.env (no allowlist, overrides global)
  const groupEnvFile = path.join(GROUPS_DIR, group.folder, '.env');
  if (fs.existsSync(groupEnvFile)) {
    const groupEnvContent = fs.readFileSync(groupEnvFile, 'utf-8');
    for (const line of groupEnvContent.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) continue;
      envLines.push(trimmed);
    }
  }

  if (envLines.length > 0) {
    fs.writeFileSync(path.join(envDir, 'env'), envLines.join('\n') + '\n');
    mounts.push({
      hostPath: envDir,
      containerPath: '/workspace/env-dir',
      readonly: true,
    });
  }
```

`DATA_DIR` and `GROUPS_DIR` must already be imported from `./config.js` — confirm both are present in the imports at the top of the file.

## 2. Update `container/agent-runner/src/index.ts`

Find the comment `// Build SDK env:` (around line 592) and insert the following block **before** it:

```typescript
  // Load group env vars into process.env so Bash subprocesses can see them.
  // Auth secrets are excluded — they're passed via stdin and stay in sdkEnv only.
  const groupEnvFile = '/workspace/env-dir/env';
  if (fs.existsSync(groupEnvFile)) {
    const envContent = fs.readFileSync(groupEnvFile, 'utf-8');
    for (const line of envContent.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) continue;
      const eqIdx = trimmed.indexOf('=');
      if (eqIdx === -1) continue;
      const key = trimmed.slice(0, eqIdx).trim();
      if (SECRET_ENV_VARS.includes(key)) continue;
      const value = trimmed.slice(eqIdx + 1).trim();
      process.env[key] = value;
    }
  }

```

`SECRET_ENV_VARS` is already defined in this file as `['ANTHROPIC_API_KEY', 'CLAUDE_CODE_OAUTH_TOKEN']`.

Also update the comment on the next line to read:

```typescript
  // Build SDK env: merge process.env with auth secrets for the SDK.
```

## 3. Update `container/Dockerfile`

Find the `RUN printf` line that creates `entrypoint.sh`. Replace it with a version that sources the env file before starting Node:

**Before:**
```dockerfile
RUN printf '#!/bin/bash\nset -e\ncd /app && npx tsc --outDir /tmp/dist 2>&1 >&2\nln -s /app/node_modules /tmp/dist/node_modules\nchmod -R a-w /tmp/dist\ncat > /tmp/input.json\nnode /tmp/dist/index.js < /tmp/input.json\n' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh
```

**After** (add two comment lines above, modify the printf):
```dockerfile
# Group env vars are sourced so Bash subprocesses (skills, tools) can access them.
# Secrets (CLAUDE_CODE_OAUTH_TOKEN etc.) are stripped from Bash by the PreToolUse hook.
RUN printf '#!/bin/bash\nset -e\nif [ -f /workspace/env-dir/env ]; then set -a; . /workspace/env-dir/env; set +a; fi\ncd /app && npx tsc --outDir /tmp/dist 2>&1 >&2\nln -s /app/node_modules /tmp/dist/node_modules\nchmod -R a-w /tmp/dist\ncat > /tmp/input.json\nnode /tmp/dist/index.js < /tmp/input.json\n' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh
```

The key addition is: `if [ -f /workspace/env-dir/env ]; then set -a; . /workspace/env-dir/env; set +a; fi`

`set -a` exports all variables defined by the sourced file, `set +a` restores normal behavior.

## 4. Build and verify

```bash
npm run build
```

Rebuild the container image:

```bash
./container/build.sh
```

Test by creating a group `.env` file and confirming the variable is visible inside a Bash tool:

```bash
echo "MY_VAR=hello" > groups/{your-group}/.env
# Then from the agent: run `echo $MY_VAR` via Bash tool — should print "hello"
```

For a shared variable available to all groups:

```bash
echo "SHARED_VAR=world" > groups/global/.env
```

## Summary of changed files

| File | Change |
|------|--------|
| `src/container-runner.ts` | Builds per-group env file from 3 sources, mounts as `/workspace/env-dir` |
| `container/agent-runner/src/index.ts` | Loads non-auth vars from env file into `process.env` at Node startup |
| `container/Dockerfile` | Sources env file in shell entrypoint so all Bash processes inherit vars |
