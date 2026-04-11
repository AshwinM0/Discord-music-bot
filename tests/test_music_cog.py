"""
Tests for the Music cog's internal logic (cogs/music.py).

These tests use the mock fixtures from conftest.py to simulate Discord
objects. No real Discord connection is made — we're testing pure logic
like queue management, volume validation, and loop mode handling.

Key concepts for learning:
  - AsyncMock: simulates async functions (like ctx.send)
  - MagicMock: simulates regular objects (like ctx.guild)
  - Fixtures: reusable test setup injected by name (see conftest.py)

NOTE: discord.py wraps @commands.command methods in Command objects.
To call the raw coroutine, we use `cmd.callback(cog, ctx, ...)`.
"""

import pytest
from collections import deque
from unittest.mock import AsyncMock, MagicMock, patch

import discord


# ── Queue Management ─────────────────────────────────────────────────

def test_get_queue_creates_new(music_cog, mock_guild):
    """First access should create and return a new empty deque."""
    q = music_cog._get_queue(mock_guild.id)
    assert isinstance(q, deque)
    assert len(q) == 0


def test_get_queue_returns_existing(music_cog, mock_guild):
    """Subsequent access should return the same deque object."""
    q1 = music_cog._get_queue(mock_guild.id)
    q1.append("test song")
    q2 = music_cog._get_queue(mock_guild.id)
    assert q1 is q2
    assert "test song" in q2


def test_queues_are_guild_isolated(music_cog):
    """Each guild should get its own independent queue."""
    q1 = music_cog._get_queue(111)
    q2 = music_cog._get_queue(222)
    q1.append("song A")
    assert len(q2) == 0, "Guild 222's queue should be unaffected by guild 111"


# ── Queue Cap ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_queue_cap_enforced(music_cog, mock_ctx):
    """Adding a track when the queue is full should send an error embed."""
    from core.config import settings

    # Pre-fill the queue to the limit
    q = music_cog._get_queue(mock_ctx.guild.id)
    for i in range(settings.MAX_QUEUE_SIZE):
        q.append(f"song {i}")

    # Try to play one more — call .callback to bypass Command wrapper
    await music_cog.play.callback(music_cog, mock_ctx, query="one too many")

    # The bot should have sent an error message
    mock_ctx.send.assert_called_once()
    embed = mock_ctx.send.call_args[1].get("embed") or mock_ctx.send.call_args[0][0]
    assert isinstance(embed, discord.Embed)


@pytest.mark.asyncio
async def test_queue_under_cap_allowed(music_cog, mock_ctx):
    """Adding a track when under the cap should NOT send the cap error."""
    q = music_cog._get_queue(mock_ctx.guild.id)
    q.append("existing song")

    # Mock _enqueue to avoid the full play flow (voice connection etc.)
    music_cog._enqueue = AsyncMock()

    await music_cog.play.callback(music_cog, mock_ctx, query="new song")

    # _enqueue should have been called (not blocked by cap)
    music_cog._enqueue.assert_called_once()


# ── Volume ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_volume_valid_range(music_cog, mock_ctx):
    """Volume within 0-100 should be stored correctly."""
    await music_cog.volume.callback(music_cog, mock_ctx, vol=75)
    assert music_cog.volumes[mock_ctx.guild.id] == 0.75


@pytest.mark.asyncio
async def test_volume_zero(music_cog, mock_ctx):
    """Volume of 0 (mute) should be valid."""
    await music_cog.volume.callback(music_cog, mock_ctx, vol=0)
    assert music_cog.volumes[mock_ctx.guild.id] == 0.0


@pytest.mark.asyncio
async def test_volume_hundred(music_cog, mock_ctx):
    """Volume of 100 (max) should be valid."""
    await music_cog.volume.callback(music_cog, mock_ctx, vol=100)
    assert music_cog.volumes[mock_ctx.guild.id] == 1.0


@pytest.mark.asyncio
async def test_volume_too_high(music_cog, mock_ctx):
    """Volume > 100 should send an error and NOT update the stored value."""
    await music_cog.volume.callback(music_cog, mock_ctx, vol=150)
    assert mock_ctx.guild.id not in music_cog.volumes


@pytest.mark.asyncio
async def test_volume_negative(music_cog, mock_ctx):
    """Negative volume should send an error."""
    await music_cog.volume.callback(music_cog, mock_ctx, vol=-10)
    assert mock_ctx.guild.id not in music_cog.volumes


# ── Loop Modes ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_loop_mode_off(music_cog, mock_ctx):
    await music_cog.loop.callback(music_cog, mock_ctx, mode="off")
    assert music_cog.loop_modes[mock_ctx.guild.id] == "off"


@pytest.mark.asyncio
async def test_loop_mode_track(music_cog, mock_ctx):
    await music_cog.loop.callback(music_cog, mock_ctx, mode="track")
    assert music_cog.loop_modes[mock_ctx.guild.id] == "track"


@pytest.mark.asyncio
async def test_loop_mode_queue(music_cog, mock_ctx):
    await music_cog.loop.callback(music_cog, mock_ctx, mode="queue")
    assert music_cog.loop_modes[mock_ctx.guild.id] == "queue"


@pytest.mark.asyncio
async def test_loop_mode_invalid(music_cog, mock_ctx):
    """Invalid mode should send usage message and NOT set a mode."""
    await music_cog.loop.callback(music_cog, mock_ctx, mode="banana")
    assert mock_ctx.guild.id not in music_cog.loop_modes


@pytest.mark.asyncio
async def test_loop_mode_case_insensitive(music_cog, mock_ctx):
    """Loop mode should work regardless of case."""
    await music_cog.loop.callback(music_cog, mock_ctx, mode="TRACK")
    assert music_cog.loop_modes[mock_ctx.guild.id] == "track"


# ── Shuffle ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_shuffle_too_few_tracks(music_cog, mock_ctx):
    """Shuffle with 0 or 1 tracks should send an error."""
    q = music_cog._get_queue(mock_ctx.guild.id)
    q.append("only one song")
    await music_cog.shuffle.callback(music_cog, mock_ctx)
    # Should have sent an error embed
    mock_ctx.send.assert_called()


@pytest.mark.asyncio
async def test_shuffle_preserves_length(music_cog, mock_ctx):
    """Shuffle should not add or remove tracks."""
    q = music_cog._get_queue(mock_ctx.guild.id)
    songs = ["song A", "song B", "song C", "song D", "song E"]
    q.extend(songs)

    await music_cog.shuffle.callback(music_cog, mock_ctx)

    new_q = music_cog._get_queue(mock_ctx.guild.id)
    assert len(new_q) == len(songs)
    assert set(new_q) == set(songs), "Shuffle should not change which songs are in the queue"


# ── Remove ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_remove_valid_position(music_cog, mock_ctx):
    """Removing a valid position should shrink the queue."""
    q = music_cog._get_queue(mock_ctx.guild.id)
    q.extend(["A", "B", "C"])

    await music_cog.remove.callback(music_cog, mock_ctx, position=2)

    new_q = music_cog._get_queue(mock_ctx.guild.id)
    assert "B" not in new_q
    assert len(new_q) == 2


@pytest.mark.asyncio
async def test_remove_invalid_position_zero(music_cog, mock_ctx):
    """Position 0 is invalid (1-indexed) — should send error."""
    q = music_cog._get_queue(mock_ctx.guild.id)
    q.extend(["A", "B"])

    await music_cog.remove.callback(music_cog, mock_ctx, position=0)

    # Queue should be unchanged
    assert len(music_cog._get_queue(mock_ctx.guild.id)) == 2


@pytest.mark.asyncio
async def test_remove_invalid_position_too_high(music_cog, mock_ctx):
    """Position beyond queue length should send error."""
    q = music_cog._get_queue(mock_ctx.guild.id)
    q.extend(["A", "B"])

    await music_cog.remove.callback(music_cog, mock_ctx, position=5)
    assert len(music_cog._get_queue(mock_ctx.guild.id)) == 2


# ── Clear ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_clear_empties_queue(music_cog, mock_ctx):
    """Clear should empty the queue."""
    q = music_cog._get_queue(mock_ctx.guild.id)
    q.extend(["A", "B", "C"])

    await music_cog.clear.callback(music_cog, mock_ctx)

    assert len(music_cog._get_queue(mock_ctx.guild.id)) == 0


@pytest.mark.asyncio
async def test_clear_empty_queue(music_cog, mock_ctx):
    """Clearing an already-empty queue should send an error, not crash."""
    await music_cog.clear.callback(music_cog, mock_ctx)
    mock_ctx.send.assert_called()

