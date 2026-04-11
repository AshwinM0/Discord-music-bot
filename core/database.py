import logging
from pathlib import Path

from tortoise import Tortoise, fields
from tortoise.models import Model

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "bot.db"

# ── ORM Models ──────────────────────────────────────────────────────

class GuildConfig(Model):
    """Per-server configuration stored in the database."""

    guild_id = fields.BigIntField(primary_key=True)
    music_channel_id = fields.BigIntField(null=True)
    dj_role_id = fields.BigIntField(null=True)

    class Meta:
        table = "guild_config"

    def __repr__(self) -> str:
        return f"<GuildConfig guild={self.guild_id}>"


# ── Lifecycle helpers ───────────────────────────────────────────────

TORTOISE_ORM = {
    "connections": {
        "default": f"sqlite://{DB_PATH}",
    },
    "apps": {
        "models": {
            "models": ["core.database"],
            "default_connection": "default",
        },
    },
}


async def init_db() -> None:
    """Initialize Tortoise-ORM and generate schemas."""
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()
    logger.info("Database connected at %s", DB_PATH)


async def close_db() -> None:
    """Close all Tortoise-ORM connections."""
    await Tortoise.close_connections()
    logger.info("Database connection closed")
