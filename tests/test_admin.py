import pytest
import discord
from unittest.mock import MagicMock
from cogs.admin import Admin
from core.database import GuildConfig

@pytest.fixture
def admin_cog(mock_bot):
    return Admin(mock_bot)

@pytest.mark.asyncio
async def test_admin_check_no_guild(admin_cog, mock_ctx):
    mock_ctx.guild = None
    assert await admin_cog.cog_check(mock_ctx) is False

@pytest.mark.asyncio
async def test_admin_check_not_admin(admin_cog, mock_ctx):
    mock_ctx.author.guild_permissions.administrator = False
    assert await admin_cog.cog_check(mock_ctx) is False
    mock_ctx.send.assert_called_once()
    embed = mock_ctx.send.call_args[1]["embed"]
    assert "Administrator" in embed.description

@pytest.mark.asyncio
async def test_admin_check_is_admin(admin_cog, mock_ctx):
    mock_ctx.author.guild_permissions.administrator = True
    assert await admin_cog.cog_check(mock_ctx) is True

@pytest.mark.asyncio
async def test_setchannel_set(admin_cog, mock_ctx):
    mock_channel = MagicMock(spec=discord.TextChannel)
    mock_channel.id = 555
    mock_channel.mention = "<#555>"
    
    await admin_cog.setchannel.callback(admin_cog, mock_ctx, channel=mock_channel)
    
    config = await GuildConfig.get(guild_id=mock_ctx.guild.id)
    assert config.music_channel_id == 555
    mock_ctx.send.assert_called_once()

@pytest.mark.asyncio
async def test_setchannel_clear(admin_cog, mock_ctx):
    await GuildConfig.create(guild_id=mock_ctx.guild.id, music_channel_id=333)
    
    await admin_cog.setchannel.callback(admin_cog, mock_ctx, channel=None)
    
    config = await GuildConfig.get(guild_id=mock_ctx.guild.id)
    assert config.music_channel_id is None
    mock_ctx.send.assert_called_once()
    
@pytest.mark.asyncio
async def test_setdj_set(admin_cog, mock_ctx):
    mock_role = MagicMock(spec=discord.Role)
    mock_role.id = 777
    mock_role.mention = "<@&777>"
    
    await admin_cog.setdj.callback(admin_cog, mock_ctx, role=mock_role)
    
    config = await GuildConfig.get(guild_id=mock_ctx.guild.id)
    assert config.dj_role_id == 777
    mock_ctx.send.assert_called_once()

@pytest.mark.asyncio
async def test_setdj_clear(admin_cog, mock_ctx):
    await GuildConfig.create(guild_id=mock_ctx.guild.id, dj_role_id=111)
    
    await admin_cog.setdj.callback(admin_cog, mock_ctx, role=None)
    
    config = await GuildConfig.get(guild_id=mock_ctx.guild.id)
    assert config.dj_role_id is None
    mock_ctx.send.assert_called_once()
