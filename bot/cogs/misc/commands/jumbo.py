
import discord
import utils.services.dbutils as dbutils
import utils.services.discord.discordutils as discordutils
import db
import utils.pure.formatting as formatting
from languages import l

c = "jumbo"
def build_link(mfw_id: int, is_animated: bool) -> str:
    ext = "gif" if is_animated else "webp"
    return f"https://cdn.discordapp.com/emojis/{mfw_id}.{ext}"

async def jumbo(self, ctx, mfw: str):
    try:
        mfws, _, _, _ = await discordutils.parse_and_validate_mfws(self.bot, None, mfw, check_ownership=False)
    except ValueError as e:
        await ctx.send(str(e))
        return e
    
    mfw_id, _, _, _, is_animated = mfws[0]
    await ctx.send(build_link(mfw_id, is_animated))
