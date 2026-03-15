import discord
from languages import l
from ..mathproblems import generate_problem
import time
import asyncio
import db
import json

async def math(self, ctx, other_user: discord.Member|None = None):
        MATH_COINS = 20
        if other_user and other_user.bot:
            await ctx.send(l.text("math", "challenging_bot"))
            return
        
        if ctx.author.id in self.users_in_math_problems:
            return
        
        target = other_user or ctx.author
        question, answer, tip, timeout = generate_problem()
        details = {
            "question": question,
            "answer": answer
        }
        await ctx.send(l.text("math", "challenge", mention=target.mention, question=question))
        self.users_in_math_problems.append(ctx.author.id)

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
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                await ctx.send(l.text("math", "timeout", mention=target.mention))
                details["user_answer"] = None
                details["reason"] = "Timeout"
                result = "loss"
                break
            try:
                message = await self.bot.wait_for('message', check=check, timeout=remaining)
            except asyncio.TimeoutError:
                # should never happen, but good to be safe
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
                    if correct is None: continue
                    if not correct:
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
                    if message.author.id in self.users_in_math_problems:
                        continue
                    found = False
                    for substring in message.content.split(" "):
                        found = is_answer_correct(substring, answer)
                        if found: break
                    if found:
                        result = "interrupter"
                        await ctx.send(l.text("math", "not_target_answering", mention=message.author.mention))
                        details["user_answer"] = message.content.strip(),
                        details["reason"] = "Not being challenged",
                        await db.execute("INSERT INTO game_results(game_id, player1_id, winner_player_id, player1_score, details)" \
                        "VALUES (%s, %s, %s, %s, %s)", 
                        (1, message.author.id, None, 0, json.dumps(details)))
                        self.users_in_math_problems.remove(ctx.author.id)  
                        break
                    else: continue
                

        try: self.users_in_math_problems.remove(ctx.author.id)
        except ValueError: pass
        if result != "interrupter":
            winner_player_id = None if result == "loss" else ctx.author.id
            details["user_answer"] = message.content.strip() if message != None else None
            await db.execute("INSERT INTO game_results(game_id, player1_id, winner_player_id, player1_score, details)" \
            "VALUES (%s, %s, %s, %s, %s)", 
            (1, ctx.author.id, winner_player_id, 1 if winner_player_id else 0, json.dumps(details)))            

        if message: print(f"The answer given was: {message.content}\nThe correct answer is: {answer}")