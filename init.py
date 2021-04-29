import discord
import os

from secret import TOKEN
cmd_prefix = '!'

client = discord.Client()

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
