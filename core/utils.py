def make_progress_bar(elapsed: float, duration: float, length: int = 15) -> str:
    """Generate a text-based progress bar."""
    if duration <= 0:
        return "🔘" + "▬" * (length - 1)
    
    ratio = min(max(elapsed / duration, 0.0), 1.0)
    pos = int(ratio * length)
    bar = ["▬"] * length
    
    if pos < length:
        bar[pos] = "🔘"
    else:
        bar[-1] = "🔘"
        
    return "".join(bar)
