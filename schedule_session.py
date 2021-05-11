import sched_gen
import draw_sched

from contextlib import suppress
import asyncio
import discord
from discord import Colour, Embed, HTTPException, Message, Reaction, User
from discord.ext import commands
from discord.ext.commands import CheckFailure, Cog as DiscordCog, Command, Context

LEFT_EMOJI = '⬅️'
RIGHT_EMOJI = '➡️'

class ScheduleSession:
    def __init__(
        self,
        ctx: Context,
        *args,
    ):
        self._ctx = ctx
        self._bot = ctx.bot
        self.title = "Schedule Session"
        self.author = ctx.author
        self.destination = ctx.channel
        self.message = None
        self._pages = None
        self._current_page = 0
        self._timeout_task = None
        self.schedules = self.get_schedules(args)
        self.reset_timeout()

    @staticmethod
    def get_schedules(raw_args):
        args = list(raw_args)
        for i in range(len(args)):
            args[i] = args[i].upper()
        courses_queried = [x+' '+y for x,y in zip(args[0::2], args[1::2])]
        return sched_gen.generate_schedules(courses_queried)

    async def update_page(self, page_number: int = 0) -> None:
        self._current_page = page_number
        msg_desc = "Listing **{}** of **{}** generated schedules for the\
            specified course selection:"\
            .format(str(page_number+1), str(len(self.schedules)))
        embed = Embed(description=msg_desc, color=0xb3edbd)
        embed.set_author(name=self.author.display_name,
                        icon_url=self.author.avatar_url)
        draw_sched.draw_schedule(self.schedules[page_number])
        file = discord.File("schedule.png", filename="image.png")
        embed.set_image(url="attachment://image.png")
        self.new_message = await self.destination.send(file=file, embed=embed)
        if self.message:
            await self.message.delete()
        self.message = self.new_message
        self._bot.loop.create_task(self.message.add_reaction(LEFT_EMOJI))
        self._bot.loop.create_task(self.message.add_reaction(RIGHT_EMOJI))

    async def build_pages(self) -> None:
        self._pages = self.schedules

    async def prepare(self) -> None:
        await self.build_pages()
        await self.update_page()
        self._bot.add_listener(self.on_reaction_add)

    @classmethod
    async def start(cls, ctx: Context, *command, **options) -> "ScheduleSession":
        session = cls(ctx, *command, **options)
        await session.prepare()
        return session

    async def stop(self) -> None:
        self._bot.remove_listener(self.on_reaction_add)
        await self.message.clear_reactions()

    async def timeout(self, seconds: int = 60) -> None:
        await asyncio.sleep(seconds)
        await self.stop()

    def reset_timeout(self) -> None:
        if self._timeout_task:
            if not self._timeout_task.cancelled():
                self._timeout_task.cancel()
        self._timeout_task = self._bot.loop.create_task(self.timeout())

    async def do_back(self) -> None:
        if self._current_page != 0:
            await self.update_page(self._current_page-1)
        else:
            await self.update_page(len(self._pages)-1)

    async def do_next(self) -> None:
        if self._current_page != (len(self._pages)-1):
            await self.update_page(self._current_page+1)
        else:
            await self.update_page(0)

    async def on_reaction_add(self, reaction: Reaction, user: User) -> None:
        emoji = str(reaction.emoji)
        if (reaction.message.id != self.message.id) or\
           (user.id != self.author.id) or\
           (emoji not in (LEFT_EMOJI, RIGHT_EMOJI)):
            return
        self.reset_timeout()
        if emoji == LEFT_EMOJI:
            await self.do_back()
        elif emoji == RIGHT_EMOJI:
            await self.do_next()
        with suppress(HTTPException):
            await self.message.remove_reaction(reaction, user)

class Schedule(DiscordCog):
    @commands.command('schedule')
    async def new_schedule(self, ctx: Context, *args) -> None:
        try:
            await ScheduleSession.start(ctx, *args)
        except:
            embed = Embed()
            embed.colour = Colour.red()
            embed.title = str("Unknown error")
            await ctx.send(embed=embed)

def setup(bot: commands.Bot) -> None:
    bot.add_cog(Schedule())
