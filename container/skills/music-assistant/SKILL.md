---
name: music-assistant
description: Control Music Assistant — play, pause, skip, set volume, search library, list players.
allowed-tools: Bash(music-assistant:*)
---

# Music Assistant

Control a Music Assistant server: play music, manage playback, search the library.

**IMPORTANT: Always use this skill for music control. Never use Home Assistant tools for music — they are unreliable and do not have full library access.**

Requires `MUSIC_ASSISTANT_ENDPOINT` and `MUSIC_ASSISTANT_TOKEN` in the group's `.env`.

## Player selection rules

**CRITICAL: Always specify `--player` when the user mentions a room or speaker. Never auto-select or guess a player — starting music in the wrong room (e.g. where children are sleeping) is unacceptable.**

- If the user names a player or room → always pass `--player <name>`. Use a substring of the name (e.g. `--player parents`, `--player cuisine`).
- If the user gives no player preference → ask which player to use before playing.
- Never omit `--player` and let the script auto-detect.

## Quick start

```bash
music-assistant.sh players                           # list all players
music-assistant.sh status --player parents           # what's playing on a specific player
music-assistant.sh play jazz --player parents        # search and play on a specific player
music-assistant.sh pause --player parents
music-assistant.sh resume --player parents
```

## Commands

### players

List all available players with their current state and volume.

```bash
music-assistant.sh players
```

### status

Show the current track and playback state.

```bash
music-assistant.sh status --player ID  # always specify player
```

### play

Search the library and start playing the best match.

```bash
music-assistant.sh play "Miles Davis" --player parents    # play an artist on a specific player
music-assistant.sh play "Kind of Blue" --player cuisine   # play an album on a specific player
music-assistant.sh play beethoven --player nils           # on a specific player
```

### pause / resume / stop

Control playback state.

```bash
music-assistant.sh pause --player ID
music-assistant.sh resume --player ID
music-assistant.sh stop --player ID
```

### next

Skip to the next track.

```bash
music-assistant.sh next --player ID
```

### volume

Set volume (0–100).

```bash
music-assistant.sh volume 50 --player ID
music-assistant.sh volume 80 --player ID
```

### search

Search the library without playing.

```bash
music-assistant.sh search "bossa nova"
music-assistant.sh search "Coltrane"
```

### queue

Show the current playback queue.

```bash
music-assistant.sh queue --player ID
```

## Notes

- `--player` accepts a player ID or a case-insensitive name substring (e.g. `parents`, `cuisine`, `nils`).
- `MUSIC_ASSISTANT_ENDPOINT` can be `http://host:8095` or `ws://host:8095/ws` — both work.
