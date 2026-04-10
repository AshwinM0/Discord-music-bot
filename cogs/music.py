import asyncio
import random
import time
from collections import deque

import discord
import requests
import yt_dlp as youtube_dl
from discord import FFmpegPCMAudio
from discord.ext import commands
from discord.utils import get

from core.logger import get_logger
from core.resource import resources

logger = get_logger(__name__)

FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

YDL_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": "True",
}

MAX_QUEUE_SIZE = 50


def _search(query: str) -> tuple[str, str, str, int]:
    """Search YouTube for *query* and return ``(title, audio_url, video_url, duration)``."""
    with youtube_dl.YoutubeDL(YDL_OPTS) as ydl:
        try:
            requests.get(query)
        except Exception:
            info = ydl.extract_info(f"ytsearch:{query} audio", download=False)["entries"][0]
        else:
            info = ydl.extract_info(query, download=False)

        return info.get("title", "Unknown"), info.get("url", ""), info.get("webpage_url", ""), info.get("duration", 0)

def make_progress_bar(elapsed: float, duration: float, length: int = 15) -> str:
    """Generate a text-based progress bar."""
    if duration == 0:
        return "🔘" + "▬" * (length - 1)
    ratio = min(max(elapsed / duration, 0.0), 1.0)
    pos = int(ratio * length)
    bar = ["▬"] * length
    if pos < length:
        bar[pos] = "🔘"
    else:
        bar[-1] = "🔘"
    return "".join(bar)

class MusicControlView(discord.ui.View):
    def __init__(self, cog: "Music"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Play / Pause", emoji="⏯️", style=discord.ButtonStyle.primary, custom_id="music:play_pause")
    async def toggle_play(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice = get(self.cog.bot.voice_clients, guild=interaction.guild)
        if not voice:
            embed = discord.Embed(description=resources.get("music.nothing_playing"), color=discord.Color.orange())
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
        if voice and (voice.is_playing() or voice.is_paused()):
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


class Music(commands.Cog):
    """Music playback commands with per-guild queue isolation."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.queues: dict[int, deque] = {}
        self.now_playing: dict[int, dict] = {}  # guild_id -> {title, video_url, query}
        self.volumes: dict[int, float] = {}     # guild_id -> float (0.0 to 1.0)
        self.loop_modes: dict[int, str] = {}    # guild_id -> "off", "track", "queue"

    # ── Helpers ──────────────────────────────────────────────────

    async def _send_embed(self, ctx: commands.Context, description: str, title: str | None = None, color: discord.Color = discord.Color.blurple(), view: discord.ui.View | None = None) -> None:
        """Helper to send a quick styled embed message."""
        embed = discord.Embed(description=description, color=color)
        if title:
            embed.title = title
        if view:
            await ctx.send(embed=embed, view=view)
        else:
            await ctx.send(embed=embed)

    def _get_queue(self, guild_id: int) -> deque:
        """Lazily initialise and return the queue for *guild_id*."""
        if guild_id not in self.queues:
            self.queues[guild_id] = deque()
        return self.queues[guild_id]

    async def _ensure_voice(self, ctx: commands.Context) -> discord.VoiceClient | None:
        """Join the author's VC if needed. Returns the voice client or *None* on failure."""
        voice = get(self.bot.voice_clients, guild=ctx.guild)

        if not ctx.author.voice:
            if voice:
                await self._send_embed(ctx, resources.get("music.already_in_vc"), color=discord.Color.red())
            else:
                await self._send_embed(ctx, resources.get("music.join_vc_first"), color=discord.Color.red())
            return None

        author_channel = ctx.author.voice.channel

        if voice is None:
            return await author_channel.connect()

        if voice.channel != author_channel:
            await voice.disconnect()
            return await author_channel.connect()

        return voice

    async def _play_next(self, ctx: commands.Context) -> None:
        """Pop the next track from the guild queue and play it."""
        guild_id = ctx.guild.id
        queue = self._get_queue(guild_id)
        voice = get(self.bot.voice_clients, guild=ctx.guild)

        if not voice:
            self.now_playing.pop(guild_id, None)
            return

        last_track = self.now_playing.pop(guild_id, None)
        loop_mode = self.loop_modes.get(guild_id, "off")
        skip_req = getattr(self, f'_skip_req_{guild_id}', False)

        if last_track and last_track.get("query"):
            if loop_mode == "track" and not skip_req:
                queue.appendleft(last_track["query"])
            elif loop_mode == "queue":
                queue.append(last_track["query"])

        setattr(self, f'_skip_req_{guild_id}', False)

        if queue:
            query = queue.popleft()
            title, source, video_url, duration = _search(query)
            logger.info("Now playing '%s' in guild %s", title, guild_id)

            self.now_playing[guild_id] = {
                "title": title, 
                "video_url": video_url, 
                "query": query, 
                "duration": duration,
                "start_time": time.time(),
                "paused_at": 0
            }

            vol = self.volumes.get(guild_id, 1.0)
            audio_source = discord.PCMVolumeTransformer(FFmpegPCMAudio(source, **FFMPEG_OPTS), volume=vol)

            voice.play(
                audio_source,
                after=lambda e: asyncio.run_coroutine_threadsafe(
                    self._play_next(ctx), self.bot.loop
                ),
            )
            track_text = f"[{title}]({video_url})" if video_url else title
            embed = discord.Embed(
                description=resources.get("music.now_playing", track_text=track_text),
                color=discord.Color.green(),
            )
            if queue:
                embed.set_footer(text=resources.get("music.queue_remaining", len=len(queue)))
            await ctx.send(embed=embed, view=MusicControlView(self))
        else:
            self.now_playing.pop(guild_id, None)
            logger.debug("Queue empty for guild %s — waiting 120s before leaving", guild_id)
            await asyncio.sleep(120)
            voice = get(self.bot.voice_clients, guild=ctx.guild)
            if voice and not voice.is_playing() and not voice.is_paused() and not queue:
                await self._send_embed(ctx, resources.get("music.inactivity_leave"))
                await voice.disconnect()
                logger.info("Left VC due to inactivity in guild %s", guild_id)

    # ── Commands ─────────────────────────────────────────────────

    @commands.command()
    async def join(self, ctx: commands.Context) -> None:
        """Join the voice channel you are in."""
        voice = get(self.bot.voice_clients, guild=ctx.guild)

        if not ctx.author.voice:
            if voice:
                await self._send_embed(ctx, resources.get("music.already_in_vc"), color=discord.Color.red())
            else:
                await self._send_embed(ctx, resources.get("music.join_vc_first"), color=discord.Color.red())
            return

        author_channel = ctx.author.voice.channel

        if voice is None:
            await author_channel.connect()
            logger.info("Joined %s in guild %s", author_channel, ctx.guild.id)
            await self._send_embed(ctx, resources.get("music.joined", channel=author_channel.name))
        elif voice.channel == author_channel:
            await self._send_embed(ctx, resources.get("music.already_in_my_vc"), color=discord.Color.orange())
        else:
            await voice.disconnect()
            await author_channel.connect()
            logger.info("Moved to %s in guild %s", author_channel, ctx.guild.id)
            await self._send_embed(ctx, resources.get("music.moved", channel=author_channel.name))

    @commands.command()
    async def leave(self, ctx: commands.Context) -> None:
        """Leave the current voice channel."""
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        if voice:
            self._get_queue(ctx.guild.id).clear()
            self.now_playing.pop(ctx.guild.id, None)
            self.loop_modes.pop(ctx.guild.id, None)
            await voice.disconnect()
            logger.info("Left VC in guild %s", ctx.guild.id)
            await self._send_embed(ctx, resources.get("music.left_vc"))
        else:
            await self._send_embed(ctx, resources.get("music.not_in_vc"), color=discord.Color.red())

    async def _enqueue(self, ctx: commands.Context, query: str) -> None:
        """Internal method to enqueue a track and start playback if idle."""
        queue = self._get_queue(ctx.guild.id)
        queue.append(query)
        logger.debug("Enqueued '%s' for guild %s", query, ctx.guild.id)

        voice = await self._ensure_voice(ctx)
        if voice is None:
            queue.pop()
            return

        if voice.is_playing() or voice.is_paused():
            position = len(queue)
            await self._send_embed(
                ctx,
                resources.get("music.enqueued", query=query, position=position),
                color=discord.Color.green(),
                view=MusicControlView(self)
            )
        else:
            async with ctx.typing():
                await self._play_next(ctx)

    @commands.command()
    async def play(self, ctx: commands.Context, *, query: str) -> None:
        """Play a song by URL or search query."""
        queue = self._get_queue(ctx.guild.id)

        # ── Guard: queue cap ──
        if len(queue) >= MAX_QUEUE_SIZE:
            await self._send_embed(
                ctx,
                resources.get("music.queue_full", max=MAX_QUEUE_SIZE),
                color=discord.Color.red(),
            )
            return

        # ── Guard: duplicate confirmation ──
        normalized = query.strip().lower()
        current = self.now_playing.get(ctx.guild.id)
        in_queue = any(existing.strip().lower() == normalized for existing in queue)
        is_playing = current and current.get("query", "").strip().lower() == normalized

        if in_queue or is_playing:
            view = DuplicateConfirmView(self, ctx, query)
            status = "playing" if is_playing else "in the queue"
            embed = discord.Embed(
                description=resources.get("music.dup_prompt", query=query, status=status),
                color=discord.Color.orange(),
            )
            msg = await ctx.send(embed=embed, view=view)
            view.message = msg
            return

        await self._enqueue(ctx, query)

    @commands.command()
    async def skip(self, ctx: commands.Context) -> None:
        """Skip the current track."""
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        if voice and (voice.is_playing() or voice.is_paused()):
            skipped = self.now_playing.get(ctx.guild.id)
            skipped_text = f" **{skipped['title']}**" if skipped else ""
            setattr(self, f'_skip_req_{ctx.guild.id}', True)
            voice.stop()  # triggers _play_next via the `after` callback
            await self._send_embed(ctx, resources.get("music.skipped", title=skipped_text), color=discord.Color.green())
        else:
            await self._send_embed(ctx, resources.get("music.nothing_playing"), color=discord.Color.orange())

    @commands.command()
    async def pause(self, ctx: commands.Context) -> None:
        """Pause the current track."""
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        if voice and voice.is_playing():
            voice.pause()
            current = self.now_playing.get(ctx.guild.id)
            if current:
                current["paused_at"] = time.time()
                title = f" **{current['title']}**"
            else:
                title = ""
            await self._send_embed(ctx, resources.get("music.paused", title=title), color=discord.Color.orange())
        elif voice and voice.is_paused():
            await self._send_embed(ctx, resources.get("music.already_paused"), color=discord.Color.orange())
        else:
            await self._send_embed(ctx, resources.get("music.nothing_playing"), color=discord.Color.orange())

    @commands.command()
    async def resume(self, ctx: commands.Context) -> None:
        """Resume a paused track."""
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        if voice and voice.is_paused():
            voice.resume()
            current = self.now_playing.get(ctx.guild.id)
            if current:
                if current.get("paused_at"):
                    current["start_time"] += time.time() - current["paused_at"]
                    current["paused_at"] = 0
                title = f" **{current['title']}**"
            else:
                title = ""
            await self._send_embed(ctx, resources.get("music.resumed", title=title), color=discord.Color.green())
        elif voice and voice.is_playing():
            await self._send_embed(ctx, resources.get("music.already_playing"), color=discord.Color.orange())
        else:
            await self._send_embed(ctx, resources.get("music.nothing_to_resume"), color=discord.Color.orange())

    @commands.command()
    async def stop(self, ctx: commands.Context) -> None:
        """Stop playback and clear the queue."""
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        self._get_queue(ctx.guild.id).clear()
        self.now_playing.pop(ctx.guild.id, None)
        self.loop_modes.pop(ctx.guild.id, None)
        if voice and (voice.is_playing() or voice.is_paused()):
            setattr(self, f'_skip_req_{ctx.guild.id}', True)
            voice.stop()
            await self._send_embed(ctx, resources.get("music.stopped"), color=discord.Color.red())
        else:
            await self._send_embed(ctx, resources.get("music.nothing_playing"), color=discord.Color.orange())

    @commands.command(name="np", aliases=["nowplaying"])
    async def now_playing_cmd(self, ctx: commands.Context) -> None:
        """Show what's currently playing."""
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        current = self.now_playing.get(ctx.guild.id)

        if not current or not voice:
            await self._send_embed(ctx, resources.get("music.nothing_playing"), color=discord.Color.orange())
            return

        track_text = f"[{current['title']}]({current['video_url']})" if current.get("video_url") else current["title"]
        status = resources.get("music.queue_status_paused") if voice.is_paused() else resources.get("music.queue_status_playing")
        embed = discord.Embed(
            description=f"{status}: **{track_text}**",
            color=discord.Color.orange() if voice.is_paused() else discord.Color.green(),
        )
        
        # Calculate progress
        if current.get("duration"):
            elapsed = time.time() - current["start_time"] if not current.get("paused_at") else current["paused_at"] - current["start_time"]
            bar = make_progress_bar(elapsed, current["duration"])
            fmt_elapsed = time.strftime('%M:%S', time.gmtime(elapsed))
            fmt_duration = time.strftime('%M:%S', time.gmtime(current["duration"]))
            embed.description += f"\n\n{bar} `{fmt_elapsed} / {fmt_duration}`"

        queue = self._get_queue(ctx.guild.id)
        if queue:
            embed.set_footer(text=f"Up next: {queue[0]} · {len(queue)} in queue")
        await ctx.send(embed=embed, view=MusicControlView(self))

    @commands.command(name="q", aliases=["queue"])
    async def queue(self, ctx: commands.Context) -> None:
        """Show the current song queue."""
        guild_id = ctx.guild.id
        q = self._get_queue(guild_id)
        current = self.now_playing.get(guild_id)

        if not q and not current:
            await self._send_embed(ctx, resources.get("music.queue_empty"), color=discord.Color.orange())
            return

        parts = []
        if current:
            track_text = f"[{current['title']}]({current['video_url']})" if current.get("video_url") else current["title"]
            voice = get(self.bot.voice_clients, guild=ctx.guild)
            icon = "⏸" if voice and voice.is_paused() else "🎶"
            parts.append(resources.get("music.queue_now", icon=icon, track_text=track_text))

        if q:
            entries = [resources.get("music.queue_item", index=i+1, track=track) for i, track in enumerate(q)]
            parts.append("\n".join(entries))

        embed = discord.Embed(
            title=resources.get("music.queue_title"),
            description="\n".join(parts),
            color=discord.Color.blurple(),
        )
        embed.set_footer(text=resources.get("music.queue_footer", len=len(q), loop=self.loop_modes.get(guild_id, 'off')))
        await ctx.send(embed=embed)

    @commands.command()
    async def volume(self, ctx: commands.Context, vol: int) -> None:
        """Change the player volume (0-100)."""
        if vol < 0 or vol > 100:
            await self._send_embed(ctx, resources.get("music.vol_invalid"), color=discord.Color.red())
            return
        
        guild_id = ctx.guild.id
        self.volumes[guild_id] = vol / 100.0
        
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        if voice and voice.source and hasattr(voice.source, 'volume'):
            voice.source.volume = self.volumes[guild_id]

        await self._send_embed(ctx, resources.get("music.vol_set", vol=vol), color=discord.Color.green())

    @commands.command()
    async def loop(self, ctx: commands.Context, mode: str = "") -> None:
        """Set loop mode: off, track, queue."""
        mode = mode.lower()
        if mode not in ("off", "track", "queue"):
            await self._send_embed(ctx, resources.get("music.loop_usage"), color=discord.Color.orange())
            return
        
        self.loop_modes[ctx.guild.id] = mode
        icons = {"off": "➡", "track": "🔂", "queue": "🔁"}
        await self._send_embed(ctx, resources.get("music.loop_set", icon=icons[mode], mode=mode), color=discord.Color.green())

    @commands.command()
    async def shuffle(self, ctx: commands.Context) -> None:
        """Shuffle the current queue."""
        q = self._get_queue(ctx.guild.id)
        if len(q) < 2:
            await self._send_embed(ctx, resources.get("music.shuffle_fail"), color=discord.Color.orange())
            return
            
        lst = list(q)
        random.shuffle(lst)
        self.queues[ctx.guild.id] = deque(lst)
        await self._send_embed(ctx, resources.get("music.shuffled"), color=discord.Color.green())

    @commands.command()
    async def remove(self, ctx: commands.Context, position: int) -> None:
        """Remove a specific track from the queue."""
        q = self._get_queue(ctx.guild.id)
        if position < 1 or position > len(q):
            await self._send_embed(ctx, resources.get("music.remove_fail", len=len(q)), color=discord.Color.red())
            return
            
        lst = list(q)
        removed = lst.pop(position - 1)
        self.queues[ctx.guild.id] = deque(lst)
        await self._send_embed(ctx, resources.get("music.removed", removed=removed), color=discord.Color.green())

    @commands.command()
    async def clear(self, ctx: commands.Context) -> None:
        """Clear the entire queue."""
        q = self._get_queue(ctx.guild.id)
        if not q:
            await self._send_embed(ctx, resources.get("music.queue_empty"), color=discord.Color.orange())
            return
        q.clear()
        await self._send_embed(ctx, resources.get("music.queue_cleared"), color=discord.Color.green())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Music(bot))
