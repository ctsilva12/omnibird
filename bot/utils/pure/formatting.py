from languages import l
from datetime import timedelta

def join_with_and(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} {l.text("and")} {items[1]}"
    return ", ".join(items[:-1]) + f" {l.text("and")} {items[-1]}"

def format_duration(delta : timedelta|int) -> str:
    if isinstance(delta, timedelta):
        total_seconds = int(delta.total_seconds())
    else:
        total_seconds = int(delta)

    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days} {l.text("days") if days != 1 else l.text("day")}")
    if hours > 0:
        parts.append(f"{hours} {l.text("hours") if hours != 1 else l.text("hour")}")
    if minutes > 0:
        parts.append(f"{minutes} {l.text("minutes") if minutes != 1 else l.text("minute")}")
    if seconds > 0 or not parts:
        parts.append(f"{seconds} {l.text("seconds") if seconds != 1 else l.text("second")}")

    return join_with_and(parts)

def make_emoji(id : int, name : str, is_animated=False) -> str:
    if is_animated:
        return f"<a:{name}:{id}>"
    else: return f"<:{name}:{id}>"

def chunk_by_length(items, max_len=1024, sep=", ") -> list[str]:
    chunks = []
    current = ""

    for item in items:
        candidate = item if not current else current + sep + item
        if len(candidate) > max_len:
            chunks.append(current)
            current = item
        else:
            current = candidate

    if current:
        chunks.append(current)
    return chunks

def chunk_string(
    s: str,
    limit: int = 1990,
    seps: tuple[str, ...]|str = ("\n", ",",),
):
    if isinstance(seps, str): seps = tuple(seps)
    start = 0
    n = len(s)

    while start < n:
        remaining = n - start
        if remaining <= limit:
            yield s[start:]
            break

        cut = None

        for sep in seps:
            idx = s.rfind(sep, start, start + limit)
            if idx != -1:
                cut = idx + len(sep)
                break

        if cut is None:
            cut = start + limit

        yield s[start:cut]
        start = cut
