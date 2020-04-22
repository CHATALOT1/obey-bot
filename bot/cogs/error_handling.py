from utils import get_and_split_env, add_reactions, split_and_send
from traceback import format_exception
from asyncio import TimeoutError
from os import getenv

from discord.ext import commands
import logging

logger = logging.getLogger("bot")


class ErrorHandling(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_command_error(self, ctx, exc):
        if (
            isinstance(exc, commands.CheckFailure)
            or isinstance(exc, commands.CommandNotFound)
            or isinstance(exc, commands.DisabledCommand)
        ):
            return

        if isinstance(exc, commands.CommandInvokeError):
            if ctx.author.id in get_and_split_env("DEV_IDS"):
                await ctx.send(
                    "Error raised! Since you're a developer, I'm DMing you the traceback."
                )
                logger.error(f"error was raised by a developer: {exc}")
                await split_and_send(
                    f"py\n{''.join(format_exception(type(exc), exc, exc.__traceback__))}\n",
                    ctx.author,
                    "```",
                    "```",
                )
                return

            await self.handle_error_reporting(ctx, exc)
            return

        await ctx.send(exc)

    async def handle_error_reporting(self, ctx, exc):
        reactions = ["\U0001f1fe", "\U0001f1f3"]
        report_channel = self.client.get_channel(int(getenv("ERROR_CHANNEL_ID")))

        confirm_report_msg = await ctx.send("An unexpected error occurred, report?")
        await add_reactions(confirm_report_msg, *reactions)

        try:
            response, user = await self.client.wait_for(
                "reaction_add",
                check=lambda r, u: u.id == ctx.author.id
                and r.emoji in reactions
                and r.message.id == confirm_report_msg.id
                and r.message.channel.id == confirm_report_msg.channel.id,
                timeout=30,
            )

        except TimeoutError:
            await confirm_report_msg.edit(
                content=f"~~{confirm_report_msg.content}~~ Time's up!"
            )
            return

        if response.emoji == reactions[0]:
            await report_channel.send(
                f"Exception raised:\nUser: {ctx.author} ({ctx.author.id})"
                f"\nCommand: {ctx.command}\nCog: {ctx.command.cog_name}"
                f"\nTraceback:"
            )
            await split_and_send(
                f"py\n{''.join(format_exception(type(exc), exc, exc.__traceback__))}\n",
                report_channel,
                "```",
                "```",
            )
            await confirm_report_msg.edit(
                content=f"~~{confirm_report_msg.content}~~ Error reported!"
            )

        else:
            await confirm_report_msg.edit(
                content=f"~~{confirm_report_msg.content}~~ Error ignored."
            )


def setup(client):
    client.add_cog(ErrorHandling(client))
