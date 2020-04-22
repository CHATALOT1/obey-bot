import discord
from discord.ext import commands
from discord.ext.commands.errors import BadArgument

from jishaku.codeblocks import codeblock_converter

import asyncio
from dotenv import load_dotenv
import json
from typing import Optional

from utils import get_and_split_env

MEANS_TRUE = ["y", "yes", "t", "true", "mhm"]


class MentionConverter(commands.Converter):
    async def convert(self, ctx, argument):
        if argument.lower().endswith("everyone"):
            return "@everyone"
        if argument.lower().endswith("here"):
            return "@here"

        try:
            converter = commands.RoleConverter()
            role = await converter.convert(ctx, argument)
            return role.mention
        except (commands.NoPrivateMessage, BadArgument):
            pass

        try:
            converter = commands.MemberConverter()
            user = await converter.convert(ctx, argument)
            return user.mention
        except BadArgument:
            pass

        raise BadArgument(f'mention for "{argument}" could not be created')


class TrueConverter(commands.Converter):
    async def convert(self, ctx, argument):
        if argument.lower() in MEANS_TRUE:
            return True
        raise BadArgument("Message did not look like True")


class DevTools(commands.Cog, name="Developer Commands"):
    def __init__(self, client):
        self.client = client

    def cog_check(self, ctx):
        return ctx.author.id in get_and_split_env("DEV_IDS")

    @commands.command()
    async def say(self, ctx, mention: Optional[MentionConverter], *, content: str):
        if mention is not None:
            content = f"{mention} {content}"

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        await ctx.send(content)

    @commands.command(aliases=["reloadenv"])
    async def reload_env(self, ctx):
        await self.client.loop.run_in_executor(None, lambda: load_dotenv(override=True))
        await ctx.send(
            ".env file reloaded, you may need to reload the relevant extensions in some cases."
        )

    @commands.command(aliases=["sendembedfromjson", "sefj", "embed"])
    async def send_embed_from_json(
        self,
        ctx,
        debug: Optional[TrueConverter],
        mention: Optional[MentionConverter],
        *,
        raw_data: codeblock_converter,
    ):
        try:
            embed_data = json.loads(raw_data[1])
        except json.JSONDecodeError:
            return await ctx.send(
                "The data inputted was not of valid JSON format, please try again"
            )

        try:
            embed = discord.Embed.from_dict(embed_data)
        except AttributeError:
            return await ctx.send(
                "The data inputted could not be converted to a discord.Embed object"
            )

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        try:
            await ctx.send(mention, embed=embed)
        except discord.HTTPException:
            error_response = "The data inputted could not be sent (may not have made anything or could've been formatted wrong)"
            if debug:
                error_response += ". Debug turned on, re-raising"

            await ctx.send(error_response)

            if debug:
                raise


def setup(client):
    client.add_cog(DevTools(client))
