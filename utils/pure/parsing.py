import re
import emoji

def canonical(name: str) -> str:
    if emoji.is_emoji(name):
        name = emoji.demojize(name, delimiters=(":", ":"))
    m = re.search(r":(\w+):", name)
    return m.group(1) if m else name.strip()

def parse_mfw_values(input_str: str) -> list[tuple[str, int]]:
    item_dict: dict[str, int] = {}

    # Normalize input: split by commas first, then strip each part
    parts = [p.strip() for p in input_str.split(",")]

    for part in parts:
        if not part:
            continue

        tokens = part.split()
        if not tokens:
            continue

        quantity = 1
        name: str

        if len(tokens) == 1:
            name = tokens[0]

        elif len(tokens) == 2:
            if tokens[0].isdigit():
                quantity = int(tokens[0])
                name = tokens[1]
            elif tokens[1].isdigit():
                quantity = int(tokens[1])
                name = tokens[0]
            else:
                raise ValueError(f"Invalid MFW format: {part}")

        else:
            raise ValueError(f"Too many tokens in part: {part}")

        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        canon = canonical(name)
        item_dict[canon] = item_dict.get(canon, 0) + quantity

    return list(item_dict.items())
