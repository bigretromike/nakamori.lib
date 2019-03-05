# -*- coding: utf-8 -*-
import inspect
import os
import sys
import time
import traceback
from collections import defaultdict, Counter

import xbmcgui
from nakamori_utils.globalvars import plugin_addon, plugin_version
from proxy.python_version_proxy import python_proxy as pp

try:
    import xbmc
    addon_path = 'special://home/addons'
    addon_path = xbmc.translatePath(addon_path).replace('\\', '/')
except (ImportError, NameError):
    addon_path = os.path.expanduser('~/Documents/GitHub/Nakamori').replace('\\', '/')
    import kodi_dummy as xbmc


# The plan is:
# gather all errors/exceptions, regardless of whether they are painless
# sort and group them
# BLOCKING errors will immediately return and break
# otherwise, log only HIGH and above priority errors
# log the count and place(s) of occurrence
# Show a dialog OK message that there was an error if it was HIGHEST or greater
# Show a notification if it was HIGH
# log counts of normal errors if they happen a lot, like more than 5 times
# We will normally not even log LOW priority errors,
# but we may enable it (and logging all errors) in the settings
# Errors will start being collected at the start of the plugin cycle, and will only show messages when done
# Especially suppress errors during playback unless it is BLOCKING

# I WANT LINQ!!!!!!
# a dictionary of ErrorPriority to list of errors
__exceptions = defaultdict(list)


class ErrorPriority(object):
    """
    | **BLOCKING**: Something that prevents continuing.
    | **HIGHEST**: An entire item failed to parse or something. May impact the user greatly. We show a dialog.
    | **HIGH**: Some data failed to parse, or a command couldn't succeed. May impact the user. Notification.
    | **NORMAL**: couldn't keep up scrobbling or something that shouldn't happen often,
    but isn't really a problem most of the time. Log it if there's more than 5.
    | **LOW**: Basically negligible. They could happen all day, and the user wouldn't even care.
    An example of LOW might be needing to internally retry selecting the next unwatched episode, as it wasn't ready yet.
    We don't even log them unless spam log is on.
    """
    LOW, NORMAL, HIGH, HIGHEST, BLOCKING = range(0, 5)


class NakamoriError(object):
    """
    The error object has the point of carrying the traceback and exception info.
    It may also carry some extra data or less data, if the error is raised by us with a specific message
    """
    def __init__(self):
        # the message, either from the exception or us
        self.exc_message = 'Something Happened :('
        # the Exception type, in str form
        self.exc_type = Exception.__name__
        # (str, int) that carries the file and line number, relative to the addon directory
        self.exc_trace = ('./error_handler.py', 61)
        # this is for spam log or BLOCKING errors. It contains the full trace info, in list form at 1 line each
        self.exc_full_trace = []

    def __init__(self, message, ex, trace):
        self.exc_message = message
        if not isinstance(ex, str):
            ex = ex.__name__
        self.exc_type = ex
        self.exc_trace = trace
        self.exc_full_trace = []

    def __eq__(self, o):
        if not isinstance(o, NakamoriError):
            return False
        return self.exc_type == o.exc_type and self.exc_message == o.exc_message and self.exc_trace == o.exc_trace

    def __hash__(self):
        return hash((self.exc_type, self.exc_message, self.exc_trace))

    def __lt__(self, other):
        if not isinstance(other, NakamoriError):
            return True
        return (self.exc_type, self.exc_message, self.exc_trace) < (other.exc_type, other.exc_message, other.exc_trace)


def try_function(error_priority, message=''):
    def try_inner1(func):
        def try_inner2(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as ex:
                exception(error_priority, message)
                if error_priority == ErrorPriority.BLOCKING:

                    show_messages()
                    # sys.exit is called if BLOCKING errors exist in the above
                return None
        return try_inner2
    return try_inner1


def kodi_log(text):
    xbmc.log(text, xbmc.LOGNOTICE)


def kodi_error(text):
    xbmc.log(text, xbmc.LOGERROR)


# noinspection PyProtectedMember
def __get_caller_prefix():
    # this gets the frame from 2 methods ago.
    # It is 2 because method_that_errors() -> meh.error() -> __get_caller_prefix()
    # method_that_errors() is 2 frames above this
    filepath, line_number, clsname, lines, index = inspect.getframeinfo(sys._getframe(2))
    filename = 'Nakamori|' + os.path.split(filepath)[1]
    if clsname == '<module>':
        prefix = filename + '#L' + str(line_number) + ' -> '
    else:
        prefix = filename + '::' + clsname + '#L' + str(line_number) + ' -> '
    return prefix


def __get_basic_prefix():
    return 'Nakamori|Logger -> '


# see this for handling the re-raises below
# https://stackoverflow.com/questions/6598053/python-global-exception-handling
def try_2_do(error_priority, message, func, *args, **kwargs):
    """
    Try a function, then catch it cleanly
    :param func: the function to attempt
    :param error_priority: the priority of the error
    :type error_priority: ErrorPriority
    :param message: a custom message to show
    :type message: str
    :return:
    """
    try:
        func(*args, **kwargs)
        return True
    except Exception as ex:
        exception(error_priority, message)
        if error_priority == ErrorPriority.BLOCKING:
            raise ex
        return True


def try_2_get(error_priority, message, func, *args, **kwargs):
    """
    Try a function, then catch it cleanly
    :param func: the function to attempt
    :param error_priority: the priority of the error
    :type error_priority: ErrorPriority
    :param message: a custom message to show
    :type message: str
    :return:
    """
    try:
        return func(*args, **kwargs)
    except Exception as ex:
        exception(error_priority, message)
        if error_priority == ErrorPriority.BLOCKING:
            raise ex
        return None


def log(text):
    kodi_log(__get_caller_prefix() + text)


def error(text):
    """
    Print a message on the ERROR stream, with a simple traceback.
    This is for readable messages that are expected, such as connection errors.
    If you want to log a full traceback use exception()
    :param text:
    :return:
    """
    kodi_error(__get_caller_prefix() + text)


def exception(priority, message=''):
    exc_type, exc_obj, exc_tb = sys.exc_info()
    exception_internal(exc_type, exc_obj, exc_tb, priority, message)


def exception_internal(exc_type, exc_obj, exc_tb, priority, message=''):
    """
    Most of the data needed can be called from sys. The priority determines how the system will handle or display the error.
    :param priority: The priority of the Error
    :type priority: ErrorPriority
    :param message: a custom message to give the user. If left blank, it will use the exception's
    :return:
    """
    # apparently sometimes they give us exc_type as a str instead of a type
    if not isinstance(exc_type, str):
        exc_type = exc_type.__name__
    # for now we'll keeping the logging and stuff. I'll do the grouping and aggregation later
    if exc_type is not None and exc_obj is not None and exc_tb is not None:
        place = exc_tb.tb_frame.f_code.co_filename.replace('\\', '/').replace(addon_path, '.')
        if message == '':
            message = exc_obj.message
        ex = NakamoriError(message, exc_type, (place, exc_tb.tb_lineno))
        if priority == ErrorPriority.BLOCKING or plugin_addon.setSetting('spamLog') == 'true':
            for line in traceback.format_exc().replace('\r', '\n').split('\n'):
                # skip empty lines
                if len(line) == 0:
                    continue
                # skip the try_function wrapper
                if ' in try_inner2' in line or 'return func(*args, **kwargs)' in line:
                    continue

                tr = line.replace('\\', '/').replace(addon_path, '.')
                ex.exc_full_trace.append(tr)
        __exceptions[priority].append(ex)


def show_messages():
    # finalize the defaultdict so that it won't create new keys anymore
    __exceptions.default_factory = None
    if len(__exceptions) == 0:
        return
    if ErrorPriority.BLOCKING in __exceptions:
        exes = __exceptions[ErrorPriority.BLOCKING]
        exes = Counter(exes).items()
        exes = sorted(exes)
        print_exceptions(exes)
        show_dialog_for_exception(exes[0])
        sys.exit()
    if ErrorPriority.HIGHEST in __exceptions:
        exes = __exceptions[ErrorPriority.HIGHEST]
        exes = Counter(exes).items()
        exes = sorted(exes)
        print_exceptions(exes)
        show_dialog_for_exception(exes[0])
    if ErrorPriority.HIGH in __exceptions:
        exes = __exceptions[ErrorPriority.HIGH]
        exes = Counter(exes).items()
        exes = sorted(exes)
        print_exceptions(exes)
        show_notification_for_exception(exes[0])
    if ErrorPriority.NORMAL in __exceptions:
        exes = __exceptions[ErrorPriority.NORMAL]
        exes = Counter(exes).items()
        exes = sorted(exes)
        # log all if we are spamming
        if plugin_addon.getSetting('spamLog') != 'true':
            exes = next([x for x in exes if x[1] > 5], [])
        print_exceptions(exes)
    if plugin_addon.getSetting('spamLog') == 'true' and ErrorPriority.LOW in __exceptions:
        exes = __exceptions[ErrorPriority.LOW]
        exes = Counter(exes).items()
        exes = sorted(exes)
        print_exceptions(exes)


def print_exceptions(exes):
    if exes is None or len(exes) == 0:
        return

    plural = True if len(exes) > 1 else False
    pluralized_msg = 'were errors' if plural else 'was an error'
    msg = 'There ' + pluralized_msg + ' while executing Nakamori.'
    error(msg)

    msg = 'Nakamori Version ' + str(plugin_version)
    error(msg)

    url = sys.argv[0]
    if len(sys.argv) > 2 and sys.argv[2] != '':
        url += sys.argv[2]
    msg = 'The url accessed was ' + pp.unquote(url)
    error(msg)

    for ex in exes:
        key, value = ex  # type: NakamoriError, int
        msg = key.exc_message + ' -- Exception: ' + key.exc_type + ' at ' + key.exc_trace[0] + '#L' + \
            str(key.exc_trace[1])
        error(msg)
        if len(key.exc_full_trace) > 0:
            for line in key.exc_full_trace:
                error(line)

        if value > 1:
            msg = 'This error occurred ' + str(value) + ' times.'
            error(msg)


def show_dialog_for_exception(ex):
    """
    Show an OK dialog to say that errors occurred
    :param ex: a tuple of the error and the number of times it occurred
    :type ex: (NakamoriError, int)
    :return:
    """
    msg = ex[0].exc_message + '\n  at ' + ex[0].exc_trace[0] + '#L' + str(ex[0].exc_trace[1]) + '\nThis occurred ' + \
        str(ex[1]) + ' times.'
    dialog = xbmcgui.Dialog().ok('Nakamori: An Error Occurred', msg)


def show_notification_for_exception(ex):
    """
    Show a notification to say that errors occurred
    :param ex: a tuple of the error and the number of times it occurred
    :type ex: (NakamoriError, int)
    :return:
    """
    msg = ex[0].exc_message + '\nThis occurred ' + str(ex[1]) + pp.encode(u'\u00D7 ') + ' times.'
    xbmc.executebuiltin('XBMC.Notification(Nakamori: An Error Occurred, ' + msg + ', 2000, ' +
                        plugin_addon.getAddonInfo('icon') + ')')


def get_some_text():
    return __get_caller_prefix() + 'this is some text'


if __name__ == '__main__':
    log('This is a test')

    then = int(time.time() * 1000)
    log('We\'re starting now!')
    for i in range(0, 100):
        if i % 10 == 0:
            log('We are ' + str(i/10) + '0% done!')
        test_string = get_some_text()
    log('We\'re done now!')
    now = int(time.time() * 1000)
    log('It took ' + str(now - then) + 'ms to process 100 error messages')

    try:
        k = int('k')
    except:
        error('THIS IS AN ERROR!')
        exception(ErrorPriority.HIGHEST)

# Nakamori|error_handler.py#L121 -> This is a test
# Nakamori|error_handler.py#L124 -> We're starting now!
# Nakamori|error_handler.py#L127 -> We are 00% done!
# Nakamori|error_handler.py#L127 -> We are 10% done!
# Nakamori|error_handler.py#L127 -> We are 20% done!
# Nakamori|error_handler.py#L127 -> We are 30% done!
# Nakamori|error_handler.py#L127 -> We are 40% done!
# Nakamori|error_handler.py#L127 -> We are 50% done!
# Nakamori|error_handler.py#L127 -> We are 60% done!
# Nakamori|error_handler.py#L127 -> We are 70% done!
# Nakamori|error_handler.py#L127 -> We are 80% done!
# Nakamori|error_handler.py#L127 -> We are 90% done!
# Nakamori|error_handler.py#L129 -> We're done now!
# Nakamori|error_handler.py#L131 -> It took 14ms to process 100 error messages
# Nakamori|error_handler.py#L136 -> THIS IS AN ERROR!
# Nakamori|Logger -> Exception: ValueError at error_handler.py#L134
# Nakamori|Logger -> Traceback (most recent call last):
# Nakamori|Logger ->   File "./script.module.nakamori-lib/lib/error_handler.py", line 134, in <module>
# Nakamori|Logger ->     k = int('k')
# Nakamori|Logger -> ValueError: invalid literal for int() with base 10: 'k'
