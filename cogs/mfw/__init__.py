from .commands.reminder import reminder
from .commands.harvest import harvest
from .commands.inventory import inventory
from .commands.harvest import harvest
from .commands.sell import sell
from .commands.selldupes import selldupes
from .commands.almanac import almanac
from .commands.transfer import transfer
from .commands.check import check
from .commands.trade import trade

class mfw:
    reminder = staticmethod(reminder)
    harvest = staticmethod(harvest)
    inventory = staticmethod(inventory)
    selldupes = staticmethod(selldupes)
    transfer = staticmethod(transfer)
    sell = staticmethod(sell)
    almanac = staticmethod(almanac)
    check = staticmethod(check)
    trade = staticmethod(trade)