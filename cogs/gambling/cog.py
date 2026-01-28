from discord.ext import commands
from languages import l
from . import gambling

c = "commands"
class Gambling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name=l.text(c, "coinflip"), description=l.text("coinflip", "description"))
    async def coinflip_cmd(self, ctx, choice=None, quantity=None):
        await gambling.coinflip(self, ctx, choice, quantity)
    
    @commands.command(name=l.text(c, "russianroulette"), description=l.text("russianroulette", "description"))
    async def russianroulette_cmd(self, ctx, confirmation: str | None, mfw: str = '777'):
        await gambling.russianroulette(self, ctx, confirmation, mfw)
    
    @commands.command(name=l.text(c, "blackjack"), description=l.text("blackjack", "description"))
    async def blackjack_cmd(self, ctx, bet: int|None = None):
        await gambling.blackjack(self, ctx, bet)
            
async def setup(bot):
    await bot.add_cog(Gambling(bot))