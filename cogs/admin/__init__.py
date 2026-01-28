
from .commands.restart import restart
from .commands.clearcache import clearcache
from .commands.setrarity import setrarity
from .commands.addguild import addguild
from .commands.grant import grant

class admin:
    restart = staticmethod(restart)
    clearcache = staticmethod(clearcache)
    setrarity = staticmethod(setrarity)
    addguild = staticmethod(addguild)
    grant = staticmethod(grant)