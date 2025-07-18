import asyncio
import os
import sys
from time import time
from typing import Literal, Optional
import discord
from discord.ext import commands


class Dev(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def sync(
        self,
        ctx: commands.Context,
        guilds: commands.Greedy[discord.Object],
        spec: Optional[Literal["~"]] = None,
    ) -> None:
        """Sync AppCommands to guilds, or globally.
        Umbra's sync command.
        """
        # TODO: Change this
        if ctx.author.id == 733954056787198002:
            if not guilds:
                if spec == "~":
                    ctx.bot.tree.copy_global_to(guild=ctx.guild)
                    fmt = await ctx.bot.tree.sync(guild=ctx.guild)
                else:
                    fmt = await ctx.bot.tree.sync()

                await ctx.reply(
                    f"Synced {len(fmt)} commands "
                    f"{'globally' if spec is None else 'to the current guild.'}"
                )
                return

            fmt = 0
            for guild in guilds:
                try:
                    await ctx.bot.tree.sync(guild=guild)
                except discord.HTTPException:
                    pass
                else:
                    fmt += 1

            await ctx.reply(f"Synced the tree to {fmt}/{len(guilds)} guilds.")

    @commands.group(aliases=["cogs"], invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def cog(self, ctx):
        guild_pfp = ctx.guild.icon

        list_cogs = "\n".join(str(f"{cog}") for cog in self.bot.cogs)

        cog_embed = discord.Embed(
            title="cogs", description=f"""```{list_cogs}```""", color=0x9013FE
        )
        cog_embed.set_author(name="Dank Renegade", icon_url=guild_pfp)

        cog_embed.add_field(
            name="commands", value="`load`, `unload`, `reload`,  `loaded`, `restart`"
        )

        await ctx.reply(embed=cog_embed)

    @cog.command()
    @commands.has_permissions(administrator=True)
    async def load(self, ctx, cog_name):
        try:
            await self.bot.load_extension(f"cogs.{cog_name}")
            await ctx.reply(f"{cog_name} has been loaded")
        except commands.ExtensionAlreadyLoaded:
            await ctx.send("Cog is loaded")
        except commands.ExtensionNotFound:
            await ctx.send("Cog not found")

    @cog.command()
    @commands.has_permissions(administrator=True)
    async def unload(self, ctx, cog_name):
        try:
            await self.bot.unload_extension(f"cogs.{cog_name}")
            await ctx.reply(f"{cog_name} has been unloaded")
        except Exception as e:
            await ctx.send({e})

    @cog.command()
    @commands.has_permissions(administrator=True)
    async def loaded(self, ctx):
        await ctx.invoke(self.bot.get_command("cog"))

    @cog.command()
    @commands.has_permissions(administrator=True)
    async def reload(self, ctx, cog_name):
        try:
            await self.bot.load_extension(f"cogs.{cog_name}")
            await ctx.reply(f"{cog_name} has been loaded")
        except commands.ExtensionAlreadyLoaded:
            await self.bot.unload_extension(f"cogs.{cog_name}")
            dele = await ctx.send("reloading....")
            await asyncio.sleep(5)
            await self.bot.load_extension(f"cogs.{cog_name}")
            await dele.delete()
            await ctx.send(f"{cog_name} has been reloaded")
        except commands.ExtensionNotFound:
            await ctx.send("Cog not found")
        else:
            await self.bot.unload_extension(f"cogs.{cog_name}")
            dele = await ctx.send("reloading....")
            await asyncio.sleep(5)
            await self.bot.load_extension(f"cogs.{cog_name}")
            await dele.delete()
            await ctx.send(f"{cog_name} has been reloaded")

    @cog.command()
    @commands.has_permissions(administrator=True)
    async def restart(self, ctx):
        for cog_new in os.listdir("cogs"):
            if cog_new.endswith(".py"):
                cog = f"cogs.{cog_new.replace('.py', '')}"
                try:
                    await self.bot.load_extension(cog)
                except commands.ExtensionAlreadyLoaded:
                    pass
                except Exception as e:
                    await ctx.reply(e)
                else:
                    await asyncio.sleep(1)
                    await ctx.send(f"{cog} has been reload")

    def resolve_variable(self, variable):
        if hasattr(variable, "__iter__"):
            var_length = len(list(variable))
            if (var_length > 100) and (not isinstance(variable, str)):
                return f"<a {type(variable).__name__} iterable with more than 100 values ({var_length})>"
            elif not var_length:
                return f"<an empty {type(variable).__name__} iterable>"

        if (not variable) and (not isinstance(variable, bool)):
            return f"<an empty {type(variable).__name__} object>"
        return (
            variable
            if (len(f"{variable}") <= 1000)
            else f"<a long {type(variable).__name__} object with the length of {len(f'{variable}'):,}>"
        )

    def prepare(self, string):
        arr = string.strip("```").replace("py\n", "").replace("python\n", "").split("\n")
        if not arr[::-1][0].replace(" ", "").startswith("return"):
            arr[len(arr) - 1] = "return " + arr[::-1][0]
        return "".join(f"\n\t{i}" for i in arr)

    def content(self, string):
        arr = string.strip("```").replace("py\n", "").replace("python\n", "").split("\n")
        if not arr[::-1][0].replace(" ", ""):
            arr[len(arr) - 1] = arr[::-1][0]
        return "".join(f"\n\t{i}" for i in arr)

    @commands.command(pass_context=True, aliases=["eval", "exec", "evaluate", "ev"])
    async def _eval(self, ctx, *, code: str):
        if ctx.author.id == 733954056787198002:
            silent = "-s" in code
            content = self.content(code.replace("-s", ""))
            code = self.prepare(code.replace("-s", ""))
            args = {
                "discord": discord,
                "sys": sys,
                "os": os,
                "imp": __import__,
                "ctx": ctx,
                "self.bot": self.bot,
                "bot": self.bot,
                "asyncio.sleep": asyncio.sleep,
            }

            try:
                exec(f"async def func():{code}", args)
                a = time()
                response = await eval("func()", args)
                if silent or (response is None) or isinstance(response, discord.Message):
                    del args, code
                    return
                # message = ctx.message.content
                # content = ' '.join(message.split(' ')[2:])
                dev_em = discord.Embed()
                dev_em.add_field(name="Your Code", value=f"```py\n{content}```", inline=False)
                dev_em.add_field(
                    name="Your Code",
                    value=f"```{self.resolve_variable(response)}```",
                    inline=False,
                )
                dev_em.set_footer(
                    text=f"{round((time() - a) / 1000)} ms", icon_url=ctx.author.avatar
                )
                await ctx.send(embed=dev_em)
                # await ctx.send(f"```py\n{self.resolve_variable(response)}````{type(response).__name__} | {(time() - a) / 1000} ms`")
            except Exception as e:
                await ctx.send(f"Error occurred:```\n{type(e).__name__}: {str(e)}```")

            del args, code, silent

    @commands.command(aliases=["color"])
    async def colour(self, ctx):
        await ctx.reply("color=0x9013fe")


async def setup(bot):
    await bot.add_cog(Dev(bot))
