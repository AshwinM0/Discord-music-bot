import discord

from bot_main import MusicBot
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

bot = MusicBot(command_prefix="<>", intents=discord.Intents.all())

if __name__ == "__main__":
    logger.info("Starting bot...")
    bot.run(settings.DISCORD_TOKEN)