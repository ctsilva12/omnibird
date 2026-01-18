import os
import json
import asyncio


class LocaleManager:
    def __init__(self, path="locale", default_lang="en"):
        self.path = path
        self.TEXT = {}
        self.LANG = default_lang
        self.load_all()

    def load_all(self):
        self.TEXT.clear()
        for filename in os.listdir(self.path):
            if not filename.endswith(".json"):
                continue
            lang_code = filename.rsplit(".", 1)[0].lower()
            with open(os.path.join(self.path, filename), "r", encoding="utf-8") as f:
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
                raise KeyError(f"Missing key at {'/'.join(walked)}")
            cur = cur[key]

        if not isinstance(cur, str):
            raise TypeError(f"Text at {'/'.join(walked)} is not a string")
        return cur.format(**self.resolve_auto(fmt))

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
            values.append(v.format(**self.resolve_auto(fmt)))
        return values
    
class LocaleReloader:
    def __init__(self, manager: LocaleManager, poll_interval=2.0):
        self.manager = manager
        self.poll_interval = poll_interval
        self._mtimes = {f: os.path.getmtime(os.path.join(manager.path, f))
                        for f in os.listdir(manager.path) if f.endswith(".json")}
        self._task = None
        self._stopping = False

    async def _loop(self):
        while not self._stopping:
            await asyncio.sleep(self.poll_interval)
            for filename in os.listdir(self.manager.path):
                if not filename.endswith(".json"):
                    continue
                path = os.path.join(self.manager.path, filename)
                try:
                    mtime = os.path.getmtime(path)
                except OSError:
                    continue
                prev = self._mtimes.get(filename)
                if prev is None or mtime > prev:
                    self.manager.load_all()
                    self._mtimes[filename] = mtime
                    print(f"[locale] Reloaded {filename}")

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