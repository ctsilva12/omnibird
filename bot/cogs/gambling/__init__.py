from .commands.coinflip import coinflip
from .commands.russianroulette import russianroulette
from .commands.blackjack import blackjack

class gambling:
    coinflip = staticmethod(coinflip)
    russianroulette = staticmethod(russianroulette)
    blackjack = staticmethod(blackjack)