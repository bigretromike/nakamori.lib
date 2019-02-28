# -*- coding: utf-8 -*-
import cProfile
import pstats
import sys
from nakamori_utils import nakamoritools as nt
from nakamori_utils.globalvars import *
# TODO This errors with io.StringIO, so I need to find a python 3 compatible solution
from StringIO import StringIO

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
    start debugger is there is needed one
    also dump argv if spamLog
    :return:
    """
    if plugin_addon.getSetting('spamLog') == "true":
        nt.dump_dictionary(sys.argv, 'sys.argv')

    if plugin_addon.getSetting('remote_debug') == 'true':
        # try pycharm first
        try:
            import pydevd
            pydevd.settrace(host=plugin_addon.getSetting("remote_ip"), stdoutToServer=True, stderrToServer=True,
                            port=5678, suspend=False)
        except:
            xbmc.log('unable to start pycharm debugger, falling back on the web-pdb')
            try:
                import web_pdb
                web_pdb.set_trace()
            except Exception as ex:
                nt.error('Unable to start debugger, disabling', str(ex))
                plugin_addon.setSetting('remote_debug', 'false')
