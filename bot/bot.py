import asyncio
import logging.config
from dotenv import load_dotenv
from os import getenv, path, listdir, chdir
import sys

import discord
from discord.ext import commands

from utils import get_and_split_env

chdir(path.join(path.dirname(path.realpath(__file__)), ".."))
load_dotenv()

HANDLERS = {
    "console": {
        "class": "logging.StreamHandler",
        "level": getenv("LOG_LEVEL"),
        "formatter": "default",
    },
    "file": {
        "class": "logging.handlers.RotatingFileHandler",
        "level": getenv("LOG_LEVEL"),
        "filename": path.join(path.dirname(path.realpath(__file__)), "..", "debug.log"),
        "maxBytes": 1024 * 1024,
        "backupCount": 3,
        "formatter": "default",
    },
}
CONFIG_FOR_LOGGERS = {"level": getenv("LOG_LEVEL"), "handlers": ["console", "file"]}
LOGGING_CONFIG = {
    "version": 1,
    "formatters": {"default": {"format": "%(asctime)s - %(levelname)s - %(message)s"}},
    "handlers": HANDLERS,
    # "root": CONFIG_FOR_LOGGERS,
    "loggers": {"bot": CONFIG_FOR_LOGGERS},
}
logging.config.dictConfig(LOGGING_CONFIG)

logger = logging.getLogger("bot")


def prefix(client, message) -> list:
    prefixes = getenv("BOT_COMMAND_PREFIXES").split(";")

    if message.content.strip() == "" or message.type != discord.MessageType.default:
        return prefixes

    start_of_message = message.content.split()[0]

    if start_of_message.lower() in prefixes:
        return start_of_message

    for pref in prefixes:
        if pref.endswith(" ") and start_of_message.lower() == pref[:-1]:
            return start_of_message + " "

    return prefixes


class Bot(commands.Bot):
    # Overwrites default owner check to allow for multiple owners as defined in .env
    async def is_owner(self, user: discord.User):
        if user.id in get_and_split_env("DEV_IDS"):
            return True

        # Else fall back to the original
        return await super().is_owner(user)


bot = Bot(command_prefix=prefix, case_insensitive=True)


async def setup(bot):
    logger.info("Initialising...")

    @bot.event
    async def on_ready():
        logger.info(f"Active on bot {bot.user} with ID {bot.user.id}")

    @bot.check
    async def bot_check(ctx):
        if ctx.author.id not in get_and_split_env("DEV_IDS"):
            if isinstance(ctx.channel, discord.DMChannel):
                return False  # Non-developers cannot run commands in DMs

            return ctx.guild.id in [
                int(getenv("MAIN_GUILD_ID")),
                *get_and_split_env("SECONDARY_GUILD_IDS"),
            ]
        return True  # Developers can run commands no matter what

    for filename in listdir("Bot/cogs"):
        if filename.endswith(".py"):
            try:
                bot.load_extension(f"cogs.{filename[0:-3]}")
                logger.debug(f"cog extension {filename[0:-3]} loaded successfully")
            except commands.ExtensionError as e:
                logger.error(e)
    bot.load_extension("jishaku")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.create_task(setup(bot))
        loop.create_task(bot.start(getenv("BOT_TOKEN")))
        loop.run_forever()
    except KeyboardInterrupt:
        logger.debug("KeyboardInterrupt")
    finally:
        logger.info("Logging out from discord")
        loop.run_until_complete(bot.logout())
        logger.info("Logged out from discord")
    logger.debug("Closing loop")
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()
    logger.debug("Terminating program")
    sys.exit(0)
