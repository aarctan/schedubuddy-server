import discord
import os

from secret import TOKEN
cmd_prefix = '!'

client = discord.Client()

def get_numerical_time(str_t):
    h = int(str_t[0:2])
    m = int(str_t[3:5])
    pm = str_t[6:9] == 'PM'
    if pm and h==12: return h*60+m
    if pm and h<12: return (h+12)*60+m
    if not pm and h==12: return m
    if not pm and h<12: return h*60+m
    return None

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')

    if message.content.startswith(cmd_prefix + 'c'):
        valid_input = True
        try:
            query = message.content[3:]
            query = query.strip().lower()
            assert (query and query != '')
        except:
            valid_input = False
        if not valid_input:
            return

client.run(TOKEN)
