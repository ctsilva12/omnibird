import utils.services.discordutils as discordutils
import utils.services.dbutils as dbutils
import random
import db
from languages import l

c = "coinflip"
async def coinflip(self, ctx, choice : str|None = None, quantity : int|None = None):
        if (choice == None):
            await ctx.send(l.text("coinflip", "no_choice"))
            return
        
        quantity = await discordutils.sanitize_quantity(ctx, quantity)
        if (quantity is None): return
        async with db.transaction() as cur:
            info = await dbutils.get_user_info(ctx.author.id, cur=cur, for_update=True)
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