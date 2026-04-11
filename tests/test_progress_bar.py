"""
Tests for make_progress_bar() in cogs/music.py.

The progress bar is a text-based visualisation shown in the "Now Playing"
embed. It uses 🔘 as the playhead and ▬ as the track.
"""

from cogs.music import make_progress_bar


def test_start_position():
    """At elapsed=0 the playhead should be at the very beginning."""
    bar = make_progress_bar(0, 100)
    assert bar.startswith("🔘")


def test_end_position():
    """At elapsed=duration the playhead should be at the very end."""
    bar = make_progress_bar(100, 100)
    assert bar.endswith("🔘")


def test_midpoint():
    """At elapsed=duration/2 the playhead should be roughly in the middle."""
    bar = make_progress_bar(50, 100, length=10)
    pos = bar.index("🔘")
    # Should be around index 5 (middle of a 10-char bar)
    assert 3 <= pos <= 7, f"Playhead at position {pos}, expected ~5"


def test_zero_duration():
    """Zero duration should not crash — should return a valid bar."""
    bar = make_progress_bar(0, 0)
    assert "🔘" in bar
    assert isinstance(bar, str)


def test_negative_elapsed():
    """Negative elapsed should clamp to 0 (start of bar)."""
    bar = make_progress_bar(-10, 100)
    assert bar.startswith("🔘")


def test_elapsed_exceeds_duration():
    """Elapsed > duration should clamp to the end."""
    bar = make_progress_bar(200, 100)
    assert bar.endswith("🔘")


def test_custom_length():
    """The bar should respect a custom length parameter."""
    bar = make_progress_bar(50, 100, length=10)
    # Count characters (🔘 is 1 char, ▬ is 1 char)
    char_count = len(bar)
    assert char_count == 10, f"Expected 10 chars, got {char_count}"


def test_default_length():
    """Default bar length should be 15 characters."""
    bar = make_progress_bar(50, 100)
    assert len(bar) == 15
