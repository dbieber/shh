from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger

import shh_commands
from mailer import Mailer
from shh_state import ShhState

import logging
import parsedatetime

logging.basicConfig()


executor_singleton = None
def execute_command(cmd):
    global executor_singleton
    if executor_singleton is None:
        executor_singleton = CommandExecutor()
    executor_singleton.execute(cmd)

def setup_executor(app_manager=None):
    global executor_singleton
    executor_singleton = CommandExecutor(app_manager=app_manager)

class CommandExecutor(object):

    def __init__(self, app_manager=None):
        self.app_manager = app_manager
        self.mailer = Mailer()
        self.scheduler = CommandScheduler()
        self.state = ShhState()

    def execute(self, cmd_str):
        for cmd in shh_commands.commands:
            executed = cmd.execute_if_match(cmd_str,
                app_manager=self.app_manager,
                scheduler=self.scheduler,
                mailer=self.mailer,
                state=self.state
            )
            if executed:
                break

class CommandScheduler(object):

    def __init__(self, start=True):
        executors = {
            'default': ThreadPoolExecutor(20),
            'processpool': ProcessPoolExecutor(5)
        }

        self.scheduler = BackgroundScheduler(executors=executors)
        self.scheduler.add_jobstore('redis',
            jobs_key='shh:jobs',
            run_times_key='shh:run_times'
        )

        if start:
            self.scheduler.start()

        self.datetime_parser = parsedatetime.Calendar()

    def parse(self, at):
        return self.datetime_parser.parseDT(at)[0]

    def already_scheduled(self, what):
        # TODO(Bieber): Improve efficiency with a dict
        for scheduled_at, scheduled_what in self.get_jobs():
            if what == scheduled_what:
                return True
        return False

    def schedule(self, at, what):
        dt = self.parse(at)
        trigger = DateTrigger(dt)
        self.scheduler.add_job(execute_command,
            trigger=trigger,
            args=[what.strip()],
        )

    def get_jobs(self):
        jobs = self.scheduler.get_jobs()
        return [(job.next_run_time, job.args[0]) for job in jobs]
