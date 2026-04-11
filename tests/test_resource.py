"""
Tests for core/resource.py — the ResourceManager.

These tests verify that:
  - The JSON file loads correctly
  - Dot-notation key lookup works
  - String interpolation with {placeholders} works
  - Missing keys return a safe fallback instead of crashing
  - Missing format arguments don't crash the bot
"""

from core.resource import ResourceManager


def _make_manager() -> ResourceManager:
    """Create a fresh ResourceManager that reads the real messages.json."""
    return ResourceManager()


# ── Loading ──────────────────────────────────────────────────────────

def test_load_messages():
    """The JSON file should load and populate the messages dict."""
    rm = _make_manager()
    assert isinstance(rm.messages, dict)
    assert len(rm.messages) > 0, "messages.json should not be empty"


def test_top_level_keys():
    """The JSON should have our expected top-level sections."""
    rm = _make_manager()
    for key in ("errors", "help", "music"):
        assert key in rm.messages, f"Missing top-level key: {key}"


# ── Simple key retrieval ─────────────────────────────────────────────

def test_get_simple_key():
    """A plain key with no placeholders should return the exact string."""
    rm = _make_manager()
    result = rm.get("music.left_vc")
    assert "Left the voice channel" in result


def test_get_nested_key():
    """Dot-notation should traverse multiple levels."""
    rm = _make_manager()
    result = rm.get("errors.unknown_comm_title")
    assert result == "Unknown Command"


# ── String interpolation ─────────────────────────────────────────────

def test_get_with_format_args():
    """Placeholders like {vol} should be replaced with provided kwargs."""
    rm = _make_manager()
    result = rm.get("music.vol_set", vol=50)
    assert "50" in result
    assert "%" in result


def test_get_with_multiple_args():
    """Keys with multiple placeholders should interpolate all of them."""
    rm = _make_manager()
    result = rm.get("music.enqueued", query="Demons", position=3)
    assert "Demons" in result
    assert "3" in result


# ── Error handling ───────────────────────────────────────────────────

def test_get_missing_key():
    """A nonexistent key should return a safe fallback, not crash."""
    rm = _make_manager()
    result = rm.get("this.does.not.exist")
    assert "[Missing String:" in result


def test_get_missing_shallow_key():
    """A nonexistent top-level key should also return the fallback."""
    rm = _make_manager()
    result = rm.get("nonexistent")
    assert "[Missing String:" in result


def test_get_missing_format_arg():
    """If a format arg is missing, return the raw template without crashing."""
    rm = _make_manager()
    # music.vol_set expects {vol} — we deliberately omit it
    result = rm.get("music.vol_set")
    # Should return the raw template string, not crash
    assert isinstance(result, str)
    assert "{vol}" in result or "Volume" in result
