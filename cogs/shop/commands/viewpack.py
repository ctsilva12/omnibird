import discord
import db
from languages import l
from utils.PageSwitcher import PageSwitcher
from collections import defaultdict, OrderedDict
import utils.pure.formatting as formatting

async def viewpack(self, ctx, pack_name: str = "", requested_page : int|str|None = None):
    target = discord.user.BaseUser
    owned_mfws = await db.fetch_all("""
        SELECT m.id, COALESCE(i.quantity, 0), m.guild_id, m.name, m.rarity_id
        FROM mfws m
        LEFT JOIN inventory i ON i.mfw_id = m.id AND i.user_id = %s
        INNER JOIN rarities r on m.rarity_id = r.id
        ORDER BY m.guild_id ASC, m.rarity_id DESC, m.name ASC
    """, (target.id,))
    
    guilds = await db.fetch_all("SELECT id, name from guilds", cache=True)
    rarities = await db.fetch_all("SELECT * FROM rarities", cache=True, ttl=9999)
    rarity_map = {r[0]: r[1] for r in rarities}
    rarity_id_map = {r[1]: r[0] for r in rarities} # for sorting in PageSwitcher later
    guild_map = {g[0]: g[1] for g in guilds}
    rarity_map[0] = l.text("unknown").capitalize()
    
    totals: OrderedDict[str, defaultdict[str, int]] = OrderedDict()
    user_totals: OrderedDict[str, defaultdict[str, int]] = OrderedDict()
    almanac_list: OrderedDict[str, defaultdict[str, list[dict]]] = OrderedDict()

    for g_id, g_name in guild_map.items():
        totals[g_name] = defaultdict(int)
        user_totals[g_name] = defaultdict(int)
        almanac_list[g_name] = defaultdict(list)

    for mfw_id, quantity, guild_id, name, rarity_id in owned_mfws:
        guild_name = guild_map[guild_id]
        rarity_name = rarity_map[rarity_id]

        emoji = None
        guild_obj = self.bot.get_guild(guild_id) if guild_id else None
        if guild_obj:
            emoji = discord.utils.get(guild_obj.emojis, name=name) or name
        else:
            emoji = name

        almanac_list[guild_name][rarity_name].append({
            "id": mfw_id,
            "name": name,
            "quantity": quantity,
            "owned": True if quantity > 0 else False,
            "text": f"{emoji} {f"(x{quantity})" if quantity > 0 else ""}"
        })

        totals[guild_name][rarity_name] += 1
        if quantity > 0:
            user_totals[guild_name][rarity_name] += 1

    total_pages = len(guild_map)
    page = 1
    if requested_page is not None:
        if isinstance(requested_page, int):
            page = max(1, min(requested_page, total_pages))
        else: 
            try:
                page = int(requested_page)
            except ValueError:
                try:
                    page = list(guild_map.values()).index(requested_page) + 1
                except ValueError:
                    page = 1

    async def get_almanac_page(page : int):
        total_pages = len(totals)
        page = max(1, min(page, total_pages))
        
        if total_pages <= 0:
            e = discord.Embed(
                description=l.text("almanac", "no_mfws"),
                color=discord.Color.gold()
            )
            e.set_footer(text=f"0/0 • {l.text("page", page=0, total_pages=0)}", icon_url="https://cdn.discordapp.com/emojis/1425964337377443840.webp")
            return e, 0
        
        guild_name = list(totals.keys())[page-1]
        page = max(1, min(page, total_pages))
        page_slice = almanac_list[guild_name]

        embed = discord.Embed(
            colour=discord.Color.gold()
        )

        for rarity_name in sorted(page_slice.keys(), key=lambda n: rarity_id_map.get(n, 0), reverse=True):
            items = page_slice[rarity_name]

            not_owned_lines = [it["text"] for it in items if not it.get("owned")]
            owned_lines = [it["text"] for it in items if it.get("owned")]

            not_chunks = formatting.chunk_by_length(not_owned_lines) if not_owned_lines else []
            owned_chunks = formatting.chunk_by_length(owned_lines) if owned_lines else []

            first_field_for_this_rarity = True
            for group_chunks, icon in ((owned_chunks, ":white_check_mark:"), (not_chunks, ":x:")):
                if not group_chunks:
                    continue
                for i, chunk in enumerate(group_chunks):
                    value = f"{icon} {chunk}" if i == 0 else chunk

                    if first_field_for_this_rarity:
                        name = f"{rarity_name} ({user_totals[guild_name].get(rarity_name, 0)}/{totals[guild_name].get(rarity_name, 0)})"
                        first_field_for_this_rarity = False
                    else:
                        name = ""

                    embed.add_field(name=name, value=value, inline=False)

        user_count = sum(user_totals.get(guild_name, {}).values())
        total_count = sum(totals.get(guild_name, {}).values())
        percentage = round(user_count/total_count*100, 1) if total_count is not 0 else 100
        embed.title = l.text("almanac", "title", name=target.display_name, guild=guild_name, percentage=percentage)
        embed.set_footer(text=f"{user_count}/{total_count} • {l.text("page", page=page, total_pages=total_pages)}", icon_url="https://cdn.discordapp.com/emojis/1425964337377443840.webp")
        return embed, total_pages

    paginator = PageSwitcher(ctx, get_almanac_page)
    await paginator.navigate(page)