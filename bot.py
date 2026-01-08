import discord
import responses
from discord.ext import tasks, commands
from discord.utils import get
import random
import os
import json
import db
import random
from languages import text


async def send_message(message, user_message, is_private):
    try:
        response = responses.get_response(user_message)
        if response == None:
            return
        await message.author.send(response) if is_private else await message.channel.send(response)

    except Exception as e:
        print(e)


def run_discord_bot():
    TOKEN = os.getenv("BOT_TOKEN")
    if TOKEN is None:
        raise ValueError("Token not set in .env")
    
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='o!', intents=intents)
    
    @bot.event
    async def on_ready():
        await bot.load_extension("mfw")
        await bot.load_extension("economy")
        await bot.load_extension("gambling")
        await bot.load_extension("admin")
        await bot.load_extension("shop")
        await bot.load_extension("maths")
        print(f'{bot.user} is now running!')
        id_guild = 1457482751723700444
        guild = bot.get_guild(id_guild)
        if guild:
            emojis = guild.emojis
            for emoji in emojis:
                await db.execute(
                    "INSERT INTO mfws (id, name, rarity_id, guild_id, is_animated) VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE id = id;",
                    (emoji.id, emoji.name, 0, id_guild, getattr(emoji, "animated", False))
                )

        # if(SEND_FUNNY_MESSAGE == True):
            # send_funny_message.start()
    
    @tasks.loop(minutes=5)
    async def send_random_quote():
        """channel = bot.get_channel(1117633430562283531) 

        if channel:
            quote = random.choice(responses.quotes)
            await channel.send(quote)
            print(f"The following message was successfully sent: {quote}")
         """


    @bot.event
    async def on_message(message):
        if message.author.bot: # Bot will not reply to itself
            return

        username = str(message.author)
        author_id = str(message.author.id)
        user_message = str(message.content)
        channel = str(message.channel)

        print(f'{username} said: "{user_message}" ({channel})')

        await bot.process_commands(message)
        await send_message(message, user_message, False)

    @bot.command(name='quote', description=text("quote", "description"))
    async def get_random_quote(ctx):
        quote = random.choice(responses.quotes)
        await ctx.send(quote)
        print(f"The following message was successfully sent: {quote}")

    bot.run(TOKEN)