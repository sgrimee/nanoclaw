---
name: add-calendar-sync
description: Add calendar sync IPC support to NanoClaw. Enables triggering calendar synchronization from inside containers via IPC, either by piping to an active container or triggering a scheduled task. Use when user wants calendar sync, IPC calendar trigger, or scheduled calendar updates. Triggers on "calendar sync", "sync calendar", "calendar ipc".
disable-model-invocation: true
---

# Calendar Sync IPC

This skill adds an IPC mechanism for triggering calendar synchronization. When a container sends a `calendar_sync` IPC task, the host either pipes the sync command to an already-active main container or triggers the scheduled sync task to run immediately.

**What this changes:**
- `src/db.ts`: adds `triggerTaskNow()` function
- `src/ipc.ts`: adds `pipeToActiveContainer` to `IpcDeps` interface, adds `calendar_sync` case
- `src/index.ts`: passes `pipeToActiveContainer` callback to `startIpcWatcher()`

**What stays the same:**
- All existing IPC task types
- Scheduled task system
- Container runner and agent behavior

## 1. Add triggerTaskNow to Database

Edit `src/db.ts`:

### 1a. Add the triggerTaskNow function

Add this function after `deleteTask()` and before `getDueTasks()`:

```typescript
// Before:
export function getDueTasks(): ScheduledTask[] {

// After:
export function triggerTaskNow(id: string): void {
  db.prepare('UPDATE scheduled_tasks SET next_run = ? WHERE id = ?')
    .run(new Date().toISOString(), id);
}

export function getDueTasks(): ScheduledTask[] {
```

## 2. Update IPC Module

Edit `src/ipc.ts`:

### 2a. Add imports

Update the import from `./db.js` to include `getAllTasks` and `triggerTaskNow`:

```typescript
// Before:
import { createTask, deleteTask, getTaskById, updateTask } from './db.js';

// After:
import { createTask, deleteTask, getAllTasks, getTaskById, triggerTaskNow, updateTask } from './db.js';
```

### 2b. Add pipeToActiveContainer to IpcDeps interface

Add the new optional property to the `IpcDeps` interface, after the `writeGroupsSnapshot` property:

```typescript
// Before:
  ) => void;
}

// After (add before the closing brace):
  ) => void;
  /** Try to pipe a message to an active container. Returns true if sent. */
  pipeToActiveContainer?: (chatJid: string, message: string) => boolean;
}
```

### 2c. Add calendar_sync case

In the `processTaskIpc` function's switch statement, add a `calendar_sync` case before the `default` case:

```typescript
// Before:
    default:
      logger.warn({ type: data.type }, 'Unknown IPC task type');

// After:
    case 'calendar_sync': {
      // If main container is already active, pipe sync command to it directly
      // (otherwise the task would queue behind the active conversation)
      const mainJid = Object.entries(registeredGroups)
        .find(([, g]) => g.folder === MAIN_GROUP_FOLDER)?.[0];
      if (mainJid && deps.pipeToActiveContainer?.(mainJid, 'Run /workspace/group/sync_calendars.sh now. Wrap output in <internal> tags.')) {
        logger.info({ sourceGroup }, 'Calendar sync piped to active main container');
        break;
      }

      // No active container — trigger the scheduled task
      const allTasks = getAllTasks();
      const syncTask = allTasks.find(
        t => t.group_folder === MAIN_GROUP_FOLDER
          && t.status === 'active'
          && t.prompt.includes('sync_calendars.sh')
      );
      if (syncTask) {
        triggerTaskNow(syncTask.id);
        logger.info({ sourceGroup, taskId: syncTask.id }, 'Calendar sync triggered via IPC');
      } else {
        logger.warn({ sourceGroup }, 'Calendar sync requested but no sync task found');
      }
      break;
    }

    default:
      logger.warn({ type: data.type }, 'Unknown IPC task type');
```

## 3. Update Index

Edit `src/index.ts`:

### 3a. Pass pipeToActiveContainer to startIpcWatcher

Add the `pipeToActiveContainer` callback to the `startIpcWatcher` deps object:

```typescript
// Before:
    writeGroupsSnapshot: (gf, im, ag, rj) => writeGroupsSnapshot(gf, im, ag, rj),
  });

// After:
    writeGroupsSnapshot: (gf, im, ag, rj) => writeGroupsSnapshot(gf, im, ag, rj),
    pipeToActiveContainer: (chatJid, message) => queue.sendMessage(chatJid, message),
  });
```

Note: `queue.sendMessage` returns `true` if a container is active for that chat and the message was piped, `false` otherwise.

## 4. Verify

```bash
npm run build
```

Confirm it compiles without errors.

## Summary of Changed Files

| File | Type of Change |
|------|----------------|
| `src/db.ts` | Added `triggerTaskNow()` function |
| `src/ipc.ts` | Added `pipeToActiveContainer` dep, `calendar_sync` IPC case |
| `src/index.ts` | Passed `pipeToActiveContainer` to IPC watcher |
