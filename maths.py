import discord
from discord.ext import commands
import random
import db
import helpers
import asyncio
from utils.mathproblems.arithmetic import generate_arithmetic_problem
from utils.mathproblems.triangle import generate_triangle_problem
from utils.mathproblems.trigonometry import generate_trigonometry_problem
from utils.mathproblems.geometry import generate_geometry_problem
import random
import json
from utils.symbols import COIN_ICON
from languages import text

def generate_problem():
    problem_type = random.randint(1, 4)
    timeout = 20
    tip = None
    if problem_type == 1:
        question, answer = generate_arithmetic_problem()
    elif problem_type == 2:
        question, answer, timeout = generate_geometry_problem()
    elif problem_type == 3:
        question, answer, tip, timeout = generate_triangle_problem()
    else: 
        question, answer = generate_trigonometry_problem()

    return question, answer, tip, timeout

class Math(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='math', description=text("math", "description"))
    async def get_math_problem(self, ctx, other_user: discord.Member|None = None):
        MATH_COINS = 10
        if other_user and other_user.bot:
            await ctx.send(text("math", "challenging_bot"))
            return
        
        tip = ""
        target = other_user or ctx.author
        question, answer, tip, timeout = generate_problem()
        details = {
            "question": question,
            "answer": answer
        }
        await ctx.send(text("math", "challenge", mention=target.mention, question=question))

        def check(m):
            return m.author == target and m.channel == ctx.channel

        try:
            user_answer = await self.bot.wait_for('message', check=check, timeout=timeout)
        except asyncio.TimeoutError:
            await ctx.send(text("math", "timeout", mention=target.mention))
            if target == ctx.author:
                details["user_answer"] = None
                details["reason"] = "Timeout"
                await db.execute("INSERT INTO game_results(game_id, player1_id, winner_player_id, player1_score, details)" \
                "VALUES (%s, %s, %s, %s, %s)", 
                (1, target.id, None, 0, json.dumps(details)))
            return

        if  (answer is None): answer = ""
        lose_message = text("math", "wrong_value", mention=target.mention, answer=answer)
        if user_answer.author == target:
            try:
                if isinstance(answer, str): raise ValueError
                user_value = float(user_answer.content.strip())
                answer_value = float(answer)
                if abs(user_value - answer_value) < 1e-9:
                    await db.execute("INSERT INTO users (id, coins) VALUES (%s, %s) ON DUPLICATE KEY UPDATE coins = coins + 10;", (target.id, MATH_COINS)) # type: ignore # type: supress
                    await ctx.send(text("math", "success", mention=target.mention, coins=MATH_COINS))
                    result = "win"
                else:
                    if tip is not None: lose_message = f"{lose_message} {tip}"
                    await ctx.send(lose_message)
                    result = "loss"
            except ValueError:
                if isinstance(answer, str):
                    user_value = user_answer.content.strip().lower()
                    if user_value == answer:
                        await db.execute("INSERT INTO users (id, coins) VALUES (%s, %s) ON DUPLICATE KEY UPDATE coins = coins + 10;", (target.id, MATH_COINS)) # type: ignore # type: supress
                        await ctx.send(text("math", "success", mention=target.mention, coins=MATH_COINS))
                        result = "win"
                    else: 
                        await ctx.send(lose_message)
                        result = "loss"
                else:
                    lose_message = text("math", "invalid_value", mention=target.mention, answer=answer)
                    await ctx.send(lose_message)
                    result = "loss"
                
            user_id = str(ctx.author.id)
            winner_player_id = None if result == "loss" else user_id
            details["user_answer"] = user_answer.content.strip()

            await db.execute("INSERT INTO game_results(game_id, player1_id, winner_player_id, player1_score, details)" \
            "VALUES (%s, %s, %s, %s, %s)", 
            (1, user_id, winner_player_id, 1 if winner_player_id else 0, json.dumps(details)))
        else:
            await ctx.send(text("math", "not_target_answering", mention=other_user.mention)) # type: ignore
            user_id = str(other_user.id) # type: ignore
            details["user_answer"] = user_answer.content.strip()
            details["reason"] = "Not being challenged"
            await db.execute("INSERT INTO game_results(game_id, player1_id, winner_player_id, player1_score, details)" \
            "VALUES (%s, %s, %s, %s, %s)", 
            (1, user_answer.author.id, None, 0, json.dumps(details)))

        print(f"The answer given was: {user_answer.content}\nThe correct answer is: {answer}")

async def setup(bot):
    await bot.add_cog(Math(bot))