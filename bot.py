import discord

from bot_main import MusicBot
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = MusicBot(command_prefix=settings.COMMAND_PREFIX, intents=intents)

if __name__ == "__main__":
    logger.info("Starting bot...")
    bot.run(settings.DISCORD_TOKEN)