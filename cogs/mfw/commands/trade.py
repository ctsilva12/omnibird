import discord
from discord.ext import commands
import utils.services.discordutils as discordutils
import utils.services.dbutils as dbutils
import utils.pure.formatting as formatting
import db
from languages import l

c = "trade"

class TradeState:
    def __init__(self, users: list[discord.User]):
        self.users: list[discord.User] = users
        self.mfws: dict[int, list[tuple]] = {
            user.id: [] for user in users
        }
        self.coins: dict[int, int] = {
            user.id: 0 for user in users
        }
        self.locked: dict[int, bool] = {
            user.id: False for user in users
        }

def build_embed(trade: TradeState) -> discord.Embed:
    embed = discord.Embed(title=l.text(c, "embed_title", 
    mention1=trade.users[0].display_name, mention2=trade.users[1].display_name),
    description=l.text(c, "embed_description"))
    for u in trade.users:
        user_mfws = trade.mfws.get(u.id, [])
        if user_mfws:
            mfws_strings = []
            for mfw_id, quantity, _, name, is_animated in user_mfws:
                mfws_strings.append(f"{formatting.make_emoji(mfw_id, name, is_animated)} (x{quantity})")
            
            chunks = formatting.chunk_by_length(mfws_strings, max_len=1000, sep=", ")
        else:
            chunks = [l.text("none")]
        embed.add_field(
            name=f"{u.display_name} {":white_check_mark:" if trade.locked[u.id] else ""}",
            value=f"{l.text(c, "coins", coins=trade.coins[u.id])}\n{l.text(c, "mfws", mfws=chunks[0])}",
            inline=False
        )
        for chunk in chunks[1:]:
            embed.add_field(
                name="\u200b",
                value=chunk,
                inline=False
            )
    return embed

async def handle_trade(trade: TradeState):
    error_message = []
    if not all(trade.locked.items()): raise ValueError
    async with db.transaction() as cur:

        for user in trade.users:
            try:
                coins = (await dbutils.get_user_info(user.id, cur=cur, for_update=True))["coins"]
                if trade.coins[user.id] > coins: error_message.append(l.text(c, "coins_changed_since_modal", mention=user.mention, coins=coins))
                await dbutils.validate_mfws_by_id(
                    cur=cur,
                    user_id=user.id,
                    mfws=trade.mfws[user.id],
                )
            except ValueError as e: 
                error_message.append(str(e))

        if error_message: raise ValueError("\n".join(error_message))


        uids = [user.id for user in trade.users]
        user1, user2 = uids[0], uids[1]

        update_coins = f"""UPDATE users u
        SET coins = CASE id
        WHEN {user1} THEN coins + {trade.coins[user2]} - {trade.coins[user1]}
        WHEN {user2} THEN coins + {trade.coins[user1]} - {trade.coins[user2]}
        END
        WHERE id in (%s, %s)"""

        a_to_b = trade.mfws[user1]
        b_to_a = trade.mfws[user2]

        await cur.execute(update_coins, (user1,user2))
        for user, mfws in ((user1, a_to_b), (user2, b_to_a)):
            if not mfws: continue
            qty_case_sql, params, ids, in_placeholders = dbutils.build_qty_case_sql(mfws)
            update_sql = f"""UPDATE inventory i
            SET i.quantity = {qty_case_sql}
            WHERE i.user_id = %s AND i.mfw_id in ({in_placeholders})"""

            params.append(user)
            params.extend(ids)
            await cur.execute(update_sql, tuple(params))

        for recipient, mfws in ((user2, a_to_b), (user1, b_to_a)):
            if not mfws:
                continue
            insert_values = []
            insert_params = []
            for mfw_id, qty, *_ in mfws:
                insert_values.append("(%s, %s, %s)")
                insert_params.extend((recipient, mfw_id, qty))

            insert_sql = f"""
                INSERT INTO inventory(user_id, mfw_id, quantity)
                VALUES {', '.join(insert_values)} AS new
                ON DUPLICATE KEY UPDATE inventory.quantity = inventory.quantity + new.quantity
            """
            await cur.execute(insert_sql, tuple(insert_params))

class PromptModal(discord.ui.Modal, title=l.text(c, "offer")):
    coins_input = discord.ui.TextInput(
        required=False,
        label=l.text(c, "coins_input"),
        style=discord.TextStyle.short,
        max_length=10,
        row=1
    )

    mfws_input = discord.ui.TextInput(
        required=False,
        label=l.text(c, "mfws_input"),
        style=discord.TextStyle.long,
        max_length=200,
        row=0
    )

    def __init__(self, trade: TradeState, bot: commands.Bot, user: discord.User|discord.Member, message):
        super().__init__(timeout=None)
        self.trade = trade
        self.bot = bot
        self.message = message
        coins = trade.coins.get(user.id, 0)
        mfws = trade.mfws.get(user.id, [])
        self.coins_input.default = str(coins)
        self.mfws_input.default = ", ".join(
            f"{quantity if quantity > 1 else ""} {name}" for _, quantity, _, name, _ in mfws
        )

    async def on_submit(self, interaction: discord.Interaction):
        raw_coins = self.coins_input.value
        raw_mfws = self.mfws_input.value

        if raw_coins == "":
            coins = 0
        elif raw_coins.isdigit():
            coins = int(raw_coins)
        else:
            await interaction.response.send_message(
                l.text(c, "coins_must_be_number"),
                ephemeral=True
            )
            return
        
        balance = 0
        async with db.transaction() as cur:
            balance = (await dbutils.get_user_info(interaction.user.id, cur=cur, for_update=True))["coins"]
        if coins > balance:
            await interaction.response.send_message(
                l.text(c, "insufficient_balance", coins=balance),
                ephemeral=True
            )
            return
        
        try:
            mfws, _, _, _ = await discordutils.parse_and_validate_mfws(self.bot, interaction.user, raw_mfws, allow_zero_mfws=True)
        except ValueError as e:
            await interaction.response.send_message(
                str(e),
                ephemeral=True
            )
            return
        self.trade.mfws[interaction.user.id] = mfws
        self.trade.coins[interaction.user.id] = coins
        for u in self.trade.locked:
            self.trade.locked[u] = False
        embed = build_embed(self.trade)
        await interaction.response.edit_message(embed=embed)

    async def on_timeout(self) -> None:
        
        self.stop()


class PromptView(discord.ui.View):
    def __init__(self, trade: TradeState, bot: commands.Bot, message, ctx):
        super().__init__(timeout=300)
        self.trade = trade
        self.bot = bot
        self.message = message
        self.ctx = ctx
        self.success = False

    @discord.ui.button(label=l.text(c, "edit_offer"), style=discord.ButtonStyle.primary)
    async def prompt_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if (interaction.user.id not in (u.id for u in self.trade.users)):
            await interaction.response.send_message(
                content=l.text(c, "not_participating"),
                ephemeral=True
            )
            return
        await interaction.response.send_modal(PromptModal(self.trade, self.bot, interaction.user, self.message))

    @discord.ui.button(label=l.text(c, "cancel"), style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if (interaction.user.id not in (u.id for u in self.trade.users)):
            await interaction.response.send_message(
                content=l.text(c, "not_participating"),
                ephemeral=True
            )
            return
        if self.trade.locked[interaction.user.id]:
            self.trade.locked[interaction.user.id] = False
        else:
            await interaction.response.send_message(l.text(c, "abort_trade", mention=interaction.user.mention), allowed_mentions=discord.AllowedMentions.none())
            await self.end_trade(success=False)
            return
        
        embed = build_embed(self.trade)
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label=l.text(c, "accept"), style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if (interaction.user.id not in (u.id for u in self.trade.users)):
            await interaction.response.send_message(
                content=l.text(c, "not_participating"),
                ephemeral=True
            )
            return
        if self.trade.locked[interaction.user.id]:
            await interaction.response.send_message(
                content=l.text(c, "cant_accept_twice"),
                ephemeral=True
            )
            return

        self.trade.locked[interaction.user.id] = True
        if all(self.trade.locked.values()): 
            await self.end_trade()
            await interaction.response.defer()
        else:
            embed = build_embed(self.trade)
            await interaction.response.edit_message(embed=embed)

    async def end_trade(self, success=True):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        if success: 
            try:
                await handle_trade(self.trade)
                self.success = True
                await self.message.reply(f"{self.trade.users[0].mention} and {self.trade.users[1].mention}'s trade was successful!")
                self.stop()
            except ValueError as e:
                self.trade.locked = {
                    user.id: False for user in self.trade.users
                }
                await self.message.reply(str(e))
                
        embed = build_embed(self.trade)
        await self.message.edit(embed=embed, view=self)
            
    async def on_timeout(self):
        if not self.success:
            await self.ctx.send(l.text(c, "timeout", mention1=self.trade.users[0].mention, mention2=self.trade.users[1].mention), allowed_mentions=discord.AllowedMentions.none())
            await self.end_trade(success=False)
        self.stop()
        
        

    

async def trade(self, ctx, user: discord.User|None):
    if user is None or user.id == ctx.author.id:
        await ctx.send(l.text(c, "trading_with_self"))
        return
    
    trade = TradeState([ctx.author, user])
    view = PromptView(trade, self.bot, None, ctx=ctx)
    trade_message = await ctx.send(
        embed=build_embed(trade),
        view=view
    )
    view.message = trade_message