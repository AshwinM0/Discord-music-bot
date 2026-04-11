import pytest
from core.database import GuildConfig


@pytest.mark.asyncio
async def test_get_guild_config_empty():
    config = await GuildConfig.get_or_none(guild_id=999)
    assert config is None


@pytest.mark.asyncio
async def test_create_and_update_guild_config():
    # Create a new config
    config = await GuildConfig.create(guild_id=123, music_channel_id=456)
    assert config.music_channel_id == 456
    assert config.dj_role_id is None

    # Update with DJ role
    config.dj_role_id = 789
    await config.save()

    refreshed = await GuildConfig.get(guild_id=123)
    assert refreshed.music_channel_id == 456
    assert refreshed.dj_role_id == 789


@pytest.mark.asyncio
async def test_get_or_create():
    # First call creates
    config, created = await GuildConfig.get_or_create(guild_id=444)
    assert created is True
    assert config.music_channel_id is None

    # Second call retrieves
    config2, created2 = await GuildConfig.get_or_create(guild_id=444)
    assert created2 is False
    assert config2.guild_id == config.guild_id


@pytest.mark.asyncio
async def test_clear_values():
    config = await GuildConfig.create(guild_id=555, music_channel_id=666)

    config.music_channel_id = None
    await config.save()

    refreshed = await GuildConfig.get(guild_id=555)
    assert refreshed.music_channel_id is None
