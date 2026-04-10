import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

RESOURCE_DIR = Path(__file__).parent.parent / "resources"

class ResourceManager:
    def __init__(self):
        self.messages: dict[str, Any] = {}
        self._load_messages()

    def _load_messages(self) -> None:
        messages_file = RESOURCE_DIR / "messages.json"
        if not messages_file.exists():
            logger.error("messages.json not found at %s", messages_file)
            return

        try:
            with open(messages_file, "r", encoding="utf-8") as f:
                self.messages = json.load(f)
        except Exception as e:
            logger.error("Failed to parse messages.json: %s", e)

    def get(self, key: str, **kwargs) -> str:
        """Retrieve a nested dictionary string by dot-notation (e.g. 'music.now_playing')."""
        keys = key.split(".")
        current = self.messages
        for k in keys:
            if isinstance(current, dict):
                current = current.get(k)
            else:
                return f"[Missing String: {key}]"
        
        if not isinstance(current, str):
            return f"[Missing String: {key}]"
            
        try:
            return current.format(**kwargs)
        except KeyError as e:
            logger.warning("Missing format argument %s for string '%s'", e, key)
            return current
        except Exception as e:
            logger.warning("Formatting error for string '%s': %s", key, e)
            return current

# Singleton instance
resources = ResourceManager()
