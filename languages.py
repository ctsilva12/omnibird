
import json
import os
from utils.symbols import COIN_ICON, MFWS

LOCALE_PATH = "locale"
TEXT = {}
for filename in os.listdir(LOCALE_PATH):
    if not filename.endswith(".json"):
        continue
    lang_code = filename.rsplit(".", 1)[0].lower()
    with open(os.path.join(LOCALE_PATH, filename), "r", encoding="utf-8") as f:
        TEXT[lang_code] = json.load(f)

# more languages to be added later
LANG = "dev" if "dev" in TEXT else "en"

def resolve_auto(fmt: dict[str, str]) -> dict[str, str]:
    return {**MFWS, **fmt}

def text(*path, **fmt):
    cur = TEXT[LANG]
    walked = []

    for key in path:
        walked.append(str(key))
        if not isinstance(cur, dict):
            raise TypeError(f"Path {'/'.join(walked[:-1])} is not a dict")
        if key not in cur:
            raise KeyError(f"Missing key at {'/'.join(walked)}")
        cur = cur[key]

    if cur is None:
        raise ValueError(f"Text at {'/'.join(walked)} is null")

    if not isinstance(cur, str):
        raise TypeError(f"Text at {'/'.join(walked)} is not a string")

    try:
        return cur.format(**resolve_auto(fmt))
    except KeyError as e:
        raise KeyError(
            f"Missing format key {e} for text at {'/'.join(walked)}"
        ) from e
    
def text_all(*path, **fmt):
    cur = TEXT[LANG]
    walked = []

    for key in path:
        walked.append(str(key))
        if not isinstance(cur, dict):
            raise TypeError(f"Path {'/'.join(walked[:-1])} is not a dict")
        if key not in cur:
            raise KeyError(f"Missing key at {'/'.join(walked)}")
        cur = cur[key]

    if cur is None:
        raise ValueError(f"Text at {'/'.join(walked)} is null")

    if not isinstance(cur, dict):
        raise TypeError(f"Text at {'/'.join(walked)} is not a dict")

    values = []
    for k, v in cur.items():
        if v is None:
            raise ValueError(f"Value at {'/'.join(walked + [str(k)])} is null")
        if not isinstance(v, str):
            raise TypeError(
                f"Value at {'/'.join(walked + [str(k)])} is not a string"
            )
        try:
            values.append(v.format(**resolve_auto(fmt)))
        except KeyError as e:
            raise KeyError(
                f"Missing format key {e} for text at {'/'.join(walked + [str(k)])}"
            ) from e

    return values