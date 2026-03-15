from pathlib import Path
from typing import Any
import os

def get_env_var(var: str, boolean=True) -> Any:
    if boolean: return os.getenv(var, "0").lower() in ("1", "true", "yes")
    else: return os.getenv(var, None)

def discover_cogs(base_path: Path|None = None) -> dict[str, str]:
    if base_path is None: base_path = Path(__file__).parent.parent / "cogs"
    if not base_path.exists():
        raise FileNotFoundError(f"Cogs folder not found: {base_path}")
    result: dict[str, str] = {}

    for item in base_path.iterdir():
        if not item.is_dir():
            continue

        if not (item / "cog.py").exists():
            continue

        result[item.name] = f"cogs.{item.name}.cog"

    return result

# from old responses.py
def get_response(message):
    p_message = message.lower()

    # if p_message == 'roll':
        # return str(random.randint(1, 6))
    
    # elif re.search(r'\test\b', p_message) or re.search(r'\test\b', p_message):
        # return "test"