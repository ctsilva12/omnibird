import os
import json
import asyncio
from pathlib import Path
import warnings

class _SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"
    
class LocaleManager:
    def __init__(self, path=None, default_lang="en"):
        if path is None:
            path = Path(__file__).parent / "locale"
        elif isinstance(path, str):
            path = Path(path)
        self.path = path
        self.TEXT = {}
        self.LANG = default_lang
        self.load_all()

    def load_all(self):
        self.TEXT.clear()
        for filename in self.path.iterdir():
            if not filename.name.endswith(".json"):
                continue
            lang_code = filename.stem.lower()
            with open(filename, "r", encoding="utf-8") as f:
                self.TEXT[lang_code] = json.load(f)
        # fallback
        self.LANG = "dev" if "dev" in self.TEXT else self.LANG

    def resolve_auto(self, fmt: dict[str, str]) -> dict[str, str]:
        symbols = self.TEXT[self.LANG].get("_symbols", {})
        if not isinstance(symbols, dict):
            raise TypeError("_symbols must be a dict")
        return {**symbols, **fmt}

    def text(self, *path, **fmt):
        cur = self.TEXT[self.LANG]
        walked = []
        for key in path:
            walked.append(str(key))
            if not isinstance(cur, dict):
                raise TypeError(f"Path {'/'.join(walked[:-1])} is not a dict")
            if key not in cur:
                warnings.warn(f"Missing key [{key}] at {'/'.join(walked)}")
                return key
            cur = cur[key]

        if not isinstance(cur, str):
            raise TypeError(f"Text at {'/'.join(walked)} is not a string")
        return cur.format_map(_SafeDict(self.resolve_auto(fmt)))

    def text_all(self, *path, **fmt):
        cur = self.TEXT[self.LANG]
        walked = []
        for key in path:
            walked.append(str(key))
            if not isinstance(cur, dict):
                raise TypeError(f"Path {'/'.join(walked[:-1])} is not a dict")
            if key not in cur:
                raise KeyError(f"Missing key at {'/'.join(walked)}")
            cur = cur[key]

        if not isinstance(cur, dict):
            raise TypeError(f"Text at {'/'.join(walked)} is not a dict")
        values = []
        for k, v in cur.items():
            if not isinstance(v, str):
                raise TypeError(f"Value at {'/'.join(walked + [str(k)])} is not a string")
            values.append(v.format_map(_SafeDict(**self.resolve_auto(fmt))))
        return values


class LocaleReloader:
    def __init__(self, manager: LocaleManager, poll_interval=2.0):
        self.manager = manager
        self.poll_interval = poll_interval
        self._mtimes = {f.name: f.stat().st_mtime
                        for f in self.manager.path.iterdir() if f.name.endswith(".json")}
        self._task = None
        self._stopping = False

    async def _loop(self):
        while not self._stopping:
            await asyncio.sleep(self.poll_interval)
            for filename in self.manager.path.iterdir():
                if not filename.name.endswith(".json"):
                    continue
                try:
                    mtime = filename.stat().st_mtime
                except OSError:
                    continue
                prev = self._mtimes.get(filename.name)
                if prev is None or mtime > prev:
                    self.manager.load_all()
                    self._mtimes[filename.name] = mtime
                    print(f"[locale] Reloaded {filename.name}")

    def start(self):
        if self._task and not self._task.done():
            return
        self._stopping = False
        self._task = asyncio.create_task(self._loop())

    def stop(self):
        self._stopping = True
        if self._task:
            self._task.cancel()


l = LocaleManager()
locale_reloader = LocaleReloader(l)