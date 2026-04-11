from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    DISCORD_TOKEN: str
    SPOTIFY_CLIENT_ID: Optional[str] = None
    SPOTIFY_CLIENT_SECRET: Optional[str] = None

    # Music Bot Settings
    COMMAND_PREFIX: str = "<>"
    MAX_QUEUE_SIZE: int = 50
    INACTIVITY_TIMEOUT: int = 120
    FFMPEG_OPTS: dict = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": "-vn",
    }

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

settings = Settings()
