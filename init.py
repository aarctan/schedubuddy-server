import discord
from discord.ext import commands
from discord.ext.commands import bot
from permutation import permute_classes
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
    #await ctx.send('Working!', file=discord.File('schedule.png'))
    args = list(args)
    for i in range(len(args)):
        args[i] = args[i].upper()
    courses_queried = [x+' '+y for x,y in zip(args[0::2], args[1::2])]
    schedules = permute_classes(courses_queried)
    draw_schedule(choice(schedules))
    await ctx.send('', file=discord.File('schedule.png'))
    #await ctx.send('`{}` arguments: `{}`'.format(len(args), ', '.join(args)))

bot.run(TOKEN)
