from discord.ext import commands
from languages import l
from . import gambling

c = "commands"
async def is_valid_bet(ctx, bet: int|None, max_bet: int) -> bool:
    if bet is None:
        await ctx.send(l.text("quantity", "none"))
        return False
    if bet > max_bet:
        await ctx.send(l.text("too_much_gambling", coins=max_bet))
        return False
    return True
class Gambling(commands.Cog):

    bot: commands.Bot
    def __init__(self, bot):
        self.bot = bot
        self.MAX_COINFLIP_BET = 1000
        self.MAX_BLACKJACK_BET = 500

    @commands.command(name=l.text(c, "coinflip"), description=l.text("coinflip", "description"))
    async def coinflip_cmd(self, ctx, choice: str|None=None, bet: int|None=None):
        if (await is_valid_bet(ctx, bet, self.MAX_COINFLIP_BET)):
            await gambling.coinflip(self, ctx, choice, bet)
    
    @commands.command(name=l.text(c, "russianroulette"), description=l.text("russianroulette", "description"))
    async def russianroulette_cmd(self, ctx, confirmation: str | None, mfw: str = '777'):
        await gambling.russianroulette(self, ctx, confirmation, mfw)
    
    @commands.command(name=l.text(c, "blackjack"), description=l.text("blackjack", "description"))
    async def blackjack_cmd(self, ctx, bet: int|None = None):
        if (await is_valid_bet(ctx, bet, self.MAX_BLACKJACK_BET)):
            await gambling.blackjack(self, ctx, bet)
            
async def setup(bot):
    await bot.add_cog(Gambling(bot))