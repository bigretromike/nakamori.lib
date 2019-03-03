import datetime
from distutils.version import LooseVersion

import xbmc
from nakamori_utils.globalvars import plugin_addon


class Kodi16Proxy:
    def __init__(self):
        plugin_addon.setSetting('kodi18', 'false')

    def user_agent(self):
        """
        This is the useragent that kodi uses when making requests to various services, such as TvDB
        It used to act like Firefox, but in newer versions it has its own
        :return:
        :rtype: basestring
        """
        return 'Mozilla/6.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.5) Gecko/2008092417 Firefox/3.0.3'

    def duration(self, time_s):
        """
        Starting in Kodi 18, the duration tag uses a string timestamp, rather than an integer in seconds.
        This takes the duration in seconds and returns the proper converted version
        :param time_s: time in seconds
        :type time_s: int
        :return:
        :rtype Union[str, int]
        """
        return time_s

    def external_player(self, player_obj):
        """
        In Kodi 18+, xbmc.Player has a isExternalPlayer() method. In earlier versions, the user must specify
        :param player_obj: the player object to check
        :return: true or false
        :rtype: bool
        """
        return plugin_addon.getSetting('external_player') == 'true'


class Kodi17Proxy(Kodi16Proxy):
    def __init__(self):
        Kodi16Proxy.__init__(self)

    def user_agent(self):
        return xbmc.getUserAgent()


class Kodi18Proxy(Kodi17Proxy):
    def __init__(self):
        Kodi17Proxy.__init__(self)
        plugin_addon.setSetting('kodi18', 'true')

    def duration(self, time_s):
        return str(datetime.timedelta(seconds=time_s))

    def external_player(self, player_obj):
        return player_obj.isExternalPlayer()


def get_kodi_version():
    """
    This returns a LooseVersion instance containing the kodi version (16.0, 16.1, 17.0, etc)
    """
    version_string = xbmc.getInfoLabel('System.BuildVersion')
    # Version string is verbose, looking something like "17.6 Krypton Build 123456..."
    # use only the first part
    version_string = version_string.split(' ')[0]
    return LooseVersion(version_string)


kodi_version = get_kodi_version()

if kodi_version < LooseVersion('17.0'):
    kodi_proxy = Kodi16Proxy()
elif kodi_version < LooseVersion('17.9'):
    kodi_proxy = Kodi17Proxy()
else:
    kodi_proxy = Kodi18Proxy()
