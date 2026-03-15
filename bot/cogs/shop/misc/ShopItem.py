from dataclasses import dataclass, field

@dataclass
class ShopItem:
    id: int
    name: str
    description: str
    price: int
    type: str
    payload: dict = field(default_factory=dict)