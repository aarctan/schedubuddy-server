import discord
from discord.ext import commands
from discord.ext.commands import bot

from sched_gen import generate_schedules
from draw_sched import draw_schedule
from random import choice

from secret import TOKEN

bot = commands.Bot(command_prefix='!')

@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))

'''
@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.content.startswith(cmd_prefix + 'd'):
        valid_input = True
        query = ''
        try:
            query = message.content[3:]
            query = query.strip().upper()
            assert (query and query != '')
            query = query.split()
            assert (len(query)%2 == 0)
        except:
            valid_input = False
        if not valid_input:
            return
        courses_queried = [x+' '+y for x,y in zip(query[0::2], query[1::2])]
        schedules = permute_classes(courses_queried)
        draw_schedule(choice(schedules))
        await channel.send(file=discord.File('schedule.png'))'''

@bot.command(pass_context=True)
async def c(ctx, *args):
    args = list(args)
    for i in range(len(args)):
        args[i] = args[i].upper()
    courses_queried = [x+' '+y for x,y in zip(args[0::2], args[1::2])]
    schedules = generate_schedules(courses_queried)
    draw_schedule(choice(schedules))
    msg_desc = "Listing **1** of **" + str(len(schedules)) +\
         "** generated schedules for the specified course selection:"
    embed = discord.Embed(description=msg_desc, color=0xb3edbd)
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
    file = discord.File("schedule.png", filename="image.png")
    embed.set_image(url="attachment://image.png")
    post = await ctx.send(file=file, embed=embed)
    #left_emoji = ctx.client.get_emoji(⬅️)
    await post.add_reaction('⬅️')
    await post.add_reaction('➡️')

 


@bot.command(pass_context=True)
async def embed(ctx):
    embed=discord.Embed(description="This is an embed that will show how to build an embed and the different components", color=discord.Color.blue())
    await ctx.send(embed=embed)

bot.run(TOKEN)
