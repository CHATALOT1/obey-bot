import discord

from os import getenv
import asyncio
from typing import Optional, Union

UNIFORM_EMBED_DEFAULTS = {}


def get_and_split_env(var: str):
    try:
        return [int(f) for f in getenv(var).split(";")]
    except (IndexError, AttributeError):
        return []
    except ValueError:
        return [f for f in getenv(var).split(";")]


async def add_reactions(message, *reacs):
    for reac in reacs:
        await message.add_reaction(reac)


def done_callback(task: asyncio.Task):
    if task.exception():
        task.print_stack()


def uniform_embed(
    requesting_user: Optional[Union[discord.User, discord.Member]] = None, **kwargs
):
    """
    For creating embeds uniform throughout the bot.

    Creates an embed, passing in the kwargs combined with but overwriting some default kwargs.
    Has an author already set and the possibility to pass in a requesting user as explained below.

    :param requesting_user: The discord.User or discord.Member that requested the embed's creation to be displayed in
    the footer, None if not applicable.
    :rtype discord.Embed
    """
    embed_kwargs = UNIFORM_EMBED_DEFAULTS["kwargs"].copy()
    embed_kwargs.update(kwargs)
    embed = discord.Embed(**embed_kwargs)
    embed.set_author(**UNIFORM_EMBED_DEFAULTS["author"])
    if requesting_user is not None:
        embed.set_footer(
            text=f"Requested by {requesting_user} ({requesting_user.id})",
            icon_url=requesting_user.avatar_url,
        )
    return embed


def split_message(
    message: str,
    each_message_start: str = "",
    each_message_end: str = "",
    character_limit: int = 2000,
):
    character_limit = character_limit - (
        len(each_message_start) + len(each_message_end)
    )
    lines = message.splitlines(keepends=True)
    messages = [each_message_start]
    for line in lines:
        if len(messages[-1] + line) <= character_limit:
            messages[-1] = messages[-1] + line
        else:
            messages.append(each_message_start + line)
    for index, message in enumerate(messages):
        messages[index] = message + each_message_end

    return messages


async def split_and_send(
    message: str,
    channel: discord.abc.Messageable,
    each_message_start: str = "",
    each_message_end: str = "",
):

    for chunk in split_message(message, each_message_start, each_message_end):
        await channel.send(chunk)


async def split_and_send_embed(
    message: str,
    channel: discord.abc.Messageable,
    use_uniform: bool = True,
    requesting_user: Optional[Union[discord.User, discord.Member]] = None,
    **kwargs,
):
    if not use_uniform and requesting_user is not None:
        raise ValueError("requesting_user argument is only valid if use_inform is True")

    async with channel.typing():
        embeds = []

        if use_uniform:
            for chunk in split_message(
                message,
                character_limit=6000 - len(uniform_embed(requesting_user, **kwargs)),
            ):
                embeds.append(
                    uniform_embed(requesting_user, description=chunk, **kwargs)
                )
        else:
            for chunk in split_message(
                message, character_limit=6000 - len(discord.Embed(**kwargs))
            ):
                embeds.append(discord.Embed(**kwargs))

        for embed in embeds:
            await channel.send(embed=embed)
