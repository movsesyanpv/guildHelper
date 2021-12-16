from abc import ABC

import discord
from discord import ApplicationContext, DiscordException
import json
import sqlite3
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import datetime
import traceback


class NickTooLong(Exception):

    def __init__(self, message='Никнейм слишком длинный'):
        self.message = message
        super().__init__(self.message)


class ClanHelper(discord.Bot, ABC):
    api_data_file = open('api.json', 'r')
    api_data = json.loads(api_data_file.read())

    task_db = sqlite3.connect('tasks.db')
    task_cursor = task_db.cursor()

    nick_db = sqlite3.connect('nicknames.db')
    nick_cursor = nick_db.cursor()

    sched = AsyncIOScheduler(timezone='UTC')

    def __init__(self, **options):
        super().__init__(**options)
        try:
            self.task_cursor.execute('''CREATE TABLE tasks ( server_id integer, member_id integer, old_nick text, timestamp integer)''')
            self.task_db.commit()
        except sqlite3.OperationalError:
            pass

    async def on_ready(self):
        self.task_cursor.execute('''SELECT * FROM tasks''')
        task_list = self.task_cursor.fetchall()
        for task in task_list:
            undo_time = datetime.datetime.utcfromtimestamp(task[3])
            if undo_time < datetime.datetime.utcnow():
                await self.undo_kirkorov(task[1], task[0], task[2])
            else:
                self.sched.add_job(self.undo_kirkorov, 'date', run_date=undo_time, args=[task[1], task[0], task[2]])
        self.sched.start()

    def startup(self):
        self.run(self.api_data['token'])

    async def make_kirkorov(self, member: discord.Member):
        old_nick = member.nick if member.nick is not None else member.name
        try:
            nick = self.nick_cursor.execute('''SELECT nick FROM nicknames ORDER BY RANDOM() LIMIT 1;''').fetchone()
            nick_prefix = nick[0]
            undo_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=604800)
            timestamp = int(undo_time.timestamp())
            self.task_cursor.execute('''INSERT INTO tasks (server_id, member_id, old_nick, timestamp) VALUES (?,?,?,?)''', (member.guild.id, member.id, old_nick, timestamp))
            self.task_db.commit()
            self.sched.add_job(self.undo_kirkorov, 'date', run_date=undo_time, args=[member.id, member.guild.id, old_nick])
            new_nick = '{} ({})'.format(nick_prefix, old_nick)
            if len(new_nick) > 32:
                raise NickTooLong(nick_prefix)
            await member.edit(nick=new_nick, reason='Протокол КИРКОРОВ')
        except sqlite3.OperationalError:
            pass

    async def undo_kirkorov(self, member_id, guild_id, old_nick):
        guild = await self.fetch_guild(guild_id)
        member = await guild.fetch_member(member_id)

        self.task_cursor.execute('''DELETE FROM tasks WHERE member_id=?''', (member_id,))
        self.task_db.commit()
        await member.edit(nick=old_nick, reason='Протокол КИРКОРОВ истек')

    async def on_application_command_error(
        self, context: ApplicationContext, exception: DiscordException
    ) -> None:
        bot_info = await self.application_info()
        owner = bot_info.owner
        if owner.dm_channel is None:
            await owner.create_dm()
        traceback_str = ''
        for line in traceback.format_exception(type(exception), exception, exception.__traceback__):
            traceback_str = '{}{}'.format(traceback_str, line)
        await owner.dm_channel.send('`{}`'.format(traceback_str))
        command_line = '/{}'.format(context.interaction.data['name'])
        for option in context.interaction.data['options']:
            command_line = '{} {}:{}'.format(command_line, option['name'], option['value'])
        await owner.dm_channel.send('{}:\n{}'.format(context.author, command_line))
        if context.author.dm_channel is None:
            await context.author.create_dm()
        if context.author != owner:
            await context.author.dm_channel.send(self.translations['en']['error'])
