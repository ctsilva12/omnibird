import discord
from languages import l
import db
from utils.PageSwitcher import PageSwitcher

ALIASES = {
    "mfw": 1,
    "mfd": 2,
}
TOTAL_PAGES = len(ALIASES)
c = "leaderboard"
async def leaderboard(self, ctx, index: str|int|None):
        if isinstance(index, str):
            index = int(ALIASES.get(index.lower().strip(), 1))

        if not isinstance(index, int):
            index = 1
        view = PageSwitcher(
            source=ctx,
            get_page=leaderboard_router,
            start_index=(index or 1),
        )
        await view.send()
        

async def leaderboard_router(index: int) -> tuple[discord.Embed, int]:
    if index == 1:
        embed = await mfw_leaderboard()
    elif index == 2 :
        embed = await money_leaderboard()
    else: embed = await mfw_leaderboard()

    embed.set_footer(text=l.text("page", page=index, total_pages=TOTAL_PAGES))
    return embed, TOTAL_PAGES

async def money_leaderboard() -> discord.Embed:
    leaderboard = await db.fetch_all("SELECT id, coins FROM users ORDER BY coins DESC LIMIT 10")
    description = ""
    for index, row in enumerate(leaderboard, start=1):
        user_id = row[0]
        coins = row[1]
        description += l.text(c, "money_line", index=index, user_id=user_id, coins=coins)

    embed = discord.Embed(
        title=l.text(c, "money_title"),
        description=description,
        color=discord.Color.gold(),
    )
    return embed

async def mfw_leaderboard() -> discord.Embed:
    query = """SELECT u.id AS user_id, COUNT(i.mfw_id) as mfws_owned, (
        SELECT COUNT(*) AS total_mfws from mfws WHERE enabled = TRUE AND rarity_id != 0
    ) AS total_mfws
    from users u 
    LEFT JOIN inventory i ON u.id = i.user_id
    GROUP BY u.id
    ORDER BY mfws_owned DESC
    LIMIT 10"""

    leaderboard = await db.fetch_all(query)

    description = ""
    total_mfws = 0
    for index, row in enumerate(leaderboard, start=1):
        user_id, mfws_owned, total_mfws = row
        percentage = round(mfws_owned/total_mfws*100, 2) if total_mfws != 0 else 0
        description += l.text(c, "mfw_line", 
        index=index, user_id=user_id, mfws_owned=mfws_owned, percentage=percentage)

    embed = discord.Embed(
        title=l.text(c, "mfw_title", total_mfws=total_mfws),
        description=description,
        color=discord.Color.gold()
    )
    return embed
