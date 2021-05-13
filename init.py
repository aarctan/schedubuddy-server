import discord
from discord.ext import commands
from discord.ext.commands import bot

from sched_gen import generate_schedules
from draw_sched import draw_schedule
from random import choice

from secret import TOKEN

bot = commands.Bot(command_prefix='!')
import eightbitify
import schedule_session
eightbitify.setup(bot)
schedule_session.setup(bot)

@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))

'''
@bot.event(pass_context=True)
async def on_reaction_add(reaction, user):
    channel = reaction.message.channel
    await ctx.send("hello")
'''

@bot.command(pass_context=True)
async def c(ctx, *args):
    args = list(args)
    for i in range(len(args)):
        args[i] = args[i].upper()
    courses_queried = [x+' '+y for x,y in zip(args[0::2], args[1::2])]
    schedules = generate_schedules(courses_queried)
    if len(schedules) == 0:
        query = ' '.join(courses_queried)
        msg = "No valid schedules found for query: ```"+str(query)+\
            "```Better error messages coming in the future."
        await ctx.send(msg)
        return
    
    could_draw = True
    try:
#        draw_schedule(choice(schedules))
        draw_schedule(schedules[0])
    except:
        could_draw = False
        msg = "Valid schedules found but not able to draw the query: ```"+str(query)+\
            "```Please let Arctan#1234 know."
        await ctx.send(msg)
    if not could_draw:
        return
    msg_desc = "Listing **1** of **" + str(len(schedules)) +\
         "** generated schedules for the specified course selection:"
    embed = discord.Embed(description=msg_desc, color=0xb3edbd)
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
    file = discord.File("schedule.png", filename="image.png")
    embed.set_image(url="attachment://image.png")
    post = await ctx.send(file=file, embed=embed)
    await post.add_reaction('⬅️')
    await post.add_reaction('➡️')

bot.run(TOKEN)
