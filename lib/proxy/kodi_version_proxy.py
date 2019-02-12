from distutils.version import LooseVersion

import xbmc


class Kodi16Proxy:
    def __init__(self):
        pass

    def user_agent(self):
        return 'Mozilla/6.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.5) Gecko/2008092417 Firefox/3.0.3'


class Kodi17Proxy(Kodi16Proxy):
    def __init__(self):
        Kodi16Proxy.__init__(self)

    def user_agent(self):
        return xbmc.getUserAgent()


class Kodi18Proxy(Kodi17Proxy):
    def __init__(self):
        Kodi17Proxy.__init__(self)


def get_kodi_version():
    """
    This returns a LooseVersion instance containing the kodi version (16.0, 16.1, 17.0, etc)
    """
    version_string = xbmc.getInfoLabel('System.BuildVersion')
    version_string = version_string.split(' ')[0]
    return LooseVersion(version_string)


kodi_version = get_kodi_version()

if kodi_version < LooseVersion('17.0'):
    instance = Kodi16Proxy()
elif kodi_version < LooseVersion('18.0'):
    instance = Kodi17Proxy()
elif kodi_version >= LooseVersion('18.0'):
    instance = Kodi18Proxy()
