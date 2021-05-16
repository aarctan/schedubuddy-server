from discord.ext import commands
from discord.ext.commands import bot

from secret import TOKEN
import schedule_session

bot = commands.Bot(command_prefix='!')
schedule_session.setup(bot)

@bot.event
async def on_ready():
    print("Logged in as {0.user}".format(bot))

bot.run(TOKEN)
