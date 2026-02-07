import discord
import db
import utils.services.dbutils as dbutils
import utils.services.discordutils as discordutils
from languages import l
from typing import TypedDict
from ..misc.blackjack_state import GameState, render_hand, calculate_value
import asyncio

ONGOING_GAMES : list[GameState] = []

c = "blackjack"
class PlayerData(TypedDict):
    user: discord.User
    balance: int
class GameUI(discord.ui.View):
    def __init__(self, game : GameState, players : dict[int, PlayerData]):
        super().__init__(timeout=60)
        self.players = players
        self.game = game
        self.embed = None
        self.message_sent = False
        self.all_settled = False
        self.finished_event = asyncio.Event()

        self.stand_button = discord.ui.Button(label=l.text(c, "stand"), style=discord.ButtonStyle.primary, custom_id="stand")
        self.hit_button = discord.ui.Button(label=l.text(c, "hit"), style=discord.ButtonStyle.success, custom_id="hit")
        self.double_button = discord.ui.Button(label=l.text(c, "double_down"), style=discord.ButtonStyle.danger, custom_id="double_down")

        self.stand_button.callback = self.stand
        self.hit_button.callback = self.hit
        self.double_button.callback = self.double_down

        self.add_item(self.stand_button)
        self.add_item(self.hit_button)
        self.add_item(self.double_button)

    async def start(self, ctx):
        self.embed = self.create_embed()
        self.message = await ctx.send(embed=self.embed, view=self)
        if self.all_settled:
            await self.end_game()

    async def check_if_in_game(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in self.players:
            await interaction.response.send_message(
                    l.text(c, "not_playing"),
                    ephemeral=True,
                )
            return False
        else:
            return True

    async def hit(self, interaction : discord.Interaction):
        if not await self.check_if_in_game(interaction):
            return
        await interaction.response.defer()
        self.game.hit(interaction.user.id)
        await self.update_message()

    async def stand(self, interaction : discord.Interaction):
        if not await self.check_if_in_game(interaction):
            return
        await interaction.response.defer()
        self.game.stand(interaction.user.id)
        await self.update_message()

    async def double_down(self, interaction : discord.Interaction):
        if not await self.check_if_in_game(interaction):
            return
        if self.game.players_hand[interaction.user.id].bet*2 > self.players[interaction.user.id]["balance"]:
            await interaction.response.send_message(
                    l.text(c, "insufficient_funds"),
                    ephemeral=True,
                )
            return
        
        await interaction.response.defer()
        self.game.double_down(interaction.user.id)
        await self.update_message()

    def create_embed(self, reveal_dealer_cards=False):
        self.all_settled = True
        embed = discord.Embed(title=l.text(c, "blackjack"),
                              color=discord.Color.gold())
        
        embed.add_field(
            name=f"{l.text(c, "dealer")} {l.text(c, "busted") if self.game.dealer_hand.busted else ""}",
            value=render_hand(self.game.dealer_hand, is_dealer=True, reveal_dealer_cards=reveal_dealer_cards),
            inline=False
        )
        for player, hand in self.game.players_hand.items():
            display_name : str = self.players[player]["user"].display_name
            value = calculate_value(hand.cards)
            if value.total >= 21: 
                hand.settled = True
            if value.total > 21:
                hand.busted = True
            embed.add_field(
                name=f"{display_name} {l.text(c, "busted") if hand.busted else ""}",
                value=render_hand(hand),
                inline=False
            )
            if not hand.settled: self.all_settled = False
        return embed

    async def update_message(self, reveal_dealer_cards=False):
        self.embed = self.create_embed(reveal_dealer_cards=reveal_dealer_cards)
        await self.message.edit(embed=self.embed, view=self)
        if self.all_settled and not self.game.finished:
            await self.end_game()
    
    async def end_game(self):
        self.game.finished = True
        self.stand_button.disabled = True
        self.hit_button.disabled = True
        self.double_button.disabled = True
        await self.message.edit(embed=self.embed, view=self)

        await asyncio.sleep(1)
        await self.update_message(reveal_dealer_cards=True)
        while (self.game.dealer_can_hit()):
            await asyncio.sleep(1)
            self.game.dealer_play()
            await self.update_message()
        self.finished_event.set()

    async def on_timeout(self):
        if not self.game.finished:
            await self.end_game()
            self.stop()

async def blackjack(self, ctx, bet: int|None = None):
    if bet is None:
        await ctx.send(l.text(c, "no_bet"))
        return
    amount = await discordutils.sanitize_quantity(ctx, bet)
    if (amount is None): return

    if (await dbutils.get_user_info(ctx.author.id))["coins"] < amount:
        await ctx.send(l.text(c, "insufficient_funds"))
        return
    
    async with db.transaction() as cur:
        player_ids : list[int] = [ctx.author.id]
        placeholders = ", ".join(["%s"] * len(player_ids))
        await cur.execute(f"SELECT id, coins FROM users WHERE id in ({placeholders}) FOR UPDATE", tuple(player_ids,))
        rows = await cur.fetchall()
        players: dict[int, PlayerData] = {}
        for id, coins in rows:
            user = await self.bot.fetch_user(id)
            players[id] = PlayerData(user=user, balance=coins)
        game = GameState([(ctx.author.id, amount)])
        view = GameUI(game, players)
        await view.start(ctx)
        await view.finished_event.wait()
        payouts : dict[int, int] = game.calculate_payouts()
        for player, payout in payouts.items():
            await cur.execute("UPDATE users SET coins = coins + %s WHERE id = %s", (payout, player))
        result_message = []
        if game.dealer_hand.busted: result_message.append(l.text(c, "x_has_busted", name=l.text(c, "dealer")))
        for id, hand in game.players_hand.items():
            old_coins = players[id]["balance"]
            new_coins = players[id]["balance"] + payouts[id]
            name = players[id]["user"].mention
            if hand.busted:
                result_message.append(
                f"{l.text(c, "x_has_busted", name=name)} {l.text(c, "lost", old_coins=old_coins, new_coins=new_coins)}"
                )
                continue
            
            if game.results[id] == True:
                result_message.append(
                f"{l.text(c, "x_has_won", name=name)} {l.text(c, "win", old_coins=old_coins, new_coins=new_coins)}"
                )
            elif game.results[id] == False:
                result_message.append(
                f"{l.text(c, "x_has_lost", name=name)} {l.text(c, "lost", old_coins=old_coins, new_coins=new_coins)}"
                )
            else:
                result_message.append(
                f"{l.text(c, "x_has_pushed", name=name)} {l.text(c, "tie")}"
                )

        await asyncio.sleep(1)
        await ctx.send("\n".join(result_message))
        
