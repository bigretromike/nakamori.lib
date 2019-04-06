import sys

import xbmcgui
import xbmcplugin
from nakamori_utils.globalvars import *


class WatchedStatus(object):
    UNWATCHED = 0
    PARTIAL = 1
    WATCHED = 2


class ListItem(xbmcgui.ListItem):
    def __init__(self, label='', label2='', icon_image='', thumbnail_image='', path='', offscreen=False):
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
        :param resume_time: int s
        :return:
        """
        if flag == WatchedStatus.UNWATCHED:
            infolabels['playcount'] = 0
            infolabels['overlay'] = 4
        elif flag == WatchedStatus.WATCHED:
            infolabels['playcount'] = 1
            infolabels['overlay'] = 5
        elif flag == WatchedStatus.PARTIAL and plugin_addon.getSetting('file_resume') == 'true':
            self.setProperty('ResumeTime', str(resume_time))

    def resume(self):
        resume = self.getProperty('ResumeTime')
        if resume is None or resume == '':
            return
        self.setProperty('StartOffset', resume)


class DirectoryListing(object):
    """
    An optimized list to add directory items.
    There may be a speedup by calling `del dir_list`, but Kodi's GC is pretty aggressive
    """
    def __init__(self, content_type='', cache=False):
        self.pending = []
        self.handle = int(sys.argv[1])
        self.cache = cache
        self.success = True
        self.content_type = content_type
        if self.content_type != '':
            xbmcplugin.setContent(self.handle, content_type)
        self.immediate = False

    def set_immediate(self, immediate):
        self.immediate = immediate

    def set_cached(self):
        self.cache = True

    def set_content(self, content_type):
        self.content_type = content_type
        if self.content_type != '':
            xbmcplugin.setContent(self.handle, content_type)

    def extend(self, iterable):
        result_list = []
        for item in iterable:
            result = get_tuple(item)
            if result is not None:
                result_list.append(result)
        return self.pending.extend(result_list)

    def append(self, item, folder=True, total_items=0):
        result = get_tuple(item, folder)
        if result is not None:
            if self.immediate:
                if total_items != 0:
                    return xbmcplugin.addDirectoryItem(self.handle, result[0], result[1], result[2], total_items)
                else:
                    return xbmcplugin.addDirectoryItem(self.handle, result[0], result[1], result[2])
            else:
                self.pending.append(result)
                return True
        else:
            raise RuntimeError('Attempting to Add Not a ListItem to the List')

    def insert(self, index, obj, folder=True):
        if self.immediate:
            raise RuntimeError('Cannot change order of items after adding. Immediate mode is enabled')
        item = get_tuple(obj, folder)
        return self.pending.insert(index, item)

    def __getitem__(self, item):
        if self.immediate:
            raise RuntimeError('Cannot get items after adding. Immediate mode is enabled')
        return self.pending.__getitem__(item)

    def __setitem__(self, key, value):
        if self.immediate:
            raise RuntimeError('Cannot change order of items after adding. Immediate mode is enabled')
        item = get_tuple(value, True)
        return self.pending.__setitem__(key, item)

    def __delitem__(self, key):
        if self.immediate:
            raise RuntimeError('Cannot change order of items after adding. Immediate mode is enabled')
        return self.pending.__delitem__(key)

    def __del__(self):
        if not self.immediate and len(self.pending) > 0:
            xbmcplugin.addDirectoryItems(self.handle, self.pending, self.pending.__len__())
        xbmcplugin.endOfDirectory(self.handle, succeeded=self.success, cacheToDisc=self.cache)


def get_tuple(item, folder=True):
    if is_listitem(item):
        return item.getPath(), item, folder
    if isinstance(item, tuple):
        if len(item) == 2:
            if not is_listitem(item[0]):
                return None
            return item[0].getPath(), item[0], item[1]
        if len(item) == 3:
            if not is_listitem(item[1]):
                return None
            return item[0], item[1], item[2]
    return None


def is_listitem(item):
    return isinstance(item, xbmcgui.ListItem) or isinstance(item, ListItem)
