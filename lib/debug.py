# -*- coding: utf-8 -*-
import cProfile
import json
import pstats
import sys
from nakamori_utils.globalvars import *
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

has_line_profiler = False
try:
    # noinspection PyUnresolvedReferences
    import line_profiler as line_profiler
    has_line_profiler = True
except ImportError:
    pass


def profile_this(func):
    """
    This can be used to profile any function.
    Usage:
    @profile_this
    def function_to_profile(arg, arg2):
        pass
    """

    def profiled_func(*args, **kwargs):
        """
        a small wrapper
        """
        profile = cProfile.Profile()
        try:
            profile.enable()
            result = func(*args, **kwargs)
            profile.disable()
            return result
        finally:

            stream = StringIO()
            sort_by = u'cumulative'
            ps = pstats.Stats(profile, stream=stream).sort_stats(sort_by)
            ps.print_stats(20)
            xbmc.log(u'Profiled Function: ' + func.__name__ + u'\n' + stream.getvalue(), xbmc.LOGWARNING)
    return profiled_func


def debug_init():
    """
    start debugger if it's enabled
    also dump argv if spamLog
    :return:
    """
    if plugin_addon.getSetting('spamLog') == 'true':
        xbmc.log('Nakamori: sys.argv = ' + json.dumps(sys.argv))

    if plugin_addon.getSetting('remote_debug') == 'true':
        # try pycharm first
        try:
            import pydevd
            # try to connect multiple times...in case we forgot to start it
            # TODO Show a message to the user that we are waiting on the debugger
            connected = False
            tries = 0
            while not connected and tries < 60:
                try:
                    pydevd.settrace(host=plugin_addon.getSetting('remote_ip'), stdoutToServer=True, stderrToServer=True,
                                    port=5678, suspend=False)
                    connected = True
                except:
                    tries += 1
                    xbmc.sleep(1000)
        except ImportError:
            xbmc.log('unable to start pycharm debugger, falling back on the web-pdb', xbmc.LOGINFO)
            try:
                import web_pdb
                web_pdb.set_trace()
            except Exception as ex:
                xbmc.log('Unable to start debugger, disabling' + str(ex), xbmc.LOGERROR)
                plugin_addon.setSetting('remote_debug', 'false')
