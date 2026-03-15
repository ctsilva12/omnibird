import re
import emoji
from languages import l

def canonical(name: str) -> str:
    if emoji.is_emoji(name):
        name = emoji.demojize(name, delimiters=(":", ":"))
    m = re.search(r":(\w+):", name)
    return m.group(1) if m else name.strip()

TOKEN_RE = re.compile(r"<:\w+:\d+>|:\w+:|\S+")

def parse_mfw_values(input_str: str) -> list[tuple[str, int]]:
    item_dict: dict[str, int] = {}

    parts = [p.strip() for p in input_str.split(",")] if "," in input_str else [input_str.strip()]

    for part in parts:
        if not part:
            continue

        tokens = TOKEN_RE.findall(part)
        i = 0
        while i < len(tokens):
            token = tokens[i]

            if token.isdigit() and i + 1 < len(tokens):
                quantity = int(token)
                name = tokens[i + 1]
                i += 2
            elif i + 1 < len(tokens) and tokens[i + 1].isdigit():
                quantity = int(tokens[i + 1])
                name = token
                i += 2
            else:
                quantity = 1
                name = token
                i += 1

            if quantity <= 0:
                raise ValueError(l.text("quantity", "invalid"))

            canon = canonical(name)
            item_dict[canon] = item_dict.get(canon, 0) + quantity

    return list(item_dict.items())