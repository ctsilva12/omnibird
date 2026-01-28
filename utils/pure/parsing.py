import re

def canonical(name: str) -> str:
    m = re.search(r"<:([^:]+):\d+>", name)
    return m.group(1) if m else name.strip()

def parse_mfw_values(input_str: str) -> list[tuple[str, int]]:
    items = []

    for part in input_str.split(","):
        tokens = part.strip().split()
        if not tokens:
            continue
        name = None
        quantity = 1
        if len(tokens) == 1:
            name = tokens[0]
            items.append((canonical(name), quantity))
            continue
        elif len(tokens) > 2:
            raise ValueError
        try:
            quantity = int(tokens[0])
            name = tokens[-1]
        except ValueError:
            name = tokens[0]
            try:
                quantity = int(tokens[1])
            except ValueError:
                quantity = 1

        if (name is None):
            raise ValueError
        items.append((canonical(name), quantity))
    return items