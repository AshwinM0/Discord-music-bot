import time
import discord
from discord.utils import get
from typing import TYPE_CHECKING
from discord.ext import commands
from core.resource import resources

if TYPE_CHECKING:
    from cogs.music import Music

class MusicControlView(discord.ui.View):
    """Persistent UI view for music playback control."""
    
    def __init__(self, cog: "Music"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Play / Pause", emoji="⏯️", style=discord.ButtonStyle.primary, custom_id="music:play_pause")
    async def toggle_play(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice = get(self.cog.bot.voice_clients, guild=interaction.guild)
        if not voice:
            embed = discord.Embed(description=resources.get("music.nothing_playing"), color=discord.Color.orange())
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if not interaction.user.voice or interaction.user.voice.channel != voice.channel:
            embed = discord.Embed(description=resources.get("music.not_in_bot_vc"), color=discord.Color.red())
            return await interaction.response.send_message(embed=embed, ephemeral=True)
            
        if voice.is_playing():
             voice.pause()
             current = self.cog.now_playing.get(interaction.guild.id)
             title = f" **{current['title']}**" if current else ""
             if current:
                 current["paused_at"] = time.time()
             embed = discord.Embed(description=resources.get("music.paused", title=title), color=discord.Color.orange())
             await interaction.response.send_message(embed=embed)
        elif voice.is_paused():
             voice.resume()
             current = self.cog.now_playing.get(interaction.guild.id)
             title = f" **{current['title']}**" if current else ""
             if current and current.get("paused_at"):
                 current["start_time"] += time.time() - current["paused_at"]
                 current["paused_at"] = 0
             embed = discord.Embed(description=resources.get("music.resumed", title=title), color=discord.Color.green())
             await interaction.response.send_message(embed=embed)
        else:
             embed = discord.Embed(description=resources.get("music.nothing_playing"), color=discord.Color.orange())
             await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Skip", emoji="⏭️", style=discord.ButtonStyle.secondary, custom_id="music:skip")
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice = get(self.cog.bot.voice_clients, guild=interaction.guild)

        if voice and (not interaction.user.voice or interaction.user.voice.channel != voice.channel):
            embed = discord.Embed(description=resources.get("music.not_in_bot_vc"), color=discord.Color.red())
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if voice and (voice.is_playing() or voice.is_paused()):
            # Dynamic attribute name matches legacy music cog logic
            setattr(self.cog, f'_skip_req_{interaction.guild.id}', True)
            skipped = self.cog.now_playing.get(interaction.guild.id)
            skipped_text = f" **{skipped['title']}**" if skipped else ""
            voice.stop()
            embed = discord.Embed(description=resources.get("music.skipped", title=skipped_text), color=discord.Color.green())
            await interaction.response.send_message(embed=embed)
        else:
             embed = discord.Embed(description=resources.get("music.nothing_playing"), color=discord.Color.orange())
             await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Stop & Clear", emoji="🟥", style=discord.ButtonStyle.primary, custom_id="music:stop")
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice = get(self.cog.bot.voice_clients, guild=interaction.guild)

        if voice and (not interaction.user.voice or interaction.user.voice.channel != voice.channel):
            embed = discord.Embed(description=resources.get("music.not_in_bot_vc"), color=discord.Color.red())
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        self.cog._get_queue(interaction.guild.id).clear()
        self.cog.now_playing.pop(interaction.guild.id, None)
        self.cog.loop_modes.pop(interaction.guild.id, None)
        if voice and (voice.is_playing() or voice.is_paused()):
            setattr(self.cog, f'_skip_req_{interaction.guild.id}', True)
            voice.stop()
            embed = discord.Embed(description=resources.get("music.stopped"), color=discord.Color.red())
            await interaction.response.send_message(embed=embed)
        else:
             embed = discord.Embed(description=resources.get("music.nothing_playing"), color=discord.Color.orange())
             await interaction.response.send_message(embed=embed, ephemeral=True)


class DuplicateConfirmView(discord.ui.View):
    """Confirmation prompt when a user tries to queue a duplicate track."""

    def __init__(self, cog: "Music", ctx: commands.Context, query: str):
        super().__init__(timeout=30)
        self.cog = cog
        self.ctx = ctx
        self.query = query
        self.responded = False

    async def on_timeout(self) -> None:
        if not self.responded:
            embed = discord.Embed(description=resources.get("music.dup_timeout"), color=discord.Color.greyple())
            try:
                await self.message.edit(embed=embed, view=None)
            except Exception:
                pass

    @discord.ui.button(label="Add Anyway", emoji="✅", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(
                embed=discord.Embed(description=resources.get("music.dup_only_author_confirm"), color=discord.Color.red()),
                ephemeral=True,
            )
        self.responded = True
        # Delegate to the cog's internal enqueue logic
        await interaction.response.defer()
        await interaction.delete_original_response()
        await self.cog._enqueue(self.ctx, self.query)

    @discord.ui.button(label="Cancel", emoji="❌", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(
                embed=discord.Embed(description=resources.get("music.dup_only_author_cancel"), color=discord.Color.red()),
                ephemeral=True,
            )
        self.responded = True
        embed = discord.Embed(description=resources.get("music.dup_cancelled"), color=discord.Color.greyple())
        await interaction.response.edit_message(embed=embed, view=None)
