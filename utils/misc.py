from pathlib import Path

def discover_cogs(base: str = "cogs") -> dict[str, str]:
    base_path = Path(base)
    result: dict[str, str] = {}

    for item in base_path.iterdir():
        if not item.is_dir():
            continue

        if not (item / "cog.py").exists():
            continue

        result[item.name] = f"{base}.{item.name}.cog"

    return result