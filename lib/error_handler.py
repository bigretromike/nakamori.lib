# -*- coding: utf-8 -*-
import inspect
import os
import sys
import time
import traceback

try:
    import xbmc
    addon_path = 'special://home/addons'
    addon_path = xbmc.translatePath(addon_path)
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


class ErrorPriority(object):
    """
    | **BLOCKING**: Something that prevents continuing.
    | **HIGHEST**: An entire item failed to parse or something. May impact the user greatly.
    | **HIGH**: Some data failed to parse, or a command couldn't succeed. May impact the user, but tolerable.
    | **NORMAL**: couldn't keep up scrobbling or something that shouldn't happen often,
    but isn't really a problem most of the time.
    | **LOW**: Basically negligible. They could happen all day, and the user wouldn't even care.
    An example of LOW might be needing to internally retry selecting the next unwatched episode, as it wasn't ready yet.
    """
    LOW, NORMAL, HIGH, HIGHEST, BLOCKING = range(0, 5)


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


def exception():
    exc_type, exc_obj, exc_tb = sys.exc_info()
    if exc_type is not None and exc_obj is not None and exc_tb is not None:
        kodi_error(__get_basic_prefix() + 'Exception: ' + exc_type.__name__ + ' at ' +
              os.path.split(exc_tb.tb_frame.f_code.co_filename)[1] + '#L' + str(exc_tb.tb_lineno))
        for line in traceback.format_exc().replace('\r', '\n').split('\n'):
            if len(line) == 0:
                continue
            kodi_error(__get_basic_prefix() + line.replace(addon_path, '.'))


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
        exception()

# Nakamori|Logger -> This is a test
# Nakamori|Logger -> We're starting now!
# Nakamori|Logger -> We are 00% done!
# Nakamori|Logger -> We are 10% done!
# Nakamori|Logger -> We are 20% done!
# Nakamori|Logger -> We are 30% done!
# Nakamori|Logger -> We are 40% done!
# Nakamori|Logger -> We are 50% done!
# Nakamori|Logger -> We are 60% done!
# Nakamori|Logger -> We are 70% done!
# Nakamori|Logger -> We are 80% done!
# Nakamori|Logger -> We are 90% done!
# Nakamori|Logger -> We're done now!
# Nakamori|Logger -> It took 16ms to process 100 error messages
# Nakamori|ErrorHandler.py#L117 -> THIS IS AN ERROR!
# Nakamori|Logger -> Exception: ValueError at ErrorHandler.py#L115
# Nakamori|Logger -> Traceback (most recent call last):
# Nakamori|Logger ->   File "./script.module.nakamori-lib/lib/ErrorHandler.py", line 115, in <module>
# Nakamori|Logger ->     k = int('k')
# Nakamori|Logger -> ValueError: invalid literal for int() with base 10: 'k'
