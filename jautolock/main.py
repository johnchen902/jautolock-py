#!/usr/bin/env python
"""main resides here"""
import argparse
import asyncio
import datetime
import os.path
import re
import jautolock.xidle as xidle
import xdg.BaseDirectory

def parse_time(text):
    """Parse time of form 1m30s into datetime.timedelta"""
    match = re.match('([0-9]+)([hms])', text)
    if not match:
        raise ValueError

    value = int(match.group(1))
    unit = {
        'h': datetime.timedelta(hours=1),
        'm': datetime.timedelta(minutes=1),
        's': datetime.timedelta(seconds=1),
    }[match.group(2)]
    time = value * unit

    remaining_text = text[match.end():]
    if remaining_text:
        time += parse_time(remaining_text)
    return time

class Task:
    """A task demanded by user"""
    AWAIT_BELOW = 1
    AWAIT_ABOVE = 2
    AWAIT_CHILD = 3
    def __init__(self, name, time, command):
        self.name = name
        self.time = time
        self.command = command
        self.state = Task.AWAIT_BELOW

def parse_task(text):
    """Parse a `Task`"""
    name, timetext, command = text.split(',', 2)
    time = parse_time(timetext)
    return Task(name, time, command)

class Daemon:
    """The daemon firing tasks at approprite time"""
    MAX_SLEEP_TIME = (2 ** 31 - 1) / 1000

    def __init__(self, tasks):
        self.idle_time = 0
        self.tasks = tasks
        self.event = asyncio.Event()
        self.busy = False

    def get_next_offset(self):
        """Get the maximum time to sleep before any task miss state transfer
           from STATE_BELOW to STATE_ABOVE"""
        answer = datetime.timedelta()
        for task in self.tasks:
            if task.state == Task.AWAIT_CHILD:
                answer = max(answer, task.time)
        return answer

    def get_sleep_time_below(self):
        """Get the maximum time to sleep before any task miss state transfer
           from STATE_BELOW to STATE_ABOVE"""
        answer = datetime.timedelta.max
        next_offset = self.get_next_offset()
        for task in self.tasks:
            if task.state == Task.AWAIT_BELOW and task.time > next_offset:
                answer = min(answer, task.time - next_offset)
        return answer

    def get_sleep_time_above(self):
        """Get the maximum time to sleep before any task miss state transfer
           from STATE_ABOVE to STATE_CHILD"""
        answer = datetime.timedelta.max
        for task in self.tasks:
            if task.state == Task.AWAIT_ABOVE:
                answer = min(answer, task.time - self.idle_time)
        return answer

    def get_sleep_time(self):
        """Get sleep time in milliseconds"""
        sleep_time = min(self.get_sleep_time_below(),
                         self.get_sleep_time_above())
        return min(sleep_time / datetime.timedelta(seconds=1),
                   Daemon.MAX_SLEEP_TIME)

    def get_raw_idle_time(self):
        """Get idle time without respect to active tasks"""
        if self.busy:
            return datetime.timedelta()
        return xidle.get_idle_time()

    async def main_loop(self):
        """Run this loop to make it happen"""
        last_time = None
        offset = datetime.timedelta()
        while True:
            this_time = self.get_raw_idle_time()
            if last_time is None or last_time > this_time:
                offset = self.get_next_offset()
            self.idle_time = this_time + offset
            last_time = this_time

            self.update_task_states()

            sleep_time = self.get_sleep_time()
            self.event.clear()
            try:
                await asyncio.wait_for(self.event.wait(), sleep_time)
            except asyncio.TimeoutError:
                pass

    async def run_task(self, task):
        """Run the specified task; return when the task is finished"""
        process = await asyncio.create_subprocess_shell(task.command)
        await process.wait()
        task.state = Task.AWAIT_BELOW
        self.event.set()

    def run_task_soon(self, task):
        """Schedule run of the specified task"""
        assert task.state != Task.AWAIT_CHILD
        task.state = Task.AWAIT_CHILD
        asyncio.ensure_future(self.run_task(task))

    def update_task_states(self):
        """Update states of all tasks"""
        for task in self.tasks:
            if task.state == Task.AWAIT_BELOW:
                if self.idle_time < task.time:
                    task.state = Task.AWAIT_ABOVE
            elif task.state == Task.AWAIT_ABOVE:
                if self.idle_time >= task.time:
                    self.run_task_soon(task)

    def run_task_by_name_soon(self, name):
        """Schedule run of all tasks with the specified name

        Returns list of tasks scheduled
        """
        scheduled_task = []
        for task in self.tasks:
            if task.name == name and task.state != Task.AWAIT_CHILD:
                self.run_task_soon(task)
                scheduled_task.append(task)
        return scheduled_task

class CommandHandler:
    """Handle user commands from a socket"""
    def __init__(self, daemon):
        self.daemon = daemon

    async def handle_command(self, command, writer):
        """Handle a single command"""
        command = command.rstrip()

        if command == b'busy':
            if self.daemon.busy:
                writer.write(b"You're already busy\n")
            else:
                self.daemon.busy = True
                writer.write(b"You're now busy\n")
        elif command == b'unbusy':
            if self.daemon.busy:
                self.daemon.busy = False
                writer.write(b"You're no longer busy\n")
            else:
                writer.write(b"You're not busy\n")
        elif command.startswith(b'now '):
            _, taskname = command.split(b' ', 1)
            tasks = self.daemon.run_task_by_name_soon(taskname.decode())
            writer.write(b'%d tasks fired\n' % len(tasks))
        else:
            writer.write(b'Unknown command: %r\n' % command)

    async def handle_connection(self, reader, writer):
        """Handle a connection"""
        try:
            while True:
                data = await reader.readline()
                if not data:
                    break
                await self.handle_command(data, writer)
                await writer.drain()
        except Exception as exc:
            writer.write(repr(exc).encode() + b'\n')
        else:
            writer.write(b'Bye!\n')
        finally:
            writer.close()

    async def start_unix_server(self, path):
        """Start an unix server at path"""
        await asyncio.start_unix_server(self.handle_connection, path)

def start(args):
    """The start action"""
    path = os.path.join(xdg.BaseDirectory.get_runtime_dir(strict=False),
                        'jautolock.socket')
    daemon = Daemon(args.tasks)
    cmd_handler = CommandHandler(daemon)

    asyncio.ensure_future(daemon.main_loop())
    asyncio.ensure_future(cmd_handler.start_unix_server(path))
    asyncio.get_event_loop().run_forever()

def main():
    """Parse argv and act accordingly"""
    parser = argparse.ArgumentParser(
        description="Automatic X screen-locker/screen-saver")
    subparsers = parser.add_subparsers(dest='action')
    parser_start = subparsers.add_parser('start', help='start daemon')
    parser_start.add_argument(
        '-t', '--task', required=True, action='append',
        type=parse_task, dest='tasks',
        help='add a task', metavar='NAME,TIME,COMMAND')

    args = parser.parse_args()

    if args.action == 'start':
        start(args)
    else:
        raise ValueError('Unknown action %r' % args.action)

if __name__ == '__main__':
    main()
