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
from languages import l
import time

users_in_math_problems : list[int] = []

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
    
    @commands.command(name='math', description=l.text("math", "description"))
    async def get_math_problem(self, ctx, other_user: discord.Member|None = None):
        MATH_COINS = 10
        if other_user and other_user.bot:
            await ctx.send(l.text("math", "challenging_bot"))
            return
        
        if ctx.author.id in users_in_math_problems:
            return
        
        target = other_user or ctx.author
        question, answer, tip, timeout = generate_problem()
        details = {
            "question": question,
            "answer": answer
        }
        await ctx.send(l.text("math", "challenge", mention=target.mention, question=question))
        users_in_math_problems.append(ctx.author.id)

        def is_answer_correct(attempt, answer):
            if isinstance(answer, str):
                return attempt.lower().strip() == answer.lower()
            elif isinstance(answer, int) or isinstance(answer, float): 
                try:
                    return abs(float(attempt) - float(answer)) < 1e-9
                except ValueError:
                    return False
            else: return None 
            
        def check(m):
            return m.channel == ctx.channel and not m.author.bot
        deadline = time.monotonic() + timeout
        result = "loss"
        message = None
        while True:
            try:
                message = await self.bot.wait_for('message', check=check, timeout=deadline-time.monotonic())
            except asyncio.TimeoutError:
                await ctx.send(l.text("math", "timeout", mention=target.mention))
                if target == ctx.author:
                    details["user_answer"] = None
                    details["reason"] = "Timeout"
                    result = "loss"
                    await db.execute("INSERT INTO game_results(game_id, player1_id, winner_player_id, player1_score, details)" \
                    "VALUES (%s, %s, %s, %s, %s)", 
                    (1, target.id, None, 0, json.dumps(details)))
                    break
            if message is not None:
                if message.author == target:
                    correct = is_answer_correct(message.content, answer);
                    if correct is None: pass
                    elif correct == False:
                        lose_message = l.text("math", "wrong_value", mention=target.mention, answer=answer)
                        if tip is not None: lose_message = f"{lose_message} {tip}"
                        await ctx.send(lose_message)
                        result = "loss"
                        break
                    else:
                        await db.execute("INSERT INTO users (id, coins) VALUES (%s, %s) ON DUPLICATE KEY UPDATE coins = coins + %s;", (target.id, MATH_COINS, MATH_COINS))
                        await ctx.send(l.text("math", "success", mention=target.mention, coins=MATH_COINS))
                        result = "win"
                        break
                else:
                    if message.author.id not in users_in_math_problems:
                        correct = None
                        for substring in message.content.split(" "):
                            correct = is_answer_correct(substring, answer)
                            if correct: break
                        if correct:
                            await ctx.send(l.text("math", "not_target_answering", mention=message.author.mention))
                        details["user_answer"] = message.content.strip(),
                        details["reason"] = "Not being challenged",
                        await db.execute("INSERT INTO game_results(game_id, player1_id, winner_player_id, player1_score, details)" \
                        "VALUES (%s, %s, %s, %s, %s)", 
                        (1, message.author.id, None, 0, json.dumps(details)))
                        return

                

            
        winner_player_id = None if result == "loss" else ctx.author.id
        details["user_answer"] = message.content.strip() if message != None else None
        await db.execute("INSERT INTO game_results(game_id, player1_id, winner_player_id, player1_score, details)" \
        "VALUES (%s, %s, %s, %s, %s)", 
        (1, ctx.author.id, winner_player_id, 1 if winner_player_id else 0, json.dumps(details)))        
        users_in_math_problems.remove(ctx.author.id)       

        if message: print(f"The answer given was: {message.content}\nThe correct answer is: {answer}")

async def setup(bot):
    await bot.add_cog(Math(bot))