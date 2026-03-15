from .commands.jumbo import jumbo
from .commands.ping import ping

class misc:
    jumbo = staticmethod(jumbo)
    ping = staticmethod(ping)