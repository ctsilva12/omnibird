from collections import defaultdict
from enum import Enum
from languages import l
from dataclasses import dataclass, field
import random

#todo implement split later (maybe, if it doesnt break the economy)
c = "cards"
d = "suits"
class Suit(Enum):
    HEARTS = l.text(c, d, "hearts")
    SPADES  = l.text(c, d, "spades")
    CLUBS = l.text(c, d, "clubs")
    DIAMONDS = l.text(c, d, "diamonds")

d = "ranks"
class Rank(Enum):
    TWO = (2, l.text(c, d, "two"))
    THREE = (3, l.text(c, d, "three"))
    FOUR = (4, l.text(c, d, "four"))
    FIVE = (5, l.text(c, d, "five"))
    SIX = (6, l.text(c, d, "six"))
    SEVEN = (7, l.text(c, d, "seven"))
    EIGHT = (8, l.text(c, d, "eight"))
    NINE = (9, l.text(c, d, "nine"))
    TEN = (10, l.text(c, d, "ten"))
    JACK = (10, l.text(c, d, "jack"))
    QUEEN = (10, l.text(c, d, "queen"))
    KING = (10, l.text(c, d, "king"))
    ACE = (11, l.text(c, d, "ace"))

    def __init__(self, numeric_value, emoji):
        self._value_ = numeric_value  
        self.emoji = emoji

class Card:
    def __init__(self, rank : Rank, suit : Suit):
        self.rank = rank
        self.suit = suit

    def __repr__(self):
        return f"{self.suit.value}{self.rank.emoji}"

def generate_deck() -> list[Card]: 
    deck = [Card(rank, suit) for suit in Suit for rank in Rank]
    random.shuffle(deck)
    return deck

@dataclass 
class Value:
    total: int = 0
    soft : bool = False
    is_blackjack : bool = False

def calculate_value(cards : list[Card]) -> Value:
    total = 0
    aces = 0
    soft = False
    for card in cards:
        if (card.rank == Rank.ACE): aces += 1
        total += card.rank.value
    
    if len(cards) == 2 and total == 21:
        return Value(total, soft, is_blackjack=True)

    while(total > 21 and aces > 0):
        aces -= 1;
        total -= 10
    if aces > 0:
        soft = True
    return Value(total, soft)

def can_split(cards : list[Card]) -> bool:
    if len(cards) != 2: return False
    return cards[0].rank == cards[1].rank

def compare_hands(player : Value, dealer : Value) -> bool|None:
    """
    True = player won,
    False = player lost,
    None = tie
    """
    if player.total > 21:
        return False
    if dealer.total > 21:
        return True
    
    if player.total != dealer.total:
        return player.total > dealer.total
    else:
        if player.is_blackjack:
            if dealer.is_blackjack: return None
            else: return True
        else:
            if dealer.is_blackjack: return False
            else: return None

@dataclass
class Hand:
    cards: list[Card] = field(default_factory=list)
    bet: int = 0
    settled: bool = False
    busted: bool = False

c = "blackjack"
def render_hand(hand : Hand, is_dealer: bool = False, reveal_dealer_cards = False) -> str:
    cards_list : list[str] = []
    value : Value|None = None
    if is_dealer and len(hand.cards) == 2 and not reveal_dealer_cards:
        cards_list.append(hand.cards[0].__repr__())
        cards_list.append(l.text(c, "mystery_card"))
        value = calculate_value([hand.cards[0]])
    else:
        for card in hand.cards:
            cards_list.append(card.__repr__())

    cards_str = " ".join(cards_list)
    if value is None: value = calculate_value(hand.cards)

    value_str = "".join([
    f"{l.text(c, "value")}: {f"{l.text(c, "soft")} " if value.soft else ""}",
    f"{value.total if not value.is_blackjack else l.text(c, "blackjack")}",
    ])
    
    parts : list[str] = [cards_str, value_str]
    if not is_dealer:
        bet_str = f"{l.text(c, "bet")}: {hand.bet} {l.text("_symbols", "coin_icon")}"
        parts.append(bet_str)
    return " | ".join(parts)

@dataclass
class GameState:
    players_and_bets : list[tuple[int, int]]
    payout : float = 1/1
    blackjack_payout : float = 7/4
    finished : bool = False
    deck : list[Card] = field(default_factory=generate_deck)
    dealer_hand : Hand = field(init=False)
    dealer_value: Value = field(init=False)
    players_hand : dict[int, Hand] = field(init=False)
    results : dict[int, bool|None] = field(init=False)

    def __post_init__(self):
        self.dealer_hand = Hand([self.deck.pop(), self.deck.pop()], 0, False)
        self.dealer_value = calculate_value(self.dealer_hand.cards)
        self.players_hand = {}
        self.results = {}
        for player, bet in self.players_and_bets:
           hand = Hand(
               cards = [self.deck.pop(), self.deck.pop()],
               bet = bet,
           )
           self.players_hand[player] = hand

    def hit(self, player : int) -> Value:
        hand = self.players_hand[player]
        if hand.settled:
            raise ValueError("Can't hit anymore")
        hand.cards.append(self.deck.pop())
        value = calculate_value(hand.cards)
        if value.total > 21: 
            hand.settled = True
            hand.busted = True
        return value

    # MAKE SURE TO CHECK IF THE PLAYER HAS ENOUGH MONEY FOR THIS
    def double_down(self, player : int) -> Value:
        hand = self.players_hand[player]
        if hand.settled:
            raise ValueError("Can't double down anymore")
        hand.bet *= 2
        hand.cards.append(self.deck.pop())
        value = calculate_value(hand.cards)
        hand.settled = True
        if value.total > 21:
            hand.busted = True
        return value
    
    def stand(self, player : int) -> Value:
        hand = self.players_hand[player]
        hand.settled = True
        return calculate_value(hand.cards)     

    def dealer_can_hit(self, hit_soft_17=False) -> bool:
        value = self.dealer_value
        if value.total < 17:
            return True
        
        if value.total == 17 and value.soft and hit_soft_17:
            return True
        else: return False

    def dealer_play(self) -> Value:
        self.dealer_hand.cards.append(self.deck.pop())
        self.dealer_value = calculate_value(self.dealer_hand.cards)
        if self.dealer_value.total > 21:
            self.dealer_hand.settled = True
            self.dealer_hand.busted = True
        return self.dealer_value
    
    def calculate_payouts(self) -> dict[int, int]:
        payouts : dict[int, int] = defaultdict(int)
        for player, hand in self.players_hand.items():
            player_value = calculate_value(hand.cards)
            dealer_value = calculate_value(self.dealer_hand.cards)
            bet = hand.bet

            result = compare_hands(player_value, dealer_value)
            self.results[player] = result
            if result == True: 
                if player_value.is_blackjack: payouts[player] += round((hand.bet * self.blackjack_payout))
                else: payouts[player] += round(hand.bet * (self.payout))
            elif result == False: payouts[player] += -bet
            else: payouts[player] += 0
        return payouts



    

