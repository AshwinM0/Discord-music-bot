from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from discord.ext import commands


# ── Patch the config module BEFORE importing anything that touches it ──
# The real config.py tries to read .env and will crash in CI where no
# .env exists. We patch the Settings class to return dummy values.

@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch):
    """Prevent pydantic-settings from reading .env during tests."""
    monkeypatch.setenv("DISCORD_TOKEN", "fake-token-for-tests")
    monkeypatch.setenv("CHANNEL_ID", "123456789")


# ── Bot & Context fixtures ───────────────────────────────────────────

@pytest.fixture
def mock_bot():
    """Create a minimal mock of commands.Bot."""
    bot = MagicMock(spec=commands.Bot)
    bot.voice_clients = []
    bot.user = MagicMock()
    bot.user.id = 999
    bot.user.__str__ = lambda self: "TestBot#0001"
    return bot


@pytest.fixture
def mock_guild():
    """Create a mock Discord guild (server)."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = 111222333
    guild.name = "Test Server"
    return guild


@pytest.fixture
def mock_voice_channel():
    """Create a mock voice channel."""
    channel = MagicMock(spec=discord.VoiceChannel)
    channel.name = "General"
    channel.id = 444555666
    channel.connect = AsyncMock()
    return channel


@pytest.fixture
def mock_author(mock_voice_channel):
    """Create a mock member who is in a voice channel."""
    author = MagicMock(spec=discord.Member)
    author.id = 777888999
    author.name = "TestUser"

    # Simulate being in a voice channel
    voice_state = MagicMock(spec=discord.VoiceState)
    voice_state.channel = mock_voice_channel
    author.voice = voice_state

    return author


@pytest.fixture
def mock_ctx(mock_bot, mock_guild, mock_author):
    """
    Create a mock commands.Context — the object every command receives.

    This is the most important fixture. Every command in music.py takes
    a `ctx` parameter. By mocking it, we can test commands without
    actually connecting to Discord.
    """
    ctx = MagicMock(spec=commands.Context)
    ctx.bot = mock_bot
    ctx.guild = mock_guild
    ctx.author = mock_author
    ctx.send = AsyncMock()
    ctx.typing = MagicMock(return_value=AsyncMock())
    ctx.prefix = "<>"
    ctx.invoked_with = "play"
    return ctx


@pytest.fixture
def music_cog(mock_bot):
    """
    Create a real Music cog instance wired to the mock bot.

    We import Music here (not at the top) to ensure the settings
    patch is active before any module-level code runs.
    """
    from cogs.music import Music
    return Music(mock_bot)
