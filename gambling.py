import discord
from discord.ext import commands
import random
import db
import helpers
import asyncio
from decimal import Decimal, ROUND_HALF_UP
from languages import l
def mysql_round(x):
    return int(Decimal(str(x)).quantize(0, rounding=ROUND_HALF_UP))

def render_roulette_players(players, gun="gun"):
    hex_text = f"""\n
    {players[0]["mfw"]} {players[1]["mfw"]}
{players[5]["mfw"]}  {l.text("_symbols", "gun")} {players[2]["mfw"]}
    {players[4]["mfw"]} {players[3]["mfw"]}\n
"""
    return f"\n{hex_text}\n"

class Gambling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='coinflip', description=l.text("coinflip", "description"))
    async def coinflip(self, ctx, choice : str|None = None, quantity : int|None = None):
        if (choice == None):
            await ctx.send(l.text("coinflip", "no_choice"))
            return
        
        quantity = await helpers.sanitize_quantity(ctx, quantity)
        if (quantity is None): return
        async with db.transaction() as cur:
            info = await helpers.get_user_info(ctx.author.id, cur=cur, for_update=True)
            if (quantity > info["coins"]):
                await ctx.send(l.text("coinflip", "insufficient_coins", coins=info["coins"]))
                return

            choice = choice[0].lower().strip()
            heads, tails, side = l.text("coinflip", "heads"), l.text("coinflip", "tails"), l.text("coinflip", "side")
            possibilities = [heads, tails, side]
            if choice not in [p[0] for p in possibilities]:
                await ctx.send(l.text("coinflip", "wrong_choice"))
                return
            
            random_value = random.randint(1, 6000)
            if random_value == 1:
                my_choice = side
            else:
                my_choice = random.choice(possibilities[:-1])
            
            message = l.text("coinflip", "i_thought_of", choice=my_choice.capitalize())
            if my_choice != side:
                if random_value <= 5:
                    message += f" {l.text("coinflip", "side_really_close")}"
                elif random_value <= 10:
                    message += f" {l.text("coinflip", "side_close")}"
            if choice == my_choice[0]:
                if (choice == side): 
                    quantity *= 5000
                    message = f"{message} {l.text("coinflip", "got_side")}"
                else: message = f"{message} {l.text("coinflip", "you_won")}"
                new_balance = info["coins"] + quantity
                
                if (quantity > 0): await cur.execute("UPDATE users SET coins = %s WHERE id = %s;", (new_balance, ctx.author.id)) 
            else: 
                new_balance = info["coins"] - quantity
                message = f"{message} {l.text("coinflip", "you_lost")}"
                if (quantity > 0): await cur.execute("UPDATE users SET coins = %s WHERE id = %s;", (new_balance, ctx.author.id)) 
            if (quantity > 0): 
                message = f"{message} {l.text("coinflip", "new_balance", 
                mention=ctx.author.mention, new_balance=new_balance)}"
            else: message = f"{message} {l.text("coinflip", "bet_0")}"

            await ctx.send(message)
            return
    
    
    @commands.command(name='russianroulette', description=l.text("russianroulette", "description"))
    async def russianroulette(self, ctx, confirmation: str | None, mfw: str = '777'):
        MULTIPLIER = 1.25

        yes, no = l.text("yes"), l.text("no")
        valid_users = [u for u in ctx.message.mentions if not u.bot and u.id != ctx.author.id]
        singleplayer = len(valid_users) == 0

        if confirmation is None:
            await ctx.send(l.text("russianroulette", "warning"))
            return

        confirmation = confirmation.lower().strip()[0]

        author_mfw_data = await helpers.check_if_mfw_exists(mfw)
        if author_mfw_data is None:
            await ctx.send(l.text("russianroulette", "no_avatar"))
            return

        players = []

        taken_mfws = set()
        taken_mfws.add(helpers.canonical(author_mfw_data["name"]))
        players.append({"id": ctx.author.id, 
        "mfw": helpers.mfw_emoji(author_mfw_data["id"], author_mfw_data["name"], author_mfw_data["is_animated"])})

        if not singleplayer:
            mention_string = ", ".join(user.mention for user in valid_users)
            await ctx.send(
                l.text("russianroulette", "multiplayer_warning", mentions=mention_string, author_mention=ctx.author.mention)
            )

            lock = asyncio.Lock()
            await asyncio.gather(*(invite_user(u, ctx, taken_mfws, players, lock) for u in valid_users))
        
        else:
            if confirmation not in (yes[0].lower(), no[0].lower()):
                await ctx.send(l.text("russianroulette", "invalid_confirmation"))
                return
            if confirmation == no[0].lower():
                await ctx.send(l.text("russianroulette", "confirmation_no"))
                return
            
        if not singleplayer and len(players) == 1:
            await ctx.send(l.text("russianroulette", "multiplayer_failed"))
            return
        
        PLAYER_COUNT = len(players)

        async with db.transaction() as cur:
            placeholders = ", ".join(["%s"] * PLAYER_COUNT)
            await cur.execute(f"SELECT id, coins FROM users WHERE id IN ({placeholders}) FOR UPDATE", tuple(p["id"] for p in players))
            user_balances = {row[0]: row[1] for row in await cur.fetchall()}
    
            while len(players) < 6:
                players.append({"mfw": l.text("_symbols", "mfw"), "id": None})
            
            random.shuffle(players)
            rolls = random.randint(8, 13)
            delay = 0
            LOSER_INDEX = 2
            announce = await ctx.send(l.text("russianroulette", "spinning_the_gun", seconds=3))
            for seconds in [2, 1]:
                await asyncio.sleep(1)
                await announce.edit(content=l.text("russianroulette", "spinning_the_gun", seconds=seconds))
            await asyncio.sleep(1)
            await announce.edit(content=l.text("russianroulette", "go"))
            msg = await ctx.send(render_roulette_players(players))
            for _ in range(rolls):
                delay += (random.randint(0, 10)/100)
                players = [players[-1]] + players[:-1]
                await msg.edit(content=render_roulette_players(players))
                await asyncio.sleep(0.3 + delay) 
            
            gun = "gun"
            turn_around = random.randint(1, 100)
            if turn_around == 1 and (players[LOSER_INDEX]["id"] is not None or players[5]["id"] is not None):
                LOSER_INDEX = 5
                gun = "nou"
                await msg.edit(content=render_roulette_players(players, gun=gun))
                await asyncio.sleep(0.5)
                
            players[LOSER_INDEX]["mfw"] = l.text("_symbols", "ded")
            await msg.edit(content=render_roulette_players(players, gun=gun))
            await asyncio.sleep(0.5)
            results = []
            blood_money = 0
            if (players[LOSER_INDEX]["id"] is not None):
                coins = user_balances[players[LOSER_INDEX]["id"]]
                if not singleplayer: blood_money += coins/(6)
                new_coins = 0
                await cur.execute("UPDATE users SET coins = 0 WHERE id = %s", (players[LOSER_INDEX]['id'],))
                results.append(l.text("russianroulette", "lost",
                mention=f"<@{players[LOSER_INDEX]["id"]}>", new_coins=new_coins, old_coins=coins))
                players[LOSER_INDEX]["id"] = None
                if coins == new_coins:
                        results[-1] += f" {l.text("russianroulette", "bet_0")}"

            for player in players:
                if (player["id"] is not None):
                    coins = user_balances[player["id"]]
                    new_coins = mysql_round((coins*MULTIPLIER) + blood_money)
                    await cur.execute("UPDATE users SET coins = (coins * %s) + %s WHERE id = %s", (MULTIPLIER, blood_money, player["id"]))
                    results.append(l.text("russianroulette", "win",
                    mention=f"<@{player["id"]}>", new_coins=new_coins, old_coins=coins))
                    if coins == new_coins:
                        results[-1] += f" {l.text("russianroulette", "bet_0")}"
            await ctx.send("\n".join(results))

async def invite_user(user, ctx, taken_mfws, players, lock):
    joined = False
    attempts = 0
    while attempts < 3 and not joined:
        attempts += 1

        def check(m: discord.Message) -> bool:
            return m.author == user and m.channel == ctx.channel

        try:
            response = await ctx.bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            await ctx.send(l.text("russianroulette", "invite_timeout", mention=user.mention))
            break

        content = response.content.strip()
        parts = content.split(None, 1)
        token = parts[0].lower()

        if token == "no":
            await ctx.send(l.text("russianroulette", "declined_to_join", mention=user.mention), allowed_mentions=discord.AllowedMentions.none())
            break

        requested = None
        if token == "avatar" and len(parts) == 2:
            requested = parts[1]
        elif token != "avatar":
            requested = content
        else:
            await ctx.send(l.text("russianroulette", "specify_mfw", mention=user.mention), allowed_mentions=discord.AllowedMentions.none())
            continue

        req_canon = helpers.canonical(requested.replace("<", "").replace(">", "").replace(":", ""))

        async with lock:
            if req_canon in taken_mfws:
                if attempts < 3:
                    await ctx.send(l.text("russianroulette", "already_taken", mention=user.mention), allowed_mentions=discord.AllowedMentions.none())
                    continue
                else:
                    await ctx.send(l.text("russianroulette", "fail_due_already_taken", mention=user.mention))
                    break

            mfw_data = await helpers.check_if_mfw_exists(requested)
            if mfw_data is None:
                if attempts < 3:
                    await ctx.send(l.text("russianroulette", "non_existent_mfw", mention=user.mention), allowed_mentions=discord.AllowedMentions.none())
                    continue
                else:
                    await ctx.send(l.text("russianroulette", "fail_due_non_existent_mfw", mention=user.mention))
                    break

            taken_mfws.add(helpers.canonical(mfw_data["name"]))
            players.append({
                "id": user.id,
                "mfw": helpers.mfw_emoji(mfw_data["id"], mfw_data["name"], mfw_data["is_animated"])
            })

        await ctx.send(l.text("russianroulette", "successful_join", mention=user.mention), allowed_mentions=discord.AllowedMentions.none())
        joined = True
            
async def setup(bot):
    await bot.add_cog(Gambling(bot))