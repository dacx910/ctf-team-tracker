import asyncio
import os
from enum import Enum
from typing import Optional

from dotenv import load_dotenv
import discord
from discord import app_commands
from discord.ext import commands

import db

load_dotenv()
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()  # Start with default intents (non-privileged)

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await bot.tree.sync()

@bot.tree.command(name='who', description='Get a list of who is doing what problem')
async def get_doing(interaction: discord.Interaction):
    doings = await db.get_doing(interaction.guild_id)

    description = ''
    for user_id, problem in doings:
        description += f'- <@{user_id}> is working on {problem}\n';

    if description == '':
        description = 'Nobody is doing anything!'

    embed = discord.Embed(
        title=':tools: Problems in progress',
        description=description,
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name='start', description='Start doing a problem (not mutually exclusive)')
async def start(interaction: discord.Interaction, problem_name: str):
    user_ids = await db.start(interaction.guild_id, interaction.user.id, problem_name)

    if user_ids:
        description = ''
        for user_id in user_ids:
            description += f'- <@{user_id}>\n';
        embed = discord.Embed(
                title=':ballot_box_with_check: This problem was already completed!',
                description=description,
                color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
        return

    embed = discord.Embed(
            title=':white_check_mark: Started a problem',
            description=f'{interaction.user.mention} now working on {problem_name}!',
            color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name='stop', description='Stop doing a problem')
async def stop(interaction: discord.Interaction, problem_name: str):
    await db.stop(interaction.guild_id, interaction.user.id, problem_name)

    embed = discord.Embed(
            title=':octagonal_sign: Stopped a problem',
            description=f'{interaction.user.mention} is no longer working on {problem_name}!',
            color=discord.Color.red()
    )
    await interaction.response.send_message(embed=embed)

class LeaderboardType(Enum):
    ALL = 'all'
    PROBLEMS = 'problems'
    WRITEUPS = 'write-ups'

@bot.tree.command(name='leaderboard', description='Get the leaderboard! Can be problems, write-ups, or both!')
async def get_leaderboard(interaction: discord.Interaction, leaderboard_type: Optional[LeaderboardType] = LeaderboardType.ALL):
    if leaderboard_type == LeaderboardType.ALL:
        title = ':trophy: Full Leaderboard'
        none = 'No solves or write-ups yet!'
        leaderboard = await db.get_leaderboard_all(interaction.guild_id)
    elif leaderboard_type == LeaderboardType.PROBLEMS:
        title = ':trophy: Problem Leaderboard'
        none = 'No solves yet!'
        leaderboard = await db.get_leaderboard_challenges(interaction.guild_id)
    else:
        title = ':trophy: Write-up Leaderboard'
        none = 'No write-ups yet!'
        leaderboard = await db.get_leaderboard_writeups(interaction.guild_id)

    description = ''
    for user_id, points in leaderboard:
        description += f'<@{user_id}> - {points}\n'
    if description == '':
        description = none

    embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name='solve', description='Update the leaderboard with your solve!')
async def solve(interaction: discord.Interaction, problem_name: str):
    result = await db.solve_challenge(interaction.guild_id, interaction.user.id, problem_name)

    if result:
        embed = discord.Embed(
                title=':triangular_flag_on_post: Solved!',
                description=f'{interaction.user.mention} has solved {problem_name}!',
                color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
                title='Already solved!',
                description=f'{interaction.user.mention} has already solved {problem_name}.',
                color=discord.Color.red()
        )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name='write-up', description='Update the leaderboard with your write-up!')
async def write_up(interaction: discord.Interaction, problem_name: str):
    result = await db.submit_writeup(interaction.guild_id, interaction.user.id, problem_name)

    if result:
        embed = discord.Embed(
                title=':pencil: Write-up submitted!',
                description=f'{interaction.user.mention} submitted a write-up for {problem_name}!',
                color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
                title='Write-up submitted!',
                description=f'{interaction.user.mention} has already submitted a write-up for {problem_name}.',
                color=discord.Color.red()
        )

    await interaction.response.send_message(embed=embed)


async def setup():
    if not DISCORD_BOT_TOKEN:
        raise SystemExit('DISCORD_BOT_TOKEN not set')
    await db.create()


if __name__ == '__main__':
    asyncio.run(setup())
    bot.run(DISCORD_BOT_TOKEN)
