import sys

import xbmcgui
import xbmcplugin
from nakamori_utils.globalvars import *


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

    def set_thumb(self, thumb):
        xbmcgui.ListItem.setArt(self, {"thumb": thumb})
        xbmcgui.ListItem.setArt(self, {"icon": thumb})
        xbmcgui.ListItem.setArt(self, {"poster": thumb})

    def set_fanart(self, fanart):
        xbmcgui.ListItem.setArt(self, {"fanart": fanart})
        xbmcgui.ListItem.setArt(self, {"clearart": fanart})

    def set_banner(self, banner):
        xbmcgui.ListItem.setArt(self, {"banner": banner})

    def set_watched_flags(self, episode):
        """
        set the needed flags on a listitem for watched or resume icons
        :param self:
        :param episode:
        :return:
        """
        if episode.watched:
            infolabels = {
                "playcount": '1',
                "overlay": '5',
                "watched": 'True'
            }
            self.setInfo("Video", infolabels)
            return
        file = episode.items[0] if len(episode.items) > 0 else None
        if file is not None and file.resume_time > 0 and plugin_addon.getSetting("file_resume") == "true":
            infolabels = {
                "overlay": '7',
                "watched": 'True'
            }
            self.setInfo("Video", infolabels)
            properties = {
                'ResumeTime': str(file.resume_time)
            }
            for prop in properties:
                self.setProperty(prop, properties[prop])


class DirectoryListing(list):
    """An optimized list to add directory items. There may be a speedup by calling `del dir_list`"""
    def __init__(self, content_type):
        list.__init__(self)
        self.pending = []
        self.handle = int(sys.argv[1])
        xbmcplugin.setContent(self.handle, content_type)

    def extend(self, iterable):
        if len(self.pending) > 0:
            xbmcplugin.addDirectoryItems(self.handle, self.pending, self.__len__() + self.pending.__len__())
            self.pending = []
        list.extend(self, iterable)
        xbmcplugin.addDirectoryItems(self.handle, iterable, self.__len__())

    def append(self, item):
        self.pending.append((item.getPath(), item, True))
        list.append(self, item)

    def __del__(self):
        if len(self.pending) > 0:
            xbmcplugin.addDirectoryItems(self.handle, self.pending, self.__len__() + self.pending.__len__())
        xbmcplugin.endOfDirectory(self.handle, cacheToDisc=False)
