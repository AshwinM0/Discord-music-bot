"""
Tests for the _is_url() SSRF guard in cogs/music.py.

This is a critical security function. It must:
  - Accept only legitimate YouTube URLs
  - Reject everything else (other domains, internal IPs, plain text)

If any of these tests fail, the bot may be vulnerable to SSRF attacks
where a user tricks it into fetching internal network resources.
"""

from core.search import is_url as _is_url


# ── YouTube URLs that SHOULD be accepted ─────────────────────────────

def test_youtube_standard_url():
    assert _is_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True


def test_youtube_without_www():
    assert _is_url("https://youtube.com/watch?v=dQw4w9WgXcQ") is True


def test_youtube_short_url():
    assert _is_url("https://youtu.be/dQw4w9WgXcQ") is True


def test_youtube_music_url():
    assert _is_url("https://music.youtube.com/watch?v=dQw4w9WgXcQ") is True


def test_youtube_http():
    """HTTP (not HTTPS) YouTube URLs should still be accepted."""
    assert _is_url("http://www.youtube.com/watch?v=dQw4w9WgXcQ") is True


def test_youtube_playlist():
    assert _is_url("https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf") is True


# ── URLs that MUST be rejected (SSRF vectors) ───────────────────────

def test_random_website_rejected():
    assert _is_url("https://evil.com/malware") is False


def test_localhost_rejected():
    assert _is_url("http://localhost:8080/admin") is False


def test_internal_ip_rejected():
    assert _is_url("http://192.168.1.1/config") is False


def test_aws_metadata_rejected():
    """This is the classic cloud SSRF attack vector."""
    assert _is_url("http://169.254.169.254/latest/meta-data/") is False


def test_ftp_rejected():
    assert _is_url("ftp://files.example.com/song.mp3") is False


def test_file_protocol_rejected():
    assert _is_url("file:///etc/passwd") is False


# ── Plain text (search queries) that must NOT look like URLs ─────────

def test_plain_search_query():
    assert _is_url("demons imagine dragons") is False


def test_empty_string():
    assert _is_url("") is False


def test_just_a_word():
    assert _is_url("rickroll") is False


def test_partial_url_no_scheme():
    """A domain without http:// should not be treated as a URL."""
    assert _is_url("youtube.com/watch?v=abc") is False
