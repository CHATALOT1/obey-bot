import discord
from discord.ext import commands

import asyncio
import aiohttp
from os import getenv
from typing import List, Dict

from utils import done_callback


def interpret_server_list(data: str, maximum: int = 0) -> List[Dict]:
    """
    :param data: the raw data grabbed from http://ms.obeygame.com/serverList.php
    :param maximum: the maximum number of servers to include in the returned list
    :return: A list of dicts containing each server name the player count of each
    server, and the maximum number of players allowed on each server
    """
    # separate servers
    split_data = data.split("§")
    servers = [split_data[i : i + 16] for i in range(0, len(split_data), 16)][:-1]

    result = []
    for server in servers:
        result.append(
            {
                "name": server[2],
                "player_count": int(server[4]),
                "max_players": int(server[6]),
            }
        )

    result.sort(key=lambda k: k["player_count"], reverse=True)
    if maximum > 0:
        result = result[: maximum - 1]

    return result


class UserCount(commands.Cog):
    http_session = aiohttp.ClientSession()

    def __init__(self, client):
        self.client = client

        self.task = self.client.loop.create_task(self.update_player_counts_task())
        self.task.add_done_callback(done_callback)

    def cog_unload(self):
        self.task.cancel()

    async def update_player_counts_task(self):
        await self.client.wait_until_ready()
        while not self.client.is_closed():
            await self.update_player_counts()
            await asyncio.sleep(300)

    async def update_player_counts(self):
        """
        Requests the server list and updates the guild name/channels as needed.
        """
        guild = self.client.get_guild(int(getenv("MAIN_GUILD_ID")))
        category = guild.get_channel(int(getenv("SERVER_LIST_CATEGORY_ID")))

        # Get and process the server list
        async with self.http_session.get(
            "http://ms.obeygame.com/serverList.php"
        ) as resp:
            server_list = interpret_server_list(await resp.text(), 8)

        existing_channels = {
            " - ".join(channel.name.split(" - ")[1:]): channel
            for channel in category.channels
            if isinstance(channel, discord.VoiceChannel)
        }
        for server in server_list:
            new_channel_name = (
                f"{server['player_count']}/{server['max_players']} - "
                f"{server['name']}"
            )
            if server["name"] in existing_channels.keys():
                existing_channel = existing_channels.pop(server["name"])

                # Update the channel name
                if not existing_channel.name == new_channel_name:
                    await existing_channel.edit(name=new_channel_name)
            else:
                await category.create_voice_channel(name=new_channel_name)

        # Delete any channels remaining in existing_channels, must no longer be open
        # (Could also mean there are more servers open then the maximum set)
        for channel in existing_channels.values():
            await channel.delete()

    @commands.command(name="update_player_counts", aliases=["update"])
    async def _update_player_counts(self, ctx):
        await self.update_player_counts()
        await ctx.send("Update done!")


def setup(client):
    client.add_cog(UserCount(client))
