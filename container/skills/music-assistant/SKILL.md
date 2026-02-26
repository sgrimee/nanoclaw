---
name: music-assistant
description: Control Music Assistant — play, pause, skip, set volume, search library, list players.
allowed-tools: Bash(music-assistant:*)
---

# Music Assistant

Control a Music Assistant server: play music, manage playback, search the library.

Requires `MUSIC_ASSISTANT_ENDPOINT` and `MUSIC_ASSISTANT_TOKEN` in the group's `.env`.

## Quick start

```bash
music-assistant.sh players              # list all players
music-assistant.sh status               # what's playing now
music-assistant.sh play jazz            # search and play
music-assistant.sh pause                # pause
music-assistant.sh resume               # resume
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
music-assistant.sh status               # auto-detect player
music-assistant.sh status --player ID  # specific player
```

### play

Search the library and start playing the best match.

```bash
music-assistant.sh play jazz                       # play jazz
music-assistant.sh play "Miles Davis"              # play an artist
music-assistant.sh play "Kind of Blue"             # play an album
music-assistant.sh play beethoven --player ID      # on a specific player
```

### pause / resume / stop

Control playback state.

```bash
music-assistant.sh pause
music-assistant.sh resume
music-assistant.sh stop
music-assistant.sh pause --player ID
```

### next

Skip to the next track.

```bash
music-assistant.sh next
music-assistant.sh next --player ID
```

### volume

Set volume (0–100).

```bash
music-assistant.sh volume 50
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
music-assistant.sh queue
music-assistant.sh queue --player ID
```

## Notes

- `--player` accepts a player ID or a case-insensitive name substring.
- If `--player` is omitted, the first active (playing/paused) player is used; falls back to the first available player.
- `MUSIC_ASSISTANT_ENDPOINT` can be `http://host:8095` or `ws://host:8095/ws` — both work.
