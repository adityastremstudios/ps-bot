from __future__ import annotations

import typing as T

if T.TYPE_CHECKING:
    from core import Quotient

import inspect
import os
import time

import discord
from core import Context
from discord.ext import commands

from quotient.models import Guild


class Miscellaneous(commands.Cog):
    def __init__(self, bot: Quotient):
        self.bot = bot

    @commands.command(aliases=("src",))
    async def source(self, ctx: Context, *, search: T.Optional[str]):
        """Refer to the source code of the bot commands."""
        source_url = "https://github.com/quotientbot/Quotient-Bot"

        if search is None:
            return await ctx.send(f"<{source_url}>")

        command = ctx.bot.get_command(search)

        if not command:
            return await ctx.send("Couldn't find that command.")

        src = command.callback.__code__
        filename = src.co_filename
        lines, firstlineno = inspect.getsourcelines(src)

        location = os.path.relpath(filename).replace("\\", "/")

        final_url = f"<{source_url}/blob/main/{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}>"
        await ctx.send(final_url)

    @commands.hybrid_command(aliases=("inv",))
    async def invite(self, ctx: Context):
        """Quotient Invite Links."""
        v = discord.ui.View(timeout=None)
        v.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.link,
                label="Invite Quotient (Free)",
                url=os.getenv("QUOTIENT_INVITE_LINK"),
                row=1,
            )
        )
        v.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.link,
                label="Invite Quotient Pro (Premium Only)",
                url=os.getenv("PRO_INVITE_LINK"),
                row=2,
            )
        )
        v.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.link,
                label="Join Support Server",
                url=os.getenv("SUPPORT_SERVER_LINK"),
                row=3,
            )
        )

        await ctx.reply(view=v)

    @commands.hybrid_command()
    async def contributors(self, ctx):
        """People who made Quotient Possible."""
        url = f"https://api.github.com/repos/quotientbot/Quotient-Bot/contributors"

        e = discord.Embed(
            title=f"Project Contributors",
            color=self.bot.color,
            timestamp=self.bot.current_time,
        )
        e.description = ""
        async with self.bot.session.get(url) as response:
            data = await response.json()
            for idx, contributor in enumerate(data, start=1):
                if contributor["type"] == "Bot":
                    continue

                e.description += f"`{idx:02}.` [{contributor['login']} ({contributor['contributions']})]({contributor['html_url']})\n"

        await ctx.reply(embed=e)

    @commands.hybrid_command()
    @commands.has_permissions(manage_guild=True)
    async def prefix(self, ctx: Context, *, new_prefix: str = None):
        """Change your server's prefix"""

        if not new_prefix:

            return await ctx.send(
                embed=self.bot.simple_embed(
                    "Current prefix of this server is `{0}`".format(self.bot.cache.prefixes.get(ctx.guild.id, self.bot.default_prefix))
                )
            )

        if len(new_prefix) > 5:
            return await ctx.reply(embed=self.bot.error_embed("Prefix cannot contain more than `5 characters`."))

        self.bot.cache.prefixes[ctx.guild.id] = new_prefix
        await Guild.filter(guild_id=ctx.guild.id).update(prefix=new_prefix)
        await ctx.reply(embed=self.bot.success_embed(f"Updated server prefix to: `{new_prefix}`"))

    @commands.command()
    async def ping(self, ctx: Context):
        """Check how the bot is doing"""
        await ctx.send(f"Bot: `{round(self.bot.latency*1000, 2)} ms`, Database: `{await self.get_db_latency()}`")

    async def get_db_latency(self):
        t1 = time.perf_counter()
        await self.bot.my_pool.fetchval("SELECT 1;")
        t2 = time.perf_counter() - t1
        return f"{t2*1000:.2f} ms"


async def setup(bot: Quotient):
    await bot.add_cog(Miscellaneous(bot))
