import discord
from discord.ext import commands
import random
import db
import helpers
from dataclasses import dataclass, field
import json
from typing import Dict, Tuple
from utils.Pagination import Pagination
from utils.symbols import COIN_ICON
from languages import l

@dataclass
class ShopItem:
    id: int
    name: str
    description: str
    price: int
    type: str
    payload: Dict = field(default_factory=dict)


class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.items: list[ShopItem] = []
        self.ITEMS_PER_PAGE : int = 10

    async def get_shop_page(self, page: int) -> Tuple[discord.Embed, int]:
        total_pages = Pagination.compute_total_pages(len(self.items), self.ITEMS_PER_PAGE)
        page = max(1, min(page, total_pages))

        start = (page - 1) * self.ITEMS_PER_PAGE
        end = start + self.ITEMS_PER_PAGE
        items_page = self.items[start:end]

        embed = discord.Embed(title=l.text("shop", "title"), color=0x00ff00)
        for item in items_page:
            embed.add_field(
                name=f"{item.name} - {item.price} {COIN_ICON}",
                value=item.description,
                inline=False
            )
        embed.set_footer(text=l.text("page", page=page, total_pages=total_pages))
        return embed, total_pages

    async def load_items(self):
        items_db = await db.fetch_all("SELECT id, locale_id, price, item_type, payload FROM shop WHERE enabled = 1 ORDER BY item_type ASC, price ASC", cache=True)
        for id, locale_id, price, item_type, payload in items_db:
            self.items.append(ShopItem(id, 
            l.text("shop", "items", locale_id, "name"), l.text("shop", "items", locale_id, "description"),
            price, item_type, json.loads(payload)))
        

 
    @commands.group(name='shop', description=l.text("shop", "description"), invoke_without_command=True)
    async def shop(self, ctx):
        if (not self.items):
            await self.load_items()
        paginator = Pagination(ctx, self.get_shop_page)
        await paginator.navigate()
        

    @shop.command(name='buy', description=l.text("shop", "buy", "description"))
    async def buy(self, ctx, *, args: str):
        item : ShopItem|None = None
        parts = args.rsplit(maxsplit=1)
        try:
            amount = int(parts[-1])
            item_name = " ".join(parts[:-1])
        except ValueError:
            amount = 1
            item_name = args
        amount = await helpers.sanitize_quantity(ctx, amount)
        if (amount is None): return
        if (not self.items):
            await self.load_items()

        item_name = item_name.lower().strip()
        for shop_item in self.items:
            if shop_item.name.lower().strip() == item_name:
                item = shop_item
        if (item is None): 
            await ctx.send(l.text("shop", "buy", "invalid_item"))
            return
        async with db.transaction() as cur:
            coins_to_pay : int = item.price * amount
            message = []
            await cur.execute("UPDATE users SET coins = coins - %s WHERE id = %s AND coins >= %s", (coins_to_pay, ctx.author.id, coins_to_pay))
            if cur.rowcount == 0:
                await ctx.send(l.text("shop", "buy", "insufficient_coins"))
                return
        match item.type:
            case "pack":
                message = await helpers.open_pack_and_build_message(
                    bot=self.bot, user=ctx.author, pack_id=item.payload["pack_id"], amount=amount)
                chunks = helpers.chunk_string_by_length(message, max_len=2000, sep=" ")
                for chunk in chunks:
                    await ctx.send(chunk)
            case "upgrade":
                pass



        

    
async def setup(bot):
    await bot.add_cog(Shop(bot))
