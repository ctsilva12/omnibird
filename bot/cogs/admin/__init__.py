
from .commands.restart import restart
from .commands.clearcache import clearcache
from .commands.setrarity import setrarity
from .commands.addguild import addguild
from .commands.grant import grant
from .commands.setadmin import setadmin
from .commands.speak import speak

class admin:
    restart = staticmethod(restart)
    clearcache = staticmethod(clearcache)
    setrarity = staticmethod(setrarity)
    addguild = staticmethod(addguild)
    grant = staticmethod(grant)
    setadmin = staticmethod(setadmin)
    speak = staticmethod(speak)