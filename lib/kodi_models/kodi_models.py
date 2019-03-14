import sys

import xbmcgui
import xbmcplugin
from nakamori_utils.globalvars import *


class WatchedStatus(object):
    UNWATCHED = 0
    PARTIAL = 1
    WATCHED = 2


class ListItem(xbmcgui.ListItem):
    def __init__(self):
        xbmcgui.ListItem.__init__(self)

    def __init__(self, label, label2='', icon_image='', thumbnail_image='', path='', offscreen=False):
        xbmcgui.ListItem.__init__(self, label, label2, icon_image, thumbnail_image, path, offscreen)

    def set_art(self, dir_obj):
        """
        Set Art from a Directory object
        :param dir_obj:
        :type dir_obj: Directory
        :return:
        """
        if dir_obj.fanart is not None:
            self.set_fanart(dir_obj.fanart)
        if dir_obj.poster is not None:
            self.set_thumb(dir_obj.poster)
        if dir_obj.banner is not None:
            self.set_banner(dir_obj.banner)

    def set_internal_image(self, image_name):
        icon = os.path.join(plugin_img_path, 'icons', image_name)
        fanart = os.path.join(plugin_img_path, 'backgrounds', image_name)
        self.set_thumb(icon)
        self.set_fanart(fanart)

    def set_thumb(self, thumb):
        xbmcgui.ListItem.setArt(self, {'thumb': thumb})
        xbmcgui.ListItem.setArt(self, {'icon': thumb})
        xbmcgui.ListItem.setArt(self, {'poster': thumb})

    def set_fanart(self, fanart):
        xbmcgui.ListItem.setArt(self, {'fanart': fanart})
        xbmcgui.ListItem.setArt(self, {'clearart': fanart})

    def set_banner(self, banner):
        xbmcgui.ListItem.setArt(self, {'banner': banner})

    def set_watched_flags(self, infolabels, flag, resume_time=0):
        """
        set the needed flags on a listitem for watched or resume icons
        :param self:
        :param infolabels
        :param flag:
        :type flag: WatchedStatus
        :return:
        """
        if flag == WatchedStatus.UNWATCHED:
            infolabels['playcount'] = 0
            infolabels['overlay'] = 4
        elif flag == WatchedStatus.WATCHED:
            infolabels['playcount'] = 1
            infolabels['overlay'] = 5
        elif flag == WatchedStatus.PARTIAL and plugin_addon.getSetting('file_resume') == 'true':
            # infolabels['playcount'] = 0
            # infolabels['overlay'] = 7
            self.setProperty('ResumeTime', str(resume_time))

    def set_resume(self):
        resume = self.getProperty('ResumeTime')
        if resume is None or resume == '':
            return
        self.setProperty('StartOffset', resume)


class DirectoryListing(list):
    """
    An optimized list to add directory items.
    There may be a speedup by calling `del dir_list`, but Kodi's GC is pretty aggressive
    """
    def __init__(self, content_type, cache=False):
        list.__init__(self)
        self.pending = []
        self.handle = int(sys.argv[1])
        self.cache = cache
        xbmcplugin.setContent(self.handle, content_type)

    def extend(self, iterable):
        # first handle pending items
        if len(self.pending) > 0:
            xbmcplugin.addDirectoryItems(self.handle, self.pending, self.__len__() + self.pending.__len__())
            self.pending = []
        # we pass a list of listitems, (listitem, bool). or (str, listitem, bool)
        result_list = []
        for item in iterable:
            result = get_tuple(item)
            if result is not None:
                result_list.append(result)
        list.extend(self, result_list)
        xbmcplugin.addDirectoryItems(self.handle, result_list, self.__len__())

    def append(self, item, folder=True):
        result = get_tuple(item, folder)
        if result is not None:
            self.pending.append(result)
            list.append(self, result)

    def __del__(self):
        if len(self.pending) > 0:
            xbmcplugin.addDirectoryItems(self.handle, self.pending, self.__len__() + self.pending.__len__())
        xbmcplugin.endOfDirectory(self.handle, cacheToDisc=self.cache)


def get_tuple(item, folder=True):
    if isinstance(item, ListItem):
        return item.getPath(), item, folder
    if isinstance(item, tuple):
        if len(item) == 2:
            return item[0].getPath(), item[0], item[1]
        if len(item) == 3:
            return item[0], item[1], item[2]
    return None
