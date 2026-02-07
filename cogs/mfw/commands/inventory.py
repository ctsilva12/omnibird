import discord
import db
import utils.pure.formatting as formatting
from typing import Any
from languages import l
from utils.PageSwitcher import PageSwitcher

async def inventory(self, ctx, user: discord.Member | None = None, requested_page : int|None = None):
    target = user or ctx.author
    page = 1
    if requested_page is not None:
            try:
                page = int(requested_page)
            except ValueError:
                page = 1
    async with db.transaction() as cur:
        await cur.execute("""
            SELECT i.mfw_id, i.quantity, m.guild_id, m.name, m.rarity_id
            FROM inventory i
            INNER JOIN mfws m ON i.mfw_id = m.id
            INNER JOIN rarities r on m.rarity_id = r.id
            WHERE i.user_id = %s
            ORDER BY m.rarity_id DESC, i.quantity DESC, m.name ASC
        """, (target.id,))
        owned_mfws = await cur.fetchall()

    if not owned_mfws:
        await ctx.send(l.text("inventory", "no_mfws", name=target.display_name))
        return
    
    all_mfws = await db.fetch_all("SELECT * FROM mfws", cache=True)
    rarities = await db.fetch_all("SELECT * FROM rarities", cache=True, ttl=9999)
    rarity_map = {r[0]: r[1] for r in rarities}
    rarity_map[0] = l.text("unknown").capitalize()

    total_global = 0
    global_totals = {r[0]: 0 for r in rarities}
    for _, _, _, rarity_id, *_ in all_mfws:
        if rarity_id in global_totals:
            global_totals[rarity_id] += 1
            total_global += 1

    
    entries: list[dict[str, Any]] = []
    total_user = 0
    user_totals = {r[0]: 0 for r in rarities}
    for mfw_id, quantity, guild_id, name, rarity_id in owned_mfws:
        guild = self.bot.get_guild(guild_id) if guild_id else None
        emoji = None
        if guild:
            try:
                emoji = discord.utils.get(guild.emojis, name=name)
            except Exception:
                emoji = None
        display = f"{emoji} (x{quantity})" if emoji else f":{name}: (x{quantity})"
        user_totals[rarity_id] += 1
        entries.append({"rarity_id": rarity_id, "text": display})
        total_user += 1


    async def get_inventory_page(page : int):
        total_pages = PageSwitcher.compute_total_pages(len(entries), self.MAX_MFWS_PER_PAGE)
        page = max(1, min(page, total_pages))

        if total_pages <= 0:
            e = discord.Embed(
                title=l.text("inventory", "title", name=target.display_name, percentage=0.00),
                description=l.text("inventory", "no_mfws", name=target.display_name),
                color=discord.Color.gold()
            )
            e.set_footer(text=f"0/{total_global} • {l.text("page", page=0, total_pages=0)}", icon_url="https://cdn.discordapp.com/emojis/1425964337377443840.webp")
            return e, 0
        
        start = (page - 1) * self.MAX_MFWS_PER_PAGE
        end = start + self.MAX_MFWS_PER_PAGE
        page_slice = entries[start:end]

        embed = discord.Embed(
            title=l.text("inventory", "title", name=target.display_name, percentage=round(total_user/total_global*100, 2)),
            colour=discord.Color.gold()
        )

        grouped_on_page: dict[int, list[str]] = {}
        for item in page_slice:
            rid = item["rarity_id"] or 0
            grouped_on_page.setdefault(rid, []).append(item["text"])

        for rarity_id in sorted(grouped_on_page.keys(), reverse=True):
            lines = grouped_on_page[rarity_id]
            chunks = formatting.chunk_by_length(lines) or [""]
            for i, chunk in enumerate(chunks):
                if i == 0:
                    name = f"{rarity_map.get(rarity_id, l.text("unknown").capitalize())} ({user_totals.get(rarity_id, 0)}/{global_totals.get(rarity_id, 0)})"
                else: name = ""
                embed.add_field(name=name, value=chunk, inline=False)
        embed.set_footer(text=f"{total_user}/{total_global} • {l.text("page", page=page, total_pages=total_pages)}", icon_url="https://cdn.discordapp.com/emojis/1425964337377443840.webp")
        return embed, total_pages

    paginator = PageSwitcher(ctx, get_inventory_page)
    await paginator.navigate(page)