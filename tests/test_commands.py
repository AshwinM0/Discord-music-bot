"""
Tests for Music cog commands that require a voice connection.

These tests cover: _send_embed, _ensure_voice, join, leave, skip,
pause, resume, stop, now_playing, queue display, and duplicate detection.

Each test sets up a mock voice client on the bot to simulate
the bot being connected to a voice channel.
"""

import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import discord
from discord.utils import get


# ── Helper: attach a voice client to the mock bot ────────────────────

def _connect_bot(mock_bot, mock_voice_client, mock_guild):
    """Simulate the bot being in a voice channel."""
    mock_voice_client.guild = mock_guild
    mock_bot.voice_clients = [mock_voice_client]


# ── _send_embed helper ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_embed_basic(music_cog, mock_ctx):
    """_send_embed should send a styled embed via ctx.send."""
    await music_cog._send_embed(mock_ctx, "Hello world")
    mock_ctx.send.assert_called_once()
    embed = mock_ctx.send.call_args[1]["embed"]
    assert embed.description == "Hello world"


@pytest.mark.asyncio
async def test_send_embed_with_title(music_cog, mock_ctx):
    """_send_embed should set the title if provided."""
    await music_cog._send_embed(mock_ctx, "Body", title="Header")
    embed = mock_ctx.send.call_args[1]["embed"]
    assert embed.title == "Header"


@pytest.mark.asyncio
async def test_send_embed_with_view(music_cog, mock_ctx):
    """_send_embed should pass the view through to ctx.send."""
    fake_view = MagicMock()
    await music_cog._send_embed(mock_ctx, "With view", view=fake_view)
    call_kwargs = mock_ctx.send.call_args[1]
    assert call_kwargs["view"] is fake_view


# ── _ensure_voice ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ensure_voice_no_author_vc_no_bot(music_cog, mock_ctx):
    """If author is not in VC and bot is not connected, send error."""
    mock_ctx.author.voice = None
    result = await music_cog._ensure_voice(mock_ctx)
    assert result is None
    mock_ctx.send.assert_called_once()


@pytest.mark.asyncio
async def test_ensure_voice_no_author_vc_bot_connected(music_cog, mock_ctx, mock_voice_client, mock_guild):
    """If author is not in VC but bot IS connected, send 'already in vc'."""
    _connect_bot(music_cog.bot, mock_voice_client, mock_guild)
    mock_ctx.author.voice = None
    result = await music_cog._ensure_voice(mock_ctx)
    assert result is None


@pytest.mark.asyncio
async def test_ensure_voice_author_in_vc_bot_not(music_cog, mock_ctx, mock_voice_channel):
    """If author is in VC and bot is not, should connect to author's channel."""
    # Bot has no voice clients
    mock_voice_channel.connect = AsyncMock(return_value=MagicMock())
    result = await music_cog._ensure_voice(mock_ctx)
    mock_voice_channel.connect.assert_called_once()


@pytest.mark.asyncio
async def test_ensure_voice_both_in_same_vc(music_cog, mock_ctx, mock_voice_client, mock_guild, mock_voice_channel):
    """If both are in the same VC, return the existing voice client."""
    mock_voice_client.channel = mock_voice_channel
    _connect_bot(music_cog.bot, mock_voice_client, mock_guild)
    result = await music_cog._ensure_voice(mock_ctx)
    assert result is mock_voice_client


# ── Join command ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_join_no_author_vc(music_cog, mock_ctx):
    """Join should fail when author is not in a voice channel."""
    mock_ctx.author.voice = None
    await music_cog.join.callback(music_cog, mock_ctx)
    mock_ctx.send.assert_called_once()


@pytest.mark.asyncio
async def test_join_fresh(music_cog, mock_ctx, mock_voice_channel):
    """Join should connect to the author's VC when bot is not connected."""
    mock_voice_channel.connect = AsyncMock()
    await music_cog.join.callback(music_cog, mock_ctx)
    mock_voice_channel.connect.assert_called_once()


@pytest.mark.asyncio
async def test_join_already_in_same_vc(music_cog, mock_ctx, mock_voice_client, mock_guild, mock_voice_channel):
    """Join should send 'already in your VC' when bot is in same channel."""
    mock_voice_client.channel = mock_voice_channel
    _connect_bot(music_cog.bot, mock_voice_client, mock_guild)
    await music_cog.join.callback(music_cog, mock_ctx)
    # Should have sent an embed (already in your VC)
    mock_ctx.send.assert_called_once()


@pytest.mark.asyncio
async def test_join_different_vc(music_cog, mock_ctx, mock_voice_client, mock_guild, mock_voice_channel):
    """Join should move to the author's VC when bot is in a different one."""
    other_channel = MagicMock(spec=discord.VoiceChannel)
    other_channel.name = "Other"
    mock_voice_client.channel = other_channel  # Bot is in a different channel
    _connect_bot(music_cog.bot, mock_voice_client, mock_guild)

    mock_voice_channel.connect = AsyncMock()
    await music_cog.join.callback(music_cog, mock_ctx)
    mock_voice_client.disconnect.assert_called_once()
    mock_voice_channel.connect.assert_called_once()


# ── Leave command ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_leave_connected(music_cog, mock_ctx, mock_voice_client, mock_guild):
    """Leave should disconnect and clear state."""
    _connect_bot(music_cog.bot, mock_voice_client, mock_guild)
    # Pre-set some state
    music_cog._get_queue(mock_guild.id).append("test")
    music_cog.now_playing[mock_guild.id] = {"title": "Test"}
    music_cog.loop_modes[mock_guild.id] = "track"

    await music_cog.leave.callback(music_cog, mock_ctx)

    mock_voice_client.disconnect.assert_called_once()
    assert len(music_cog._get_queue(mock_guild.id)) == 0
    assert mock_guild.id not in music_cog.now_playing
    assert mock_guild.id not in music_cog.loop_modes


@pytest.mark.asyncio
async def test_leave_not_connected(music_cog, mock_ctx):
    """Leave should send error when bot is not in a VC."""
    await music_cog.leave.callback(music_cog, mock_ctx)
    mock_ctx.send.assert_called_once()


# ── Skip command ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_skip_while_playing(music_cog, mock_ctx, mock_voice_client, mock_guild):
    """Skip should stop current playback and set _skip_req flag."""
    mock_voice_client.is_playing.return_value = True
    _connect_bot(music_cog.bot, mock_voice_client, mock_guild)
    music_cog.now_playing[mock_guild.id] = {"title": "Current Song"}

    await music_cog.skip.callback(music_cog, mock_ctx)

    mock_voice_client.stop.assert_called_once()
    assert getattr(music_cog, f'_skip_req_{mock_guild.id}', False) is True


@pytest.mark.asyncio
async def test_skip_nothing_playing(music_cog, mock_ctx):
    """Skip should send error when nothing is playing."""
    await music_cog.skip.callback(music_cog, mock_ctx)
    mock_ctx.send.assert_called_once()


# ── Pause command ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pause_while_playing(music_cog, mock_ctx, mock_voice_client, mock_guild):
    """Pause should pause playback and record paused_at time."""
    mock_voice_client.is_playing.return_value = True
    _connect_bot(music_cog.bot, mock_voice_client, mock_guild)
    music_cog.now_playing[mock_guild.id] = {"title": "Test", "paused_at": 0}

    await music_cog.pause.callback(music_cog, mock_ctx)

    mock_voice_client.pause.assert_called_once()
    assert music_cog.now_playing[mock_guild.id]["paused_at"] > 0


@pytest.mark.asyncio
async def test_pause_already_paused(music_cog, mock_ctx, mock_voice_client, mock_guild):
    """Pause when already paused should send 'already paused'."""
    mock_voice_client.is_playing.return_value = False
    mock_voice_client.is_paused.return_value = True
    _connect_bot(music_cog.bot, mock_voice_client, mock_guild)

    await music_cog.pause.callback(music_cog, mock_ctx)
    mock_ctx.send.assert_called_once()


@pytest.mark.asyncio
async def test_pause_nothing_playing(music_cog, mock_ctx):
    """Pause should send error when nothing is playing."""
    await music_cog.pause.callback(music_cog, mock_ctx)
    mock_ctx.send.assert_called_once()


# ── Resume command ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_resume_while_paused(music_cog, mock_ctx, mock_voice_client, mock_guild):
    """Resume should resume playback and reset paused_at."""
    mock_voice_client.is_paused.return_value = True
    _connect_bot(music_cog.bot, mock_voice_client, mock_guild)
    music_cog.now_playing[mock_guild.id] = {
        "title": "Test", "paused_at": time.time() - 5, "start_time": time.time() - 100
    }

    await music_cog.resume.callback(music_cog, mock_ctx)

    mock_voice_client.resume.assert_called_once()
    assert music_cog.now_playing[mock_guild.id]["paused_at"] == 0


@pytest.mark.asyncio
async def test_resume_while_playing(music_cog, mock_ctx, mock_voice_client, mock_guild):
    """Resume when already playing should send 'already playing'."""
    mock_voice_client.is_paused.return_value = False
    mock_voice_client.is_playing.return_value = True
    _connect_bot(music_cog.bot, mock_voice_client, mock_guild)

    await music_cog.resume.callback(music_cog, mock_ctx)
    mock_ctx.send.assert_called_once()


@pytest.mark.asyncio
async def test_resume_nothing_playing(music_cog, mock_ctx):
    """Resume should send error when nothing is playing."""
    await music_cog.resume.callback(music_cog, mock_ctx)
    mock_ctx.send.assert_called_once()


# ── Stop command ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stop_while_playing(music_cog, mock_ctx, mock_voice_client, mock_guild):
    """Stop should stop playback, clear queue, and wipe state."""
    mock_voice_client.is_playing.return_value = True
    _connect_bot(music_cog.bot, mock_voice_client, mock_guild)
    music_cog._get_queue(mock_guild.id).extend(["A", "B", "C"])
    music_cog.now_playing[mock_guild.id] = {"title": "Test"}
    music_cog.loop_modes[mock_guild.id] = "track"

    await music_cog.stop.callback(music_cog, mock_ctx)

    mock_voice_client.stop.assert_called_once()
    assert len(music_cog._get_queue(mock_guild.id)) == 0
    assert mock_guild.id not in music_cog.now_playing
    assert mock_guild.id not in music_cog.loop_modes


@pytest.mark.asyncio
async def test_stop_nothing_playing(music_cog, mock_ctx):
    """Stop should send error when nothing is playing."""
    await music_cog.stop.callback(music_cog, mock_ctx)
    mock_ctx.send.assert_called_once()


# ── Now Playing command ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_np_nothing_playing(music_cog, mock_ctx):
    """NP should send error when nothing is playing."""
    await music_cog.now_playing_cmd.callback(music_cog, mock_ctx)
    mock_ctx.send.assert_called_once()


@pytest.mark.asyncio
async def test_np_with_track(music_cog, mock_ctx, mock_voice_client, mock_guild):
    """NP should show the current track with a progress bar."""
    mock_voice_client.is_playing.return_value = True
    mock_voice_client.is_paused.return_value = False
    _connect_bot(music_cog.bot, mock_voice_client, mock_guild)
    music_cog.now_playing[mock_guild.id] = {
        "title": "Test Song",
        "video_url": "https://youtube.com/watch?v=abc",
        "query": "test song",
        "duration": 200,
        "start_time": time.time() - 30,
        "paused_at": 0,
    }

    await music_cog.now_playing_cmd.callback(music_cog, mock_ctx)

    mock_ctx.send.assert_called_once()
    embed = mock_ctx.send.call_args[1]["embed"]
    assert "Test Song" in embed.description
    assert "🔘" in embed.description  # progress bar


@pytest.mark.asyncio
async def test_np_while_paused(music_cog, mock_ctx, mock_voice_client, mock_guild):
    """NP while paused should show the paused status."""
    mock_voice_client.is_playing.return_value = False
    mock_voice_client.is_paused.return_value = True
    _connect_bot(music_cog.bot, mock_voice_client, mock_guild)
    paused_time = time.time() - 10
    music_cog.now_playing[mock_guild.id] = {
        "title": "Paused Song",
        "video_url": "",
        "query": "paused song",
        "duration": 180,
        "start_time": time.time() - 60,
        "paused_at": paused_time,
    }

    await music_cog.now_playing_cmd.callback(music_cog, mock_ctx)

    embed = mock_ctx.send.call_args[1]["embed"]
    assert "Paused" in embed.description


# ── Queue display command ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_queue_display_empty(music_cog, mock_ctx):
    """Queue should show 'empty' when nothing is queued or playing."""
    await music_cog.queue.callback(music_cog, mock_ctx)
    mock_ctx.send.assert_called_once()


@pytest.mark.asyncio
async def test_queue_display_with_tracks(music_cog, mock_ctx, mock_voice_client, mock_guild):
    """Queue should list all tracks and the current now-playing."""
    _connect_bot(music_cog.bot, mock_voice_client, mock_guild)
    music_cog.now_playing[mock_guild.id] = {
        "title": "Current", "video_url": "", "query": "current"
    }
    q = music_cog._get_queue(mock_guild.id)
    q.extend(["Song A", "Song B", "Song C"])

    await music_cog.queue.callback(music_cog, mock_ctx)

    mock_ctx.send.assert_called_once()
    embed = mock_ctx.send.call_args[1]["embed"]
    assert "Current" in embed.description
    assert "Song A" in embed.description


# ── Duplicate detection ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_play_duplicate_in_queue(music_cog, mock_ctx):
    """Playing a song already in queue should trigger duplicate prompt."""
    q = music_cog._get_queue(mock_ctx.guild.id)
    q.append("demons")

    await music_cog.play.callback(music_cog, mock_ctx, query="demons")

    # Should send a duplicate confirmation embed, not enqueue
    mock_ctx.send.assert_called_once()
    embed = mock_ctx.send.call_args[1]["embed"]
    assert "already" in embed.description.lower()


@pytest.mark.asyncio
async def test_play_duplicate_now_playing(music_cog, mock_ctx):
    """Playing a song that's currently playing should trigger duplicate prompt."""
    music_cog.now_playing[mock_ctx.guild.id] = {
        "title": "Demons", "video_url": "", "query": "demons"
    }

    await music_cog.play.callback(music_cog, mock_ctx, query="demons")

    mock_ctx.send.assert_called_once()
    embed = mock_ctx.send.call_args[1]["embed"]
    assert "already" in embed.description.lower()


@pytest.mark.asyncio
async def test_play_duplicate_case_insensitive(music_cog, mock_ctx):
    """Duplicate detection should be case-insensitive."""
    q = music_cog._get_queue(mock_ctx.guild.id)
    q.append("Demons")

    await music_cog.play.callback(music_cog, mock_ctx, query="DEMONS")

    mock_ctx.send.assert_called_once()
    embed = mock_ctx.send.call_args[1]["embed"]
    assert "already" in embed.description.lower()


# ── UI Button: VC guard ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_button_play_pause_not_in_vc(music_cog, mock_interaction, mock_voice_client, mock_guild):
    """Play/Pause button should reject users not in the bot's VC."""
    from cogs.music import MusicControlView

    _connect_bot(music_cog.bot, mock_voice_client, mock_guild)
    mock_interaction.user.voice = None  # User is not in any VC

    view = MusicControlView(music_cog)
    # Call the underlying coroutine directly (bypass discord.ui.button wrapper)
    await MusicControlView.toggle_play(view, mock_interaction, MagicMock())

    mock_interaction.response.send_message.assert_called_once()
    call_kwargs = mock_interaction.response.send_message.call_args[1]
    assert call_kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_button_skip_not_in_vc(music_cog, mock_interaction, mock_voice_client, mock_guild):
    """Skip button should reject users not in the bot's VC."""
    from cogs.music import MusicControlView

    _connect_bot(music_cog.bot, mock_voice_client, mock_guild)
    mock_interaction.user.voice = None

    view = MusicControlView(music_cog)
    await MusicControlView.skip(view, mock_interaction, MagicMock())

    mock_interaction.response.send_message.assert_called_once()
    call_kwargs = mock_interaction.response.send_message.call_args[1]
    assert call_kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_button_stop_not_in_vc(music_cog, mock_interaction, mock_voice_client, mock_guild):
    """Stop button should reject users not in the bot's VC."""
    from cogs.music import MusicControlView

    _connect_bot(music_cog.bot, mock_voice_client, mock_guild)
    mock_interaction.user.voice = None

    view = MusicControlView(music_cog)
    await MusicControlView.stop(view, mock_interaction, MagicMock())

    mock_interaction.response.send_message.assert_called_once()
    call_kwargs = mock_interaction.response.send_message.call_args[1]
    assert call_kwargs.get("ephemeral") is True


# ── UI Button: actual functionality ──────────────────────────────────

@pytest.mark.asyncio
async def test_button_play_pause_pauses(music_cog, mock_interaction, mock_voice_client, mock_guild):
    """Play/Pause button should pause when currently playing."""
    from cogs.music import MusicControlView

    mock_voice_client.is_playing.return_value = True
    _connect_bot(music_cog.bot, mock_voice_client, mock_guild)
    music_cog.now_playing[mock_guild.id] = {"title": "Test", "paused_at": 0}

    view = MusicControlView(music_cog)
    await MusicControlView.toggle_play(view, mock_interaction, MagicMock())

    mock_voice_client.pause.assert_called_once()


@pytest.mark.asyncio
async def test_button_play_pause_resumes(music_cog, mock_interaction, mock_voice_client, mock_guild):
    """Play/Pause button should resume when currently paused."""
    from cogs.music import MusicControlView

    mock_voice_client.is_playing.return_value = False
    mock_voice_client.is_paused.return_value = True
    _connect_bot(music_cog.bot, mock_voice_client, mock_guild)
    music_cog.now_playing[mock_guild.id] = {
        "title": "Test", "paused_at": time.time(), "start_time": time.time() - 30
    }

    view = MusicControlView(music_cog)
    await MusicControlView.toggle_play(view, mock_interaction, MagicMock())

    mock_voice_client.resume.assert_called_once()


@pytest.mark.asyncio
async def test_button_skip_works(music_cog, mock_interaction, mock_voice_client, mock_guild):
    """Skip button should stop voice and set _skip_req flag."""
    from cogs.music import MusicControlView

    mock_voice_client.is_playing.return_value = True
    _connect_bot(music_cog.bot, mock_voice_client, mock_guild)
    music_cog.now_playing[mock_guild.id] = {"title": "Skippable"}

    view = MusicControlView(music_cog)
    await MusicControlView.skip(view, mock_interaction, MagicMock())

    mock_voice_client.stop.assert_called_once()
    assert getattr(music_cog, f'_skip_req_{mock_guild.id}', False) is True


@pytest.mark.asyncio
async def test_button_stop_clears_all(music_cog, mock_interaction, mock_voice_client, mock_guild):
    """Stop button should clear queue, now_playing, and loop modes."""
    from cogs.music import MusicControlView

    mock_voice_client.is_playing.return_value = True
    _connect_bot(music_cog.bot, mock_voice_client, mock_guild)
    music_cog._get_queue(mock_guild.id).extend(["A", "B"])
    music_cog.now_playing[mock_guild.id] = {"title": "Test"}
    music_cog.loop_modes[mock_guild.id] = "queue"

    view = MusicControlView(music_cog)
    await MusicControlView.stop(view, mock_interaction, MagicMock())

    assert len(music_cog._get_queue(mock_guild.id)) == 0
    assert mock_guild.id not in music_cog.now_playing
    assert mock_guild.id not in music_cog.loop_modes
    mock_voice_client.stop.assert_called_once()


# ── UI Button: no voice connection ───────────────────────────────────

@pytest.mark.asyncio
async def test_button_play_pause_no_voice(music_cog, mock_interaction):
    """Play/Pause should send 'nothing playing' when bot is not connected."""
    from cogs.music import MusicControlView

    view = MusicControlView(music_cog)
    await MusicControlView.toggle_play(view, mock_interaction, MagicMock())

    mock_interaction.response.send_message.assert_called_once()
    call_kwargs = mock_interaction.response.send_message.call_args[1]
    assert call_kwargs.get("ephemeral") is True

