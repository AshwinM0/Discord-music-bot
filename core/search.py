import re
from urllib.parse import urlparse
import yt_dlp as youtube_dl

# ── Constants ────────────────────────────────────────────────────────

YDL_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": "True",
}

_YOUTUBE_RE = re.compile(
    r"^https?://(www\.)?(youtube\.com|youtu\.be|music\.youtube\.com)/"
)

# ── Search Logic ─────────────────────────────────────────────────────

def is_url(query: str) -> bool:
    """Check if *query* is a valid YouTube URL (rejects non-YT domains to prevent SSRF)."""
    parsed = urlparse(query)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False
    return bool(_YOUTUBE_RE.match(query))


def search_youtube(query: str) -> tuple[str, str, str, int]:
    """Search YouTube for *query* and return ``(title, audio_url, video_url, duration)``."""
    with youtube_dl.YoutubeDL(YDL_OPTS) as ydl:
        if is_url(query):
            info = ydl.extract_info(query, download=False)
        else:
            info = ydl.extract_info(f"ytsearch:{query} lyrics video", download=False)["entries"][0]

        return (
            info.get("title", "Unknown"),
            info.get("url", ""),
            info.get("webpage_url", ""),
            info.get("duration", 0)
        )
