from enum import Enum
from languages import l
import random
c = "blackjack"

class Suit(Enum):
    HEARTS = l.text(c, "hearts")
    SPADES  = l.text(c, "spades")
    CLUBS = l.text(c, "clubs")
    DIAMONDS = l.text(c, "diamonds")

class Rank(Enum):
    ONE = (1, l.text(c, "one"))
    TWO = (2, l.text(c, "two"))
    THREE = (3, l.text(c, "three"))
    FOUR = (4, l.text(c, "four"))
    FIVE = (5, l.text(c, "five"))
    SIX = (6, l.text(c, "six"))
    SEVEN = (7, l.text(c, "seven"))
    EIGHT = (8, l.text(c, "eight"))
    NINE = (9, l.text(c, "nine"))
    TEN = (10, l.text(c, "ten"))
    JACK = (10, l.text(c, "jack"))
    QUEEN = (10, l.text(c, "queen"))
    KING = (10, l.text(c, "king"))
    ACE = (11, l.text(c, "ace"))

    def __init__(self, numeric_value, name):
        self._value_ = numeric_value  
        self.localized_name = name

class Card:
    def __init__(self, rank : Rank, suit : Suit):
        self.rank = rank
        self.suit = suit

    def __repr__(self):
        return f"{self.rank.localized_name} {l.text("of")} {self.suit.value}"

def generate_deck() -> list[Card]: 
    deck = [Card(rank, suit) for suit in Suit for rank in Rank]
    random.shuffle(deck)
    return deck