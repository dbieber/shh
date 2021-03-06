from __future__ import absolute_import
from __future__ import print_function

from datetime import datetime
from random import choice
from utils import sayable_datetime

from settings import settings

import os
import re
import sys

commands = []

def command(pattern, **params):
    def command_decorator(func):
        def newfunc(*args, **kwargs):
            value = func(*args, **kwargs)
            return value
        newfunc.func_name = func.func_name

        regex_str = pattern.replace('{}', '(.*)')
        regex = re.compile(regex_str)
        name = params.get('name', func.func_name)

        command = Command(
            name=name,
            func=newfunc,
            regex=regex,
            params=params,
        )
        commands.append(command)

        return newfunc
    return command_decorator

class Command(object):

    def __init__(self, name, func, regex, params=None):
        self.name = name
        self.func = func
        self.regex = regex
        self.params = params

    def execute_if_match(self, cmd_str,
                         app_manager=None,
                         scheduler=None,
                         mailer=None,
                         state=None):
        match = self.regex.match(cmd_str)
        if match:
            args = match.groups()
            kwargs = {}

            if self.params.get('require_app_manager'):
                kwargs['app_manager'] = app_manager
            if self.params.get('require_scheduler'):
                kwargs['scheduler'] = scheduler
            if self.params.get('require_mailer'):
                kwargs['mailer'] = mailer
            if self.params.get('require_state'):
                kwargs['state'] = state

            self.func(*args, **kwargs)
            return True
        return False

@command('alarm')
def alarm():
    query = choice([
        'tell her about it YouTube',
        'piano man YouTube',
        'rhapsody in blue YouTube',
    ])
    feel_lucky(query)

@command('lucky {}')
def feel_lucky(query):
    query = query.replace(" ", "+")
    cmd = 'open "http://www.google.com/search?q={}&btnI"'.format(query)
    shell(cmd)

@command('time')
def time():
    shell('say `date "+%A, %B%e %l:%M%p"` &')

@command('status')
def status():
    say('ok')

@command('say {}')
def say(text):
    dt = datetime.now().strftime('%k:%M:%S')
    with open('tmp-say', 'w') as tmp:
        print('[{}] Writing "{}" to tmp-say'.format(dt, text))
        tmp.write(text)
    cmd = 'cat tmp-say | say &'
    shell(cmd)

@command('shell {}')
def shell(cmd):
    dt = datetime.now().strftime('%k:%M:%S')
    print("[{}] Executing command: '{}'".format(dt, cmd))
    os.system(cmd)

@command('at {}:{}', require_scheduler=True)
def schedule(at, what, scheduler):
    scheduler.schedule(at, what)

@command('help')
def help():
    set_of_names = sorted(set(cmd.name for cmd in commands))
    list_str = ', '.join(set_of_names)
    help_message = """Welcome to the shh-shell!

The purpose of this shell is to let you use your computer without having to
exert any effort or do anything that might wake you up, even a little. That
means no monitors and no mouse. The shell wants to replace the pad of paper
you keep by your bedside.

All keystrokes are timestamped and logged.
Type :<command> to execute a command.
Type :help to pull up this help message.

Available commands are {}.
"""
    print(help_message.format(list_str))

@command('list commands')
def list_commands():
    set_of_names = sorted(set(cmd.name for cmd in commands))
    list_str = ', '.join(set_of_names)
    say(list_str)

@command('list jobs', require_scheduler=True)
def list_jobs(scheduler):
    jobs = scheduler.get_jobs()
    job_list_str = ', '.join('{}, {}'.format(
        sayable_datetime(at), what
    ) for at, what in jobs)
    say(job_list_str)

@command('todo {}', require_scheduler=True, require_state=True)
def save_todo(task, scheduler, state):
    todo_list = state.get('todo_list', [])
    # TODO(Bieber): Store and use other information about TODOs like deadline
    todo_list.append(task)
    state.set('todo_list', todo_list)

    task = 'email_todo_summary'
    if not scheduler.already_scheduled(task):
        schedule('10pm', task, scheduler)

@command('list todos', require_state=True)
def list_todos(state):
    todo_list = state.get('todo_list', [])
    say(', '.join(todo_list))

@command('email_todo_summary', require_mailer=True, require_state=True)
def email_todo_summary(mailer, state):
    todo_list = state.get('todo_list', [])
    todo_list_str = '\n'.join('-  {}'.format(item) for item in todo_list)
    contents = """Did you accomplish what you set out to do?

        {}""".format(todo_list_str)
    subject = 'TODO Summary for {}'.format(datetime.now().strftime("%D"))
    mailer.mail(to=settings.secure.DEFAULT_EMAIL_RECIPIENT,
                subject=subject,
                text=contents)

@command('clear todos', require_state=True)
def clear_todos(state):
    state.delete('todo_list')

@command('reading list {}', require_state=True)
def reading_list(state):
    books = state.get('reading_list', [])
    say(' ,'.join(books))

@command('reading list {}', require_state=True)
def add_to_reading_list(book, state):
    books = state.get('reading_list', [])
    books.append(book)
    state.set(reading_list, books)

@command('login', require_mailer=True)
@command('mail login', require_mailer=True)
@command('email login', require_mailer=True)
def email_login_default(mailer):
    email_login(settings.secure.DEFAULT_EMAIL, mailer)

@command('login {}', require_mailer=True)
@command('mail login {}', require_mailer=True)
@command('email login {}', require_mailer=True)
def email_login(user, mailer):
    mailer.login(user)

@command('logout', require_mailer=True)
@command('mail logout', require_mailer=True)
@command('email logout', require_mailer=True)
def email_logout_default(mailer):
    mailer.logout()

@command('send email {}', require_mailer=True)
@command('email {}', require_mailer=True)
def email(contents, mailer):
    mailer.mail(to=settings.secure.DEFAULT_EMAIL_RECIPIENT,
                subject='shh {}'.format(datetime.now().strftime("%D %H:%M")),
                text=contents)

@command('check mail', require_mailer=True)
@command('check email', require_mailer=True)
def check_email(mailer):
    subjects = [msg.subject() for msg in mailer.check_mail()]
    say(', '.join(subjects))

@command('read mail {}', require_mailer=True)
@command('read email {}', require_mailer=True)
def read_email(subject_bit, mailer):
    for msg in mailer.check_mail():
        # TODO(Bieber): Use fuzzy select
        if subject_bit.strip().lower() in msg.subject().lower():
            # TODO(Bieber): Say with timeout
            say(msg.text()[:100])
            return
    print('Not found')

@command('num messages', require_mailer=True)
def num_messages(mailer):
    count = len(mailer.check_mail())
    say('You have {} unread messages'.format(count))

@command('text {} TO {}')
def send_text(message_text, phone_number):
    script = """
    tell application "Messages"
      send "{}" to buddy "{}" of service {}
    end tell
    """.format(
        message_text,
        phone_number,
        settings.secure.DEFAULT_SERVICE,
    )
    shell("echo '{}' | osascript".format(script))

@command('reload')
def reload_this():
    reload_module(__name__)

@command('reload {}')
def reload_module(module_name):
    if module_name in sys.modules:
        module = sys.modules[module_name]
        reload(module)
    else:
        say('{} not found'.format(module_name))

@command('goal {}', require_state=True)
def set_goal(goal, state):
    goals = state.get('goals', [])
    goals.append(goal)
    state.set('goals', goals)

@command('list goals', require_state=True)
def list_goals(state):
    goals = state.get('goals', [])
    say(', '.join(goals))

@command('clear', require_gui=True)
def clear(gui=None):
    pass

@command('list {}', require_app_manager=True, require_state=True)
def list_app(list_name, app_manager, state):
    # TODO(Bieber): Use fuzzy select
    list_id = "list:{}".format(list_name)

    def handle_line(line):
        line = line.strip()
        if not line:
            return

        say(line)
        items = state.get(list_id, [])
        items.append(line)
        state.set(list_id, items)

    app_manager.start_app(handle_line=handle_line)

@command('readlist {}', require_state=True)
def readlist(list_name, state):
    list_id = "list:{}".format(list_name)
    items = state.get(list_id, [])
    say(', '.join(items))

@command('emaillist {}', require_mailer=True, require_state=True)
def emaillist(list_name, mailer, state):
    list_id = "list:{}".format(list_name)
    items = state.get(list_id, [])

    list_str = '\n'.join('-  {}'.format(item) for item in items)
    contents = """{}

        {}""".format(list_name, list_str)
    subject = '{} at {}'.format(list_name, datetime.now().strftime("%D"))
    mailer.mail(to=settings.secure.DEFAULT_EMAIL_RECIPIENT,
                subject=subject,
                text=contents)

@command('listlists', require_state=True)
def listlists(state):
    prefix = 'shh:list:'
    lists = filter(lambda k: k[0:len(prefix)] == prefix, state.redis.keys())
    list_names = map(lambda l: l[len(prefix):], lists)
    say(', '.join(list_names))

@command('bc {}')
def calculate(expression):
    dt = datetime.now().strftime('%k:%M:%S')
    with open('tmp-bc', 'w') as tmp:
        print('[{}] Writing "{}" to tmp-bc'.format(dt, expression))
        tmp.write(expression)
        tmp.write('\n')
    cmd = 'cat tmp-bc | bc | say &'
    shell(cmd)

@command('bc', require_app_manager=True)
def calculator(app_manager):
    def handle_line(line):
        calculate(line)
    app_manager.start_app(handle_line=handle_line)

@command('solfege', require_app_manager=True)
def launch_solfege(app_manager):
    def handle_line(line):
        # TODO(Bieber): Write keyboard shortcuts for solfege
        pass
    def handle_start():
        sys.path.append('/Users/dbieber/code/pitch')
        import solfege_interface
        solfege_interface.start_app()

    app_manager.start_app(
        handle_line=handle_line,
        handle_start=handle_start,
    )

@command('recorder', require_app_manager=True)
def launch_recorder(app_manager):
    # TODO(Bieber): Implement recorder
    pass

@command('piano', require_app_manager=True)
def launch_piano(app_manager):
    # TODO(Bieber): Implement piano
    pass
