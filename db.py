import sqlite3
import os
import asyncio

SQLITE_DB = os.getenv('SQLITE_DB', 'stats.db')
CHALLENGE = 0
WRITEUP = 1

SOLVING = 0
DONE = 1
STOPPED = 2

conn = sqlite3.connect(SQLITE_DB)
lock = asyncio.Lock()

async def create():
    async with lock:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                name TEXT,
                type INTEGER,
                status INTEGER
            )
        ''')
        conn.commit()


async def _submit(guild_id, user_id, name, point_type):
    async with lock:
        cursor = conn.cursor()

        # make sure not solved before
        cursor.execute('''
            SELECT status
            FROM points
            WHERE
                guild_id = ? AND
                user_id = ? AND
                name = ? AND
                type = ?
        ''', (guild_id, user_id, name, point_type))
        row = cursor.fetchone()

        # never seen before
        if row is None:
            cursor.execute('''
                INSERT INTO points (guild_id, user_id, name, type, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (guild_id, user_id, name, point_type, DONE))
            conn.commit()
            return True
        # if was solving
        elif row[0] == SOLVING or row[0] == STOPPED:
            cursor.execute('''
                UPDATE points
                SET status = ?
                WHERE
                    guild_id = ? AND
                    user_id = ? AND
                    name = ? AND
                    type = ?
            ''', (DONE, guild_id, user_id, name, point_type))
            conn.commit()
            return True
        # if solved
        else:
            return False


async def solve_challenge(guild_id, user_id, name):
    return await _submit(guild_id, user_id, name, CHALLENGE)


async def submit_writeup(guild_id, user_id, name):
    return await _submit(guild_id, user_id, name, WRITEUP)


async def _get_leaderboard(guild_id, point_type=None):
    async with lock:
        cursor = conn.cursor()

        if point_type is None:
            cursor.execute('''
                SELECT user_id, COUNT(type) as score
                FROM points
                WHERE
                    guild_id = ? AND
                    status = ?
                GROUP BY user_id
                ORDER BY score DESC
            ''', (guild_id, DONE))
        else:
            cursor.execute('''
                SELECT user_id, COUNT(type) as score
                FROM points
                WHERE
                    guild_id = ? AND
                    type = ? AND
                    status = ?
                GROUP BY user_id
                ORDER BY score DESC
            ''', (guild_id, point_type, DONE))

        return cursor.fetchall()


async def get_leaderboard_all(guild_id):
    return await _get_leaderboard(guild_id)


async def get_leaderboard_writeups(guild_id):
    return await _get_leaderboard(guild_id, WRITEUP)


async def get_leaderboard_challenges(guild_id):
    return await _get_leaderboard(guild_id, CHALLENGE)


async def start(guild_id, user_id, name):
    async with lock:
        cursor = conn.cursor()

        # if you're trying to do a problem,
        # make sure not done by anyone in the guild
        cursor.execute('''
            SELECT user_id
            FROM points
            WHERE
                guild_id = ? AND
                name = ? AND
                type = ? AND
                status = ?
        ''', (guild_id, name, CHALLENGE, DONE))
        rows = cursor.fetchall()

        if len(rows) > 0:
            return rows

        cursor.execute('''
            INSERT INTO points (guild_id, user_id, name, type, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (guild_id, user_id, name, CHALLENGE, SOLVING))
        conn.commit()

async def stop(guild_id, user_id, name):
    async with lock:
        cursor = conn.cursor()

        # check if already doing or done
        cursor.execute('''
            SELECT status
            FROM points
            WHERE
                guild_id = ? AND
                user_id = ? AND
                name = ? AND
                type = ?
        ''', (guild_id, user_id, name, CHALLENGE))
        row = cursor.fetchone()

        if row is None: # can't stop if not started
            pass
        elif row[0] == DOING: # update row if doing
            cursor.execute('''
                UPDATE points
                    SET status = ?
                WHERE
                    guild_id = ? AND
                    user_id = ? AND
                    name = ? AND
                    type = ?
            ''', (STOPPED, guild_id, user_id, name, CHALLENGE))
            conn.commit()
        # do nothing if done


async def get_doing(guild_id):
    async with lock:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, name
            FROM points
            WHERE
                guild_id = ? AND
                type = ? AND
                status = ?
        ''', (guild_id, CHALLENGE, SOLVING))
        rows = cursor.fetchall()

        return rows


async def clear_doing(guild_id):
    async with lock:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE points
                SET status = ?
            WHERE
                guild_id = ? AND
                type = ?
        ''', STOPPED, guild_id, CHALLENGE)
        conn.commit()
