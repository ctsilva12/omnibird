from .commands.balance import balance
from .commands.give import give
from .commands.leaderboard import leaderboard

class economy:
    balance = staticmethod(balance)
    give = staticmethod(give)
    leaderboard = staticmethod(leaderboard)