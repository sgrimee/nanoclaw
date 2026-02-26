#!/usr/bin/env python3
"""CLI for controlling Music Assistant via music-assistant-client."""

import argparse
import asyncio
import os
import sys

from music_assistant_client import MusicAssistantClient


def get_endpoint() -> str:
    endpoint = os.environ.get("MUSIC_ASSISTANT_ENDPOINT", "").rstrip("/")
    if not endpoint:
        print(
            "Error: MUSIC_ASSISTANT_ENDPOINT not set. "
            "Add it to the group's .env file (e.g. MUSIC_ASSISTANT_ENDPOINT=http://192.168.1.x:8095)",
            file=sys.stderr,
        )
        sys.exit(1)
    # Convert http(s):// to ws(s):// and append /ws path
    if endpoint.startswith("https://"):
        ws_url = "wss://" + endpoint[8:]
    elif endpoint.startswith("http://"):
        ws_url = "ws://" + endpoint[7:]
    else:
        ws_url = endpoint
    if not ws_url.endswith("/ws"):
        ws_url += "/ws"
    return ws_url


def get_token() -> str:
    token = os.environ.get("MUSIC_ASSISTANT_TOKEN", "")
    if not token:
        print(
            "Error: MUSIC_ASSISTANT_TOKEN not set. "
            "Add it to the group's .env file.",
            file=sys.stderr,
        )
        sys.exit(1)
    return token


async def resolve_player(client: MusicAssistantClient, player_hint: str | None):
    """Return the best matching Player, or exit with an error."""
    players = list(client.players)
    if not players:
        print("No players available.", file=sys.stderr)
        sys.exit(1)

    if player_hint:
        hint = player_hint.lower()
        for p in players:
            if p.player_id == player_hint or hint in p.name.lower():
                return p
        names = ", ".join(f"{p.name} ({p.player_id})" for p in players)
        print(f"Player not found: {player_hint!r}. Available: {names}", file=sys.stderr)
        sys.exit(1)

    # Auto-detect: first playing/paused player, then first available
    try:
        from music_assistant_models.enums import PlayerState
        for p in players:
            if p.state in (PlayerState.PLAYING, PlayerState.PAUSED):
                return p
    except Exception:
        pass

    return players[0]


def _player_state_str(player) -> str:
    state = getattr(player, "state", None)
    if state is None:
        return "unknown"
    return state.value if hasattr(state, "value") else str(state)


def _media_name(item) -> str:
    """Extract a readable name from a media item or queue item."""
    name = getattr(item, "name", None)
    if name:
        return name
    media = getattr(item, "media_item", None)
    if media:
        return getattr(media, "name", str(media))
    return str(item)


def _artist_name(item) -> str | None:
    """Extract artist name from a media item, or None."""
    # Direct artist attribute (Track)
    artist = getattr(item, "artist", None) or getattr(item, "artists", None)
    if not artist:
        # Try via media_item
        media = getattr(item, "media_item", None)
        if media:
            artist = getattr(media, "artist", None) or getattr(media, "artists", None)
    if not artist:
        return None
    if isinstance(artist, list):
        return ", ".join(a.name for a in artist if hasattr(a, "name"))
    return artist.name if hasattr(artist, "name") else str(artist)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


async def cmd_players(client: MusicAssistantClient, _args) -> None:
    players = list(client.players)
    if not players:
        print("No players available.")
        return
    for p in players:
        vol = getattr(p, "volume_level", "?")
        state = _player_state_str(p)
        available = "" if getattr(p, "available", True) else " [unavailable]"
        print(f"{p.player_id} | {p.name} | {state} | vol:{vol}{available}")


async def cmd_status(client: MusicAssistantClient, args) -> None:
    player = await resolve_player(client, args.player)
    vol = getattr(player, "volume_level", "?")
    state = _player_state_str(player)
    print(f"Player: {player.name} [{state}] vol:{vol}")

    # Try to get current track from active queue
    try:
        queue = client.player_queues.get_active_queue(player.player_id)
        if queue and queue.current_item:
            item = queue.current_item
            name = _media_name(item)
            artist = _artist_name(item)
            if artist:
                print(f"Now playing: {name} — {artist}")
            else:
                print(f"Now playing: {name}")
            elapsed = getattr(queue, "elapsed_time", None)
            duration = getattr(item, "duration", None) or getattr(
                getattr(item, "media_item", None), "duration", None
            )
            if elapsed is not None:
                pos_str = f"{int(elapsed)}s"
                if duration:
                    pos_str += f" / {int(duration)}s"
                print(f"Position: {pos_str}")
        else:
            print("Nothing playing.")
    except Exception:
        print("Queue info unavailable.")


async def cmd_play(client: MusicAssistantClient, args) -> None:
    player = await resolve_player(client, args.player)

    try:
        from music_assistant_models.enums import MediaType
        media_types = [MediaType.TRACK, MediaType.ALBUM, MediaType.PLAYLIST, MediaType.ARTIST]
    except Exception:
        media_types = None

    kwargs = {"limit": 5}
    if media_types is not None:
        kwargs["media_types"] = media_types

    results = await client.music.search(args.query, **kwargs)

    media = None
    for bucket in ("tracks", "albums", "playlists", "artists", "radio"):
        items = getattr(results, bucket, [])
        if items:
            media = items[0]
            break

    if not media:
        print(f"No results found for: {args.query!r}")
        return

    name = _media_name(media)
    artist = _artist_name(media)
    await client.player_queues.play_media(player.player_id, media)
    if artist:
        print(f"Playing: {name} — {artist} on {player.name}")
    else:
        print(f"Playing: {name} on {player.name}")


async def cmd_pause(client: MusicAssistantClient, args) -> None:
    player = await resolve_player(client, args.player)
    await client.players.pause(player.player_id)
    print(f"Paused: {player.name}")


async def cmd_resume(client: MusicAssistantClient, args) -> None:
    player = await resolve_player(client, args.player)
    await client.players.play(player.player_id)
    print(f"Resumed: {player.name}")


async def cmd_stop(client: MusicAssistantClient, args) -> None:
    player = await resolve_player(client, args.player)
    await client.players.stop(player.player_id)
    print(f"Stopped: {player.name}")


async def cmd_next(client: MusicAssistantClient, args) -> None:
    player = await resolve_player(client, args.player)
    await client.players.next_track(player.player_id)
    print(f"Skipped to next track on: {player.name}")


async def cmd_volume(client: MusicAssistantClient, args) -> None:
    player = await resolve_player(client, args.player)
    level = max(0, min(100, args.level))
    await client.players.volume_set(player.player_id, level)
    print(f"Volume set to {level} on: {player.name}")


async def cmd_search(client: MusicAssistantClient, args) -> None:
    results = await client.music.search(args.query, limit=10)
    found = False
    for label, bucket in [
        ("Tracks", "tracks"),
        ("Albums", "albums"),
        ("Artists", "artists"),
        ("Playlists", "playlists"),
        ("Radio", "radio"),
    ]:
        items = getattr(results, bucket, [])
        if items:
            found = True
            print(f"{label}:")
            for item in items[:5]:
                name = _media_name(item)
                artist = _artist_name(item)
                if artist:
                    print(f"  {name} — {artist}")
                else:
                    print(f"  {name}")
    if not found:
        print(f"No results for: {args.query!r}")


async def cmd_queue(client: MusicAssistantClient, args) -> None:
    player = await resolve_player(client, args.player)

    # queue_id == player_id in Music Assistant
    queue_id = player.player_id
    try:
        queue = client.player_queues.get_active_queue(player.player_id)
        if queue:
            queue_id = queue.queue_id
    except Exception:
        pass

    items = await client.player_queues.get_queue_items(queue_id, limit=20)
    if not items:
        print(f"Queue is empty for: {player.name}")
        return

    # Determine current index for the ▶ marker
    current_idx = None
    try:
        q = client.player_queues.get_active_queue(player.player_id)
        if q:
            current_idx = getattr(q, "current_index", None)
    except Exception:
        pass

    print(f"Queue for {player.name} ({len(items)} items shown):")
    for i, item in enumerate(items):
        name = _media_name(item)
        artist = _artist_name(item)
        marker = "▶ " if i == current_idx else f"{i + 1}. "
        if artist:
            print(f"  {marker}{name} — {artist}")
        else:
            print(f"  {marker}{name}")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

COMMANDS = {
    "players": cmd_players,
    "status": cmd_status,
    "play": cmd_play,
    "pause": cmd_pause,
    "resume": cmd_resume,
    "stop": cmd_stop,
    "next": cmd_next,
    "volume": cmd_volume,
    "search": cmd_search,
    "queue": cmd_queue,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="music-assistant.sh",
        description="Control a Music Assistant server.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("players", help="List available players")

    p_status = sub.add_parser("status", help="Show current track/state")
    p_status.add_argument("--player", metavar="ID", help="Player ID or name substring")

    p_play = sub.add_parser("play", help="Search library and play")
    p_play.add_argument("query", nargs="+", help="Search query")
    p_play.add_argument("--player", metavar="ID", help="Player ID or name substring")

    p_pause = sub.add_parser("pause", help="Pause playback")
    p_pause.add_argument("--player", metavar="ID")

    p_resume = sub.add_parser("resume", help="Resume playback")
    p_resume.add_argument("--player", metavar="ID")

    p_stop = sub.add_parser("stop", help="Stop playback")
    p_stop.add_argument("--player", metavar="ID")

    p_next = sub.add_parser("next", help="Skip to next track")
    p_next.add_argument("--player", metavar="ID")

    p_vol = sub.add_parser("volume", help="Set volume (0-100)")
    p_vol.add_argument("level", type=int, help="Volume level 0-100")
    p_vol.add_argument("--player", metavar="ID")

    p_search = sub.add_parser("search", help="Search library without playing")
    p_search.add_argument("query", nargs="+", help="Search query")

    p_queue = sub.add_parser("queue", help="Show playback queue")
    p_queue.add_argument("--player", metavar="ID")

    return parser


async def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Join multi-word positional query args
    if hasattr(args, "query") and isinstance(args.query, list):
        args.query = " ".join(args.query)

    endpoint = get_endpoint()
    token = get_token()

    async with MusicAssistantClient(endpoint, token=token) as client:
        # Fetch player state so list(client.players) is populated
        await client.players.fetch_state()
        # Best-effort: fetch queue state for status/queue commands
        try:
            await client.player_queues.fetch_state()
        except Exception:
            pass
        await COMMANDS[args.command](client, args)


if __name__ == "__main__":
    asyncio.run(main())
