#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import time
from hashlib import md5

from abc import abstractmethod

import class_dump
import error_handler as eh
import nakamori_utils.model_utils
import xbmcplugin
from nakamori_utils.kodi_utils import Sorting

from kodi_models import ListItem, WatchedStatus
from nakamori_utils.globalvars import *
from nakamori_utils import kodi_utils, shoko_utils, script_utils, plugin_utils
from nakamori_utils import model_utils

from proxy.kodi_version_proxy import kodi_proxy
from proxy.python_version_proxy import python_proxy as pyproxy

localize = plugin_addon.getLocalizedString


# noinspection Duplicates,PyUnusedFunction
class Directory(object):
    """
    A directory object, the base for Groups, Series, Episodes, etc
    """
    def __init__(self, json_node, get_children=False):
        """
        Create a directory object from a json node, containing only what is needed to form a ListItem.
        :param json_node: the json response from things like api/serie
        :type json_node: Union[list,dict]
        """
        self.is_kodi_folder = True
        self.name = None
        self.items = []
        self.fanart = ''
        self.poster = ''
        self.banner = ''
        self.icon = ''
        self.size = -1
        self.get_children = get_children
        self.sort_index = 1
        self.sizes = None
        if isinstance(json_node, int) or pyproxy.is_unicode_or_string(json_node):
            self.id = json_node
            return

        self.id = json_node.get('id', 0)
        self.name = model_utils.get_title(json_node)
        self.size = int(json_node.get('size', '0'))

        self.make_bold = False

        self.process_art(json_node)

    def __str__(self):
        # class name
        result = '<%s> ' % self.__class__.__name__
        # if it's not a full object, use the ID
        if self.name != '':
            result += self.name
        else:
            result += '[%s]' % self.id

        if self.items is not None and len(self.items) > 0:
            if len(self.items) == 1:
                result += ' - %s item' % len(self.items)
            else:
                result += ' - %s items' % len(self.items)
        else:
            result += ' - 0 items'

        return result

    def __repr__(self):
        return class_dump.dump_to_text(self)

    def apply_image_override(self, image):
        self.fanart = os.path.join(plugin_img_path, 'backgrounds', image)
        self.poster = os.path.join(plugin_img_path, 'icons', image)
        self.banner = os.path.join(plugin_img_path, 'banners', image)

    @abstractmethod
    def get_api_url(self):
        """
        Gets the URL for retrieving data on this object from the API
        :return:
        :rtype: str
        """
        pass

    @abstractmethod
    def get_plugin_url(self):
        pass

    @abstractmethod
    def url_prefix(self):
        pass

    def base_url(self):
        return server + '/api/' + self.url_prefix()

    def get_full_object(self, force_cache=False, cache_time=0):
        url = self.get_api_url()
        json_body = pyproxy.get_json(url, force_cache=force_cache, cache_time=cache_time)
        if json_body is None:
            return None
        json_node = json.loads(json_body)
        return json_node

    def process_art(self, json_node):
        thumb = ''
        fanart = ''
        banner = ''
        icon = ''
        try:
            if len(json_node['art']['thumb']) > 0:
                thumb = json_node['art']['thumb'][0]['url']
                if thumb is not None and ':' not in thumb:
                    thumb = server + thumb

            if len(json_node['art']['fanart']) > 0:
                fanart = json_node['art']['fanart'][0]['url']
                if fanart is not None and ':' not in fanart:
                    fanart = server + fanart

            if len(json_node['art']['banner']) > 0:
                banner = json_node['art']['banner'][0]['url']
                if banner is not None and ':' not in banner:
                    banner = server + banner

            # TODO need to play with this a little more
            if kodi_utils.get_cond_visibility('System.HasAddon(resource.images.studios.white)') == 1:
                if hasattr(self, 'studio'):
                    icon = 'resource://resource.images.studios.white/{studio}.png'.format(studio=self.studio)
        except:
            pass
        self.fanart = fanart
        self.poster = thumb
        self.banner = banner
        self.icon = icon

    def process_children(self, json_node):
        pass

    def set_watched_status(self, watched):
        if pyproxy.is_unicode_or_string(watched):
            watched = watched.lower() != 'false'

        url = self.base_url()
        url += '/watch' if watched else '/unwatch'
        url = pyproxy.set_parameter(url, 'id', self.id)
        # TODO DEPRECATED
        if plugin_addon.getSetting('syncwatched') == 'true':
            pyproxy.get_json(url)
        else:
            xbmc.executebuiltin('XBMC.Action(ToggleWatched)')

        # TODO DEPRECATED
        if plugin_addon.getSetting('sync_to_library') == 'true':
            # TODO NEED TO GET EPISODEID FROM FILE
            # IN DB FILES ARE STORED AS PATH: plugin://plugin.video.nakamori/  FILENAME: plugin://plugin.video.nakamori/tvshows/<ID>/ep/<EP_ID>/play
            # <ID> is not the same as shoko ID.
            # series are directories cmd = '{"jsonrpc":"2.0","method":"Files.GetDirectory","params":{"directory":"plugin://plugin.video.nakamori/tvshows/"},"id":1}'
            #cmd = '{"jsonrpc":"2.0","method":"Files.GetFileDetails","params":{"file":"plugin://plugin.video.nakamori/plugin://plugin.video.nakamori/tvshows/%s/play", "properties": ["episode", "title", "uniqueid", "tvshowid"]},"id":1}' % self.id
            #xbmc.log(str(cmd), xbmc.LOGNOTICE)
            #rpc = xbmc.executeJSONRPC(cmd)
            #xbmc.log(str(rpc), xbmc.LOGNOTICE)

            #cmd = '{"jsonrpc":"2.0","method":"VideoLibrary.GetEpisodeDetails","params":{"episodeid":%d},"id":1}' % self.id
            #xbmc.log(str(cmd), xbmc.LOGNOTICE)
            #rpc = xbmc.executeJSONRPC(cmd)
            #xbmc.log(str(rpc), xbmc.LOGNOTICE)

            # lastplayed = 'string'
            #cmd = '{"jsonrpc":"2.0","method":"VideoLibrary.SetEpisodeDetails","params":{"episodeid":%d,"playcount":%d},"id":1}' % (self.id, watched)
            #xbmc.log(str(cmd), xbmc.LOGNOTICE)
            #rpc = xbmc.executeJSONRPC(cmd)
            #xbmc.log(str(rpc), xbmc.LOGNOTICE)
            # TODO make this work - but not here :-)
            pass

        if plugin_addon.getSetting('watchedbox') == 'true':
            msg = localize(30201) + ' ' + (localize(30202) if watched else localize(30203))
            xbmc.executebuiltin('XBMC.Notification(' + localize(30200) + ', ' + msg + ', 2000, ' +
                                plugin_addon.getAddonInfo('icon') + ')')

    def vote(self, value):
        url = self.base_url() + '/vote'
        url = pyproxy.set_parameter(url, 'id', self.id)
        url = pyproxy.set_parameter(url, 'score', value)
        pyproxy.get_json(url)

    def get_listitem(self):
        """
        This creates a ListItem based on the model
        :return:
        :rtype: ListItem
        """
        url = self.get_plugin_url()
        name = self.name
        if self.make_bold:
            name = kodi_utils.bold(self.name)
        li = ListItem(name, path=url)
        li.setPath(url)
        infolabels = self.get_infolabels()
        li.set_watched_flags(infolabels, self.is_watched())
        li.setInfo(type='video', infoLabels=infolabels)
        li.set_art(self)
        context = self.get_context_menu_items()
        if context is not None and len(context) > 0:
            li.addContextMenuItems(context)
        return li

    def get_infolabels(self):
        return {'Title': self.name, 'Plot': self.name}

    def get_context_menu_items(self):
        context_menu = []

        # Refresh
        if plugin_addon.getSetting('context_refresh') == 'true':
            context_menu += [(plugin_addon.getLocalizedString(30131), script_utils.url_refresh())]

        # Information about Kodi menu being below
        context_menu += [('  ', 'empty'), ('  ', 'empty'), (plugin_addon.getLocalizedString(30147), 'empty')]
        # ,(plugin_addon.getLocalizedString(30148), 'empty')]
        return context_menu

    def __iter__(self):
        for i in self.items:
            yield i

    def is_watched(self):
        local_only = plugin_addon.getSetting('local_total') == 'true'
        no_specials = kodi_utils.get_kodi_setting('ignore_specials_watched')
        sizes = self.sizes
        if sizes is None:
            return WatchedStatus.UNWATCHED
        # count only local episodes
        if local_only and no_specials:
            # 0 is unwatched
            if sizes.watched_episodes == 0:
                return WatchedStatus.UNWATCHED
            # Should never be greater, but meh
            if sizes.watched_episodes >= sizes.local_episodes:
                return WatchedStatus.WATCHED
            # if it's between 0 and total, then it's partial
            return WatchedStatus.PARTIAL

        # count local episodes and specials
        if local_only:
            # 0 is unwatched
            if (sizes.watched_episodes + sizes.watched_specials) == 0:
                return WatchedStatus.UNWATCHED
            # Should never be greater, but meh
            if (sizes.watched_episodes + sizes.watched_specials) >= (sizes.local_episodes + sizes.local_specials):
                return WatchedStatus.WATCHED
            # if it's between 0 and total, then it's partial
            return WatchedStatus.PARTIAL

        # count episodes, including ones we don't have
        if no_specials:
            # 0 is unwatched
            if sizes.watched_episodes == 0:
                return WatchedStatus.UNWATCHED
            # Should never be greater, but meh
            if sizes.watched_episodes >= sizes.total_episodes:
                return WatchedStatus.WATCHED
            # if it's between 0 and total, then it's partial
            return WatchedStatus.PARTIAL

        # count episodes and specials, including ones we don't have
        # 0 is unwatched
        if (sizes.watched_episodes + sizes.watched_specials) == 0:
            return WatchedStatus.UNWATCHED
        # Should never be greater, but meh
        if (sizes.watched_episodes + sizes.watched_specials) >= (sizes.total_episodes + sizes.total_specials):
            return WatchedStatus.WATCHED
        # if it's between 0 and total, then it's partial
        return WatchedStatus.PARTIAL

    def get_watched_episodes(self):
        # we don't consider local, because we can't watch an episode that we don't have
        no_specials = kodi_utils.get_kodi_setting('ignore_specials_watched')
        sizes = self.sizes
        if sizes is None:
            return 0
        # count only local episodes
        if no_specials:
            return sizes.watched_episodes
        # count local episodes and specials
        return sizes.watched_episodes + sizes.watched_specials

    def get_total_episodes(self):
        local_only = plugin_addon.getSetting('local_total') == 'true'
        no_specials = kodi_utils.get_kodi_setting('ignore_specials_watched')
        sizes = self.sizes
        if sizes is None:
            return 0
        # count only local episodes
        if local_only and no_specials:
            return sizes.local_episodes
        # count local episodes and specials
        if local_only:
            return sizes.local_episodes + sizes.local_specials
        # count episodes, including ones we don't have
        if no_specials:
            return sizes.total_episodes
        # count episodes and specials, including ones we don't have
        return sizes.total_episodes + sizes.total_specials

    def hide_info(self, infolabels):
        self.hide_images()
        self.hide_title(infolabels)
        self.hide_description(infolabels)
        self.hide_ratings(infolabels)

    def hide_images(self):
        pass

    def hide_ratings(self, infolabels):
        if plugin_addon.getSetting('hide_rating_type') == 'Episodes':  # Series|Both
            return
        if plugin_addon.getSetting('hide_rating') == 'Always':
            del infolabels['rating']
            return
        if plugin_addon.getSetting('hide_rating') == 'Unwatched':
            if self.is_watched() == WatchedStatus.WATCHED:
                return
            del infolabels['rating']
            return
        if plugin_addon.getSetting('hide_rating') == 'All Unwatched':
            if self.is_watched() != WatchedStatus.UNWATCHED:
                return
            del infolabels['rating']

    def hide_title(self, infolabels):
        pass

    def hide_description(self, infolabels):
        if self.is_watched() == WatchedStatus.WATCHED:
            return
        if not kodi_utils.get_kodi_setting('videolibrary.showunwatchedplots')\
                or plugin_addon.getSetting('hide_plot') == 'true':
            infolabels['plot'] = localize(30079)

    def add_sort_methods(self, handle):
        xbmcplugin.addSortMethod(handle, Sorting.none.listitem_id)
        xbmcplugin.addSortMethod(handle, Sorting.title.listitem_id)
        xbmcplugin.addSortMethod(handle, Sorting.date.listitem_id)
        xbmcplugin.addSortMethod(handle, Sorting.rating.listitem_id)
        xbmcplugin.addSortMethod(handle, Sorting.year.listitem_id)

    def apply_default_sorting(self):
        sorting_setting = plugin_addon.getSetting('default_sort_series')
        kodi_utils.set_user_sort_method(sorting_setting)

    def bold(self):
        self.make_bold = True

    def normal(self):
        self.make_bold = False


class CustomItem(Directory):
    def __init__(self, name, image, plugin_url, sort_index=0, is_folder=True):
        """
        Create a custom menu item for the main menu
        :param name: the text of the item
        :type name: str
        :param image: image name, such as calendar.png
        :param plugin_url: the url to call to invoke it
        :type plugin_url: str
        """
        # we are making this overrideable for Unsorted and such

        Directory.__init__(self, 0, False)
        self._context_menu = []
        self.name = name
        self.plugin_url = plugin_url
        self.image = image
        self.is_kodi_folder = is_folder
        self.apply_image_override(image)

        self.infolabels = {'Title': self.name, 'Plot': self.name}

        self.size = 0
        self.sort_index = sort_index
        self.directory_filter = False
        self.make_bold = False

    def get_api_url(self):
        return None

    def url_prefix(self):
        return None

    def get_plugin_url(self):
        """
        :type: str
        """
        return self.plugin_url

    def get_infolabels(self):
        return self.infolabels

    def set_context_menu_items(self, context_menu):
        self._context_menu = context_menu

    def get_context_menu_items(self):
        return self._context_menu

    def set_watched_status(self, watched):
        pass

    def add_sort_methods(self, handle):
        pass

    def apply_default_sorting(self):
        pass


# noinspection Duplicates
class Filter(Directory):
    """
    A filter object, contains a unified method of representing a filter, with convenient converters
    """
    def __init__(self, json_node, build_full_object=False, get_children=False, parent_menu=''):
        """
        Create a filter object from a json node, containing everything that is relevant to a ListItem.
        You can also pass an ID for a small helper object.
        :param json_node: the json response from things like api/filter
        :type json_node: Union[list,dict]
        """
        Directory.__init__(self, json_node, get_children)
        # we are making this overrideable for Unsorted and such

        if parent_menu.endswith('/'):
            parent_menu = parent_menu[:-1]
        self.parent_url = parent_menu
        self.plugin_url = '%s/filter-%s/' % (parent_menu, self.id)
        if self.id == 0:  # 0 is for retrieving all Filters
            self.plugin_url = parent_menu

        self.directory_filter = False

        if build_full_object:
            # don't redownload info on an okay object
            if self.size < 0:
                # First, download basic info
                json_node = self.get_full_object()
                Directory.__init__(self, json_node, get_children)
                self.directory_filter = json_node.get('type', 'filter') == 'filters'
            # then download children, optimized for type
            if get_children and len(self.items) < 1:
                json_node = self.get_full_object()

        # check again, as we might have replaced it above
        if isinstance(json_node, int) or pyproxy.is_unicode_or_string(json_node):
            eh.spam(self)
            return

        self.apply_built_in_overrides()
        self.process_children(json_node)

        eh.spam(self)

    def get_api_url(self):
        url = self.base_url()
        level = 0
        if self.get_children and self.size > 0:
            level = 1 if self.directory_filter else 2
        url = model_utils.add_default_parameters(url, self.id, level)
        if self.id == 0:
            url = pyproxy.set_parameter(url, 'notag', 1)
        return url

    def url_prefix(self):
        """
        the /api/ extension point
        :return:
        """
        return 'filter'

    def get_plugin_url(self):
        """
        :type: str
        """
        return self.plugin_url

    def apply_built_in_overrides(self):
        # { 'Airing Today': 0, 'Calendar': 1, 'Seasons': 2, 'Years': 3, 'Tags': 4, 'Unsort': 5, 'Settings': 6,
        # 'Shoko Menu': 7, 'Search': 8 }
        if self.name == 'Continue Watching (SYSTEM)':
            self.name = 'Continue Watching'
        elif self.name == 'Seasons':
            self.sort_index = 3
            self.apply_image_override('seasons.png')
        elif self.name == 'Years':
            self.sort_index = 4
            self.apply_image_override('years.png')
        elif self.name == 'Tags':
            self.sort_index = 5
            self.apply_image_override('tags.png')
        elif self.name == 'Unsort':
            self.name = 'Unsorted Files'
            self.sort_index = 6
            self.apply_image_override('unsort.png')
            self.plugin_url = 'plugin://plugin.video.nakamori/menu-filter-unsorted/'

    def process_children(self, json_node):
        items = json_node.get('filters', [])
        for i in items:
            try:
                self.items.append(Filter(i, build_full_object=True, parent_menu=self.parent_url))
            except:
                pass
        items = json_node.get('groups', [])
        for i in items:
            try:
                group = self.get_collapsed_group(i)
                self.items.append(group)
            except:
                pass

    def get_collapsed_group(self, json_node):
        group = Group(json_node, build_full_object=True, filter_id=self.id, parent_menu=self.parent_url)
        if group.size == 1:
            if len(group.items) == 1 and group.items[0] is not None:
                group = group.items[0]
                if group.size < 0:
                    group = Series(group.id, parent_menu=self.parent_url)
            else:
                group = Group(json_node, build_full_object=True, filter_id=self.id, parent_menu=self.parent_url)
                group = group.items[0]
                if group.size < 0:
                    group = Series(group.id, build_full_object=True, parent_menu=self.parent_url)
        return group

    def get_context_menu_items(self):
        pass

    def set_watched_status(self, watched):
        pass


# noinspection Duplicates
class Group(Directory):
    """
    A group object, contains a unified method of representing a group, with convenient converters
    """
    def __init__(self, json_node, build_full_object=False, get_children=False, filter_id=0, parent_menu=''):
        """
        Create a group object from a json node, containing everything that is relevant to a ListItem.
        You can also pass an ID for a small helper object.
        :param json_node: the json response from things like api/group
        :param filter_id: used to filter groups when Apply To Series is enabled for a filter
        :type json_node: Union[list,dict]
        :type filter_id: int
        """
        self.filter_id = 0
        Directory.__init__(self, json_node, get_children)
        if parent_menu.endswith('/'):
            parent_menu = parent_menu[:-1]
        self.plugin_url = '%s/group-%s/' % (parent_menu, self.id)
        self.parent_menu = parent_menu

        # don't redownload info on an okay object
        if build_full_object and (self.size < 0 or (get_children and len(self.items) < 1)):
            json_node = self.get_full_object()
            Directory.__init__(self, json_node, get_children)
        if filter_id != 0 and filter_id != '0':
            self.filter_id = filter_id

        # check again, as we might have replaced it above
        if isinstance(json_node, int) or pyproxy.is_unicode_or_string(json_node):
            eh.spam(self)
            return

        self.date = model_utils.get_airdate(json_node)
        self.rating = float(str(json_node.get('rating', '0')).replace(',', '.'))
        self.user_rating = float(str(json_node.get('userrating', '0')).replace(',', '.'))
        self.votes = pyproxy.safe_int(json_node.get('votes', 0))
        self.actors = model_utils.get_cast_info(json_node)
        self.sizes = get_sizes(json_node)
        self.tags = model_utils.get_tags(json_node.get('tags', {}))
        self.overview = model_utils.make_text_nice(pyproxy.decode(json_node.get('summary', '')))

        self.process_children(json_node)

        eh.spam(self)

    def get_api_url(self):
        url = self.base_url()
        url = nakamori_utils.model_utils.add_default_parameters(url, self.id, 1 if self.get_children else 0)
        if self.filter_id != 0:
            url = pyproxy.set_parameter(url, 'filter', self.filter_id)
        return url

    def url_prefix(self):
        """
        the /api/ extension point
        :return:
        """
        return 'group'

    def get_plugin_url(self):
        return self.plugin_url

    def get_listitem(self):
        """

        :return:
        :rtype: ListItem
        """
        url = self.get_plugin_url()
        li = ListItem(self.name, path=url)
        infolabels = self.get_infolabels()
        li.setPath(url)
        li.set_watched_flags(infolabels, self.is_watched(), 1)
        self.hide_info(infolabels)
        li.setRating('anidb', float(infolabels.get('rating', 0.0)), infolabels.get('votes', 0), True)
        li.setInfo(type='video', infoLabels=infolabels)
        li.setCast(self.actors)
        li.setProperty('TotalEpisodes', str(self.get_total_episodes()))
        li.setProperty('WatchedEpisodes', str(self.get_watched_episodes()))
        li.setProperty('UnWatchedEpisodes', str(self.get_total_episodes() - self.get_watched_episodes()))
        li.addContextMenuItems(self.get_context_menu_items())
        li.set_art(self)
        return li

    def get_infolabels(self):
        cast, roles = model_utils.convert_cast_and_role_to_legacy(self.actors)
        infolabels = {
            'aired': self.date,
            'date': model_utils.get_date(self.date),
            'genre': self.tags,
            'plot': self.overview,
            'premiered': self.date,
            'rating': self.rating,
            'title': self.name,
            'userrating': self.user_rating,
            'path': self.get_plugin_url(),
            'cast': cast,
            'castandrole': roles,
            'mediatype': 'tvshow',
        }

        return infolabels

    def process_children(self, json_node):
        items = json_node.get('series', [])
        for i in items:
            try:
                self.items.append(Series(i, build_full_object=True, parent_menu=self.get_plugin_url()))
            except:
                pass

    def get_context_menu_items(self):
        context_menu = []

        # Mark as watched/unwatched
        watched_item = (localize(30126), script_utils.url_group_watched_status(self.id, True))
        unwatched_item = (localize(30127), script_utils.url_group_watched_status(self.id, False))
        if plugin_addon.getSetting('context_krypton_watched') == 'true':
            watched = self.is_watched()
            if watched == WatchedStatus.WATCHED:
                context_menu.append(unwatched_item)
            elif watched == WatchedStatus.UNWATCHED:
                context_menu.append(watched_item)
            else:
                context_menu.append(watched_item)
                context_menu.append(unwatched_item)
        else:
            context_menu.append(watched_item)
            context_menu.append(unwatched_item)

        return context_menu


# noinspection Duplicates
class Series(Directory):
    """
    A series object, contains a unified method of representing a series, with convenient converters
    """
    def __init__(self, json_node, build_full_object=False, get_children=False, compute_hash=False, seiyuu_pic=False,
                 use_aid=False, in_bookmark=False, force_cache=False, cache_time=0, parent_menu=''):
        """
        Create a series object from a json node, containing everything that is relevant to a ListItem
        :param json_node: the json response from things like api/serie
        :type json_node: Union[list,dict]
        """
        Directory.__init__(self, json_node, get_children)
        self.url = None
        self.item_type = 'tvshow'
        self.use_aid = use_aid
        if parent_menu.endswith('/'):
            parent_menu = parent_menu[:-1]
        self.plugin_url = '%s/series-%s/' % (parent_menu, self.id)
        self.parent_menu = parent_menu

        # don't redownload info on an okay object
        if build_full_object and (self.size < 0 or (get_children and len(self.items) < 1)):
            json_node = self.get_full_object(force_cache=force_cache, cache_time=cache_time)
            Directory.__init__(self, json_node, get_children)
        self.episode_types = []
        # check again, as we might have replaced it above
        if isinstance(json_node, int) or pyproxy.is_unicode_or_string(json_node):
            eh.spam(self)
            return

        self.alternate_name = model_utils.get_title(json_node, 'en', 'official')
        self.overview = model_utils.make_text_nice(pyproxy.decode(json_node.get('summary', '')))

        self.anidb_aid = pyproxy.safe_int(json_node.get('aid', 0))
        self.season = pyproxy.safe_int(json_node.get('season', '1'))
        self.date = model_utils.get_airdate(json_node)
        self.rating = float(str(json_node.get('rating', '0')).replace(',', '.'))
        self.user_rating = float(str(json_node.get('userrating', '0')).replace(',', '.'))
        self.votes = pyproxy.safe_int(json_node.get('votes', 0))
        if seiyuu_pic:
            fix_seiyuu_pic = True
        else:
            fix_seiyuu_pic = True if plugin_addon.getSetting('fix_seiyuu_pic') == 'true' else False
        self.actors = model_utils.get_cast_info(json_node, fix_seiyuu_pic)
        self.sizes = get_sizes(json_node)
        self.tags = model_utils.get_tags(json_node.get('tags', {}))
        self.is_movie = json_node.get('ismovie', 0) == 1
        if self.is_movie:
            self.item_type = 'movie'
        self.file_size = json_node.get('filesize', 0)
        self.year = json_node.get('year', 0)
        self.mpaa = self.get_mpaa_rating()
        self.studio = ''
        self.outline = " ".join(self.overview.split(".", 3)[:2])  # first 3 sentence
        self.hash = None
        self.in_favorite = False
        self.in_bookmark = in_bookmark
        self.match = json_node.get('match', '')

        self.process_children(json_node)

        if compute_hash:
            m = md5()
            if len(self.items) > 0:
                for episode in self.items:
                    # TODO need a date of update of file, but how to handle serie info update?
                    # for now we pick first date_added date from first file
                    m.update(episode.hash_content)
                self.hash = m.hexdigest().upper()

        eh.spam(self)

    def get_api_url(self):
        url = self.base_url()
        url = nakamori_utils.model_utils.add_default_parameters(url, self.id, 2 if self.get_children else 0)
        return url

    def url_prefix(self):
        try:
            if self.use_aid:
                return 'serie/fromaid'
        except:
            pass
        return 'serie'

    def get_plugin_url(self):
        return self.plugin_url

    def get_listitem(self, url=None, disable_coloring=False):
        """

        :return:
        :rtype: ListItem
        """
        self.url = url
        if self.url is None:
            self.url = self.get_plugin_url()

        if disable_coloring:
            name = self.name
        else:
            # We need to assume not airing, as there is no end date provided in API
            name = model_utils.title_coloring(self.name, self.sizes.local_episodes, self.sizes.total_episodes,
                                              self.sizes.local_specials, self.sizes.total_specials, False)

        li = ListItem(name, path=self.url)
        infolabels = self.get_infolabels()
        li.setPath(self.url)
        li.set_watched_flags(infolabels, self.is_watched(), 1)

        li.setUniqueIDs({'anidb': self.anidb_aid, 'anidb_aid': self.anidb_aid, 'shoko_aid': self.id})
        self.hide_info(infolabels)
        li.setRating('anidb', float(infolabels.get('rating', 0.0)), infolabels.get('votes', 0), True)
        li.setInfo(type='video', infoLabels=infolabels)
        li.setCast(self.actors)
        li.setProperty('TotalEpisodes', str(self.get_total_episodes()))
        li.setProperty('WatchedEpisodes', str(self.get_watched_episodes()))
        li.setProperty('UnWatchedEpisodes', str(self.get_total_episodes() - self.get_watched_episodes()))
        if self.hash is not None:
            li.setProperty('hash', self.hash)
        li.addContextMenuItems(self.get_context_menu_items())
        li.set_art(self)
        return li

    def get_infolabels(self):
        cast, roles = model_utils.convert_cast_and_role_to_legacy(self.actors)
        infolabels = {
            # See Episode.get_infolabels() for more info
            # ! general values
            # 'count': int,
            'size': self.file_size,
            'date': model_utils.get_date(self.date),

            # ! video values #
            'genre': self.tags,
            # 'country': string / list
            'year': self.year,
            # 'episode': int
            'season': self.season,
            # 'sortepisode': int,
            'sortseason': self.season,
            # 'episodeguide': string,
            # 'showlink': '',
            # 'top250': int
            # 'setid': int
            # 'tracknumber: int
            'rating': self.rating,
            'userrating': self.user_rating,
            # 'watched': <-- deprecaded, don't use
            # 'playcount': int,
            # 'overlay': int,
            'cast': cast,
            'castandrole': roles,
            # 'director': string / list
            'mpaa': self.mpaa,
            'plot': self.overview,
            'plotoutline': self.outline,
            'title': self.name,
            'originaltitle': self.alternate_name,
            'sorttitle': self.name,
            # 'duration': int (in seconds)
            # 'studio': string / list, // added below, great way to use
            'tagline': ', '.join(self.tags),
            # 'writer': string/list,
            'tvshowtitle': self.name,
            'premiered': self.date,
            # 'status': string
            # 'set': string
            # 'setoverview': overview
            'tag': ['nakamori', 'series'],
            # 'imdbnumber': string
            # 'code': string - produciton code
            'aired': self.date,
            # 'credits': string / list
            # 'lastplayed': string (Y-m-d h:m:s)
            # 'album': string
            # 'artist': list
            'votes': self.votes,
            'path': self.url,
            # 'trailer': string
            # 'dateadded': string (Y-m-d h:m:s) // added below, this is true in 99% of cases, apiv3
            'mediatype': self.item_type,
            # 'dbid' <-- forbidden to use
        }

        self.add_extra_infolabels(infolabels)

        return infolabels

    def add_extra_infolabels(self, infolabels):
        # items in a series are episodes, not files
        # this is also never populated
        #  we don't pull episodes when listing series, else it'll be slowed significantly
        # I suggest commenting out the call and making a TODO for APIv3
        e = self.items[0] if len(self.items) > 0 else None  # type: Episode
        if e is None:
            return
        f = e.get_file()
        if f is None:
            return

        # if kodi_utils.get_cond_visibility('System.HasAddon(resource.images.studios.white)') == 1:

        more_infolabels = {
            'dateadded': f.date_added,
            'studio': f.group,
        }
        for key in more_infolabels:
            infolabels[key] = more_infolabels[key]

    def process_children(self, json_node):
        items = json_node.get('eps', [])
        episode_types = []
        for i in items:
            try:
                episode = Episode(i, series=self, build_full_object=True)
                self.items.append(episode)
                if episode.episode_type not in episode_types:
                    episode_types.append(episode.episode_type)
            except:
                pass
        for i in episode_types:
            self.episode_types.append(SeriesTypeList(json_node, i, parent_menu=self.parent_menu))

    def get_context_menu_items(self):
        context_menu = []

        # Mark as watched/unwatched
        watched_item = (localize(30126), script_utils.url_series_watched_status(self.id, True))
        unwatched_item = (localize(30127), script_utils.url_series_watched_status(self.id, False))
        if plugin_addon.getSetting('context_krypton_watched') == 'true':
            watched = self.is_watched()
            if watched == WatchedStatus.WATCHED:
                context_menu.append(unwatched_item)
            elif watched == WatchedStatus.UNWATCHED:
                context_menu.append(watched_item)
            else:
                context_menu.append(watched_item)
                context_menu.append(unwatched_item)
        else:
            context_menu.append(watched_item)
            context_menu.append(unwatched_item)

        # Vote Series
        if plugin_addon.getSetting('context_show_vote_Series') == 'true':
            context_menu.append((localize(30124), script_utils.url_vote_for_series(self.id)))

        # Favorite
        if plugin_addon.getSetting('show_favorites') == 'true':
            if self.in_favorite:
                context_menu.append((localize(30213), script_utils.url_remove_favorite(self.id)))
            else:
                context_menu.append((localize(30212), script_utils.url_add_favorite(self.id)))

        # Bookmark
        if plugin_addon.getSetting('show_bookmark') == 'true':
            if self.in_bookmark:
                context_menu.append((localize(30217), script_utils.url_remove_bookmark(self.anidb_aid)))
            else:
                context_menu.append((localize(30216), script_utils.url_add_bookmark(self.anidb_aid)))

        # Playlist Mode
        context_menu.append((localize(30130), script_utils.url_playlist_series(series_id=self.id)))

        # TODO Things to add: View Cast, Play All, Related, Similar
        context_menu += Directory.get_context_menu_items(self)
        return context_menu

    def vote(self, value):
        Directory.vote(self, value)
        xbmc.executebuiltin('XBMC.Notification(%s, %s %s, 7500, %s)' % (script_addon.getLocalizedString(30021),
                                                                        script_addon.getLocalizedString(30022),
                                                                        str(value), plugin_addon.getAddonInfo('icon')))

    def add_sort_methods(self, handle):
        xbmcplugin.addSortMethod(handle, Sorting.none.listitem_id)
        xbmcplugin.addSortMethod(handle, Sorting.episode_number.listitem_id)
        xbmcplugin.addSortMethod(handle, Sorting.date.listitem_id)
        xbmcplugin.addSortMethod(handle, Sorting.title.listitem_id)
        xbmcplugin.addSortMethod(handle, Sorting.rating.listitem_id)
        xbmcplugin.addSortMethod(handle, Sorting.year.listitem_id)

    def apply_default_sorting(self):
        sorting_setting = plugin_addon.getSetting('default_sort_episodes')
        kodi_utils.set_user_sort_method(sorting_setting)

    def get_mpaa_rating(self):
        """
        This is unfortunately bound by the tag filter. We may do something about it in APIv3
        shameless copy from Cazzar/ShokoMetadata.bundle
        :return:
        """
        # these are case sensitive, and they are not lowercase
        if 'Kodomo' in self.tags:
            return 'TV-Y'
        if 'Mina' in self.tags:
            return 'TV-G'
        if 'Shoujo' in self.tags:
            return 'TV-14'
        if 'Shounen' in self.tags:
            return 'TV-14'
        if 'Josei' in self.tags:
            return 'TV-14'
        if 'Seinen' in self.tags:
            return 'TV-MA'
        if 'Mature' in self.tags:
            return 'TV-MA'
        if '18 Restricted' in self.tags:
            return 'TV-R'
        return ''

    def suggest_rating_based_on_episode_rating(self):
        rating_sum = 0.0
        items_count = 0
        for ep in self.items:
            if ep.episode_type == 'Episode':
                rating_sum += ep.user_rating
                items_count += 1
        if items_count > 0:
            return rating_sum/items_count
        return 0

    def did_you_rate_every_episode(self):
        for ep in self.items:
            if ep.user_rating == 0 and ep.episode_type == 'Episode':
                return False
        return True

    def is_in_favorite(self):
        self.in_favorite = True


# noinspection Duplicates
class SeriesTypeList(Series):
    """
    The Episode Type List for a series
    """
    def __init__(self, json_node, episode_type, get_children=False, force_cache=False, cache_time=0, parent_menu=''):
        self.episode_type = episode_type
        if isinstance(json_node, int) or pyproxy.is_unicode_or_string(json_node):
            self.id = json_node
            self.get_children = get_children
            json_node = self.get_full_object(force_cache=force_cache, cache_time=cache_time)
        Series.__init__(self, json_node, get_children=get_children, force_cache=force_cache, cache_time=cache_time)
        if parent_menu.endswith('/'):
            parent_menu = parent_menu[:-1]
        self.plugin_url = '%s/type-%s/' % (parent_menu, self.episode_type)

    def process_children(self, json_node):
        items = json_node.get('eps', [])
        for i in items:
            try:
                episode = Episode(i, series=self)
                if episode.episode_type != self.episode_type:
                    continue
                self.items.append(episode)
            except:
                pass

    def get_plugin_url(self):
        return self.plugin_url

    def get_listitem(self):
        """

        :return:
        :rtype: ListItem
        """
        url = self.get_plugin_url()

        li = ListItem(self.episode_type, path=url)
        infolabels = self.get_infolabels()
        li.setPath(url)
        li.set_watched_flags(infolabels, self.is_watched(), 1)
        self.hide_info(infolabels)
        li.setRating('anidb', float(infolabels.get('rating', 0.0)), infolabels.get('votes', 0), True)
        li.setInfo(type='video', infoLabels=infolabels)
        li.setCast(self.actors)
        li.setProperty('TotalEpisodes', str(self.get_total_episodes()))
        li.setProperty('WatchedEpisodes', str(self.get_watched_episodes()))
        li.setProperty('UnWatchedEpisodes', str(self.get_total_episodes() - self.get_watched_episodes()))
        li.addContextMenuItems(self.get_context_menu_items())
        li.set_art(self)
        return li

    def get_infolabels(self):
        infolabels = {
            'aired': self.date,
            'date': model_utils.get_date(self.date),
            'originaltitle': self.alternate_name,
            'genre': self.tags,
            'plot': self.overview,
            'premiered': self.date,
            'rating': self.rating,
            'season': self.season,
            'title': self.episode_type,
            'userrating': self.user_rating,
            'path': self.get_plugin_url(),
            'mediatype': 'tvshow',
        }

        return infolabels

    def is_watched(self):
        local_only = plugin_addon.getSetting('local_total') == 'true'
        sizes = self.sizes
        if sizes is None:
            return WatchedStatus.UNWATCHED

        # count only local episodes
        if local_only and self.episode_type == 'Episode':
            # 0 is unwatched
            if sizes.watched_episodes == 0:
                return WatchedStatus.UNWATCHED
            # Should never be greater, but meh
            if sizes.watched_episodes >= sizes.local_episodes:
                return WatchedStatus.WATCHED
            # if it's between 0 and total, then it's partial
            return WatchedStatus.PARTIAL

        # count local episodes and specials
        if local_only and self.episode_type == 'Special':
            # 0 is unwatched
            if sizes.watched_specials == 0:
                return WatchedStatus.UNWATCHED
            # Should never be greater, but meh
            if sizes.watched_specials >= sizes.local_specials:
                return WatchedStatus.WATCHED
            # if it's between 0 and total, then it's partial
            return WatchedStatus.PARTIAL

        # count episodes, including ones we don't have
        if self.episode_type == 'Episode':
            # 0 is unwatched
            if sizes.watched_episodes == 0:
                return WatchedStatus.UNWATCHED
            # Should never be greater, but meh
            if sizes.watched_episodes >= sizes.total_episodes:
                return WatchedStatus.WATCHED
            # if it's between 0 and total, then it's partial
            return WatchedStatus.PARTIAL

        # count specials, including ones we don't have
        if self.episode_type == 'Special':
            # 0 is unwatched
            if sizes.watched_specials == 0:
                return WatchedStatus.UNWATCHED
            # Should never be greater, but meh
            if sizes.watched_specials >= sizes.total_specials:
                return WatchedStatus.WATCHED
            # if it's between 0 and total, then it's partial
            return WatchedStatus.PARTIAL

        return WatchedStatus.UNWATCHED

    def get_watched_episodes(self):
        # we don't consider local, because we can't watch an episode that we don't have
        sizes = self.sizes
        if sizes is None:
            return 0
        # count only local episodes
        if self.episode_type == 'Episode':
            return sizes.watched_episodes
        # count local episodes and specials
        if self.episode_type == 'Special':
            return sizes.watched_specials
        return 0

    def get_total_episodes(self):
        local_only = plugin_addon.getSetting('local_total') == 'true'
        sizes = self.sizes
        if sizes is None:
            return 0
        # count only local episodes
        if self.episode_type == 'Episode':
            if local_only:
                return sizes.local_episodes
            else:
                return sizes.total_episodes
        # count local episodes and specials
        if self.episode_type == 'Special':
            if local_only:
                return sizes.local_specials
            else:
                return sizes.total_specials
        return 0


# noinspection Duplicates
class Episode(Directory):
    """
    An episode object, contains a unified method of representing an episode, with convenient converters
    """
    def __init__(self, json_node, series=None, build_full_object=False):
        """
        Create an episode object from a json node, containing everything that is relevant to a ListItem
        :param json_node: the json response from things like api/serie.eps[]
        :type json_node: Union[list,dict]
        """
        self.series_id = 0
        self.series_name = None
        self.anidb_aid = 0
        self.anidb_eid = 0
        self.actors = []
        self.url = None
        self.item_type = 'episode'
        if series is not None:
            self.series_id = series.id
            self.series_name = series.name
            self.actors = series.actors
            self.anidb_aid = series.anidb_aid
            if series.is_movie:
                self.item_type = 'movie'

        Directory.__init__(self, json_node, True)
        # don't redownload info on an okay object
        if build_full_object and self.size < 0:
            json_node = self.get_full_object()
            Directory.__init__(self, json_node)
        # check again, as we might have replaced it above
        if isinstance(json_node, int) or pyproxy.is_unicode_or_string(json_node):
            eh.spam(self)
            return

        self.episode_number = pyproxy.safe_int(json_node.get('epnumber', ''))
        self.episode_type = json_node.get('eptype', 'Other')
        if self.anidb_aid == 0:
            self.anidb_aid = pyproxy.safe_int(json_node.get('aid', 0))
        self.anidb_eid = pyproxy.safe_int(json_node.get('eid', 0))
        self.date = model_utils.get_airdate(json_node)
        self.tvdb_episode = json_node.get('season', '0x0')
        self.update_date = None
        self.hash_content = None

        self.process_children(json_node)

        if self.name is None:
            self.name = 'Episode ' + str(self.episode_number)
        self.alternate_name = model_utils.get_title(json_node, 'x-jat', 'main')

        self.watched = pyproxy.safe_int(json_node.get('view', 0)) != 0
        self.watched_date = str(json_node.get('view_date', ''))
        self.year = pyproxy.safe_int(json_node.get('year', ''))

        self.rating = float(str(json_node.get('rating', '0')).replace(',', '.'))
        self.user_rating = float(str(json_node.get('userrating', '0')).replace(',', '.'))
        self.overview = model_utils.make_text_nice(pyproxy.decode(json_node.get('summary', '')))
        self.votes = pyproxy.safe_int(json_node.get('votes', ''))
        self.outline = " ".join(self.overview.split(".", 3)[:2])  # first 3 sentence
        self.tags = model_utils.get_tags(json_node.get('tags', {}))

        if self.episode_type != 'Special':
            season = str(json_node.get('season', '1'))
            if 'x' in season:
                season = season.split('x')[0]
        else:
            season = '0'
        self.season = pyproxy.safe_int(season)

        eh.spam(self)

    def get_file(self):
        """
        :return: the first file in the list, or None if not populated
        :rtype: File / None
        """
        if len(self.items) > 0 and self.items[0] is not None:
            return self.items[0]
        return None

    def get_file_with_id(self, file_id):
        """
        :param file_id: a file ID
        :return: the file with the given ID
        :rtype: File
        """
        for f in self.items:
            if f is None:
                continue
            if f.id == int(file_id):
                return f
        return None

    def get_api_url(self):
        # this one doesn't matter much atm, but I'll prolly copy and paste for APIv3, so I'll leave it in
        url = self.base_url()
        url = nakamori_utils.model_utils.add_default_parameters(url, self.id, 1)
        return url

    def url_prefix(self):
        return 'ep'

    def get_plugin_url(self, party_mode=False):
        if party_mode:
            return plugin_utils.url_play_video(self.id, 0)
        return plugin_utils.url_play_video(self.id, 0)

    def is_watched(self):
        if self.watched:
            return WatchedStatus.WATCHED
        f = self.get_file()
        if f is not None and f.resume_time > 0:
            return WatchedStatus.PARTIAL
        return WatchedStatus.UNWATCHED

    def get_listitem(self, url=None):
        """

        :return:
        :rtype: ListItem
        """
        self.url = url
        if self.url is None:
            self.url = self.get_plugin_url()
        li = ListItem(self.name, path=self.url)
        li.setPath(self.url)
        infolabels = self.get_infolabels()

        # set watched flags
        if self.watched:
            li.set_watched_flags(infolabels, WatchedStatus.WATCHED)
        elif self.get_file() is not None and self.get_file().resume_time > 0:
            li.set_watched_flags(infolabels, WatchedStatus.PARTIAL, self.get_file().resume_time)
        else:
            li.set_watched_flags(infolabels, WatchedStatus.UNWATCHED)

        self.hide_info(infolabels)
        li.setRating('anidb', float(infolabels.get('rating', 0.0)), infolabels.get('votes', 0), True)
        li.setInfo(type='video', infoLabels=infolabels)
        li.set_art(self)
        li.setCast(self.actors)

        li.setUniqueIDs({'anidb_eid': self.anidb_eid, 'shoko_eid': self.id})
        if self.series_id != 0:
            li.setUniqueIDs({'anidb_aid': self.anidb_aid, 'shoko_aid': self.series_id})

        f = self.get_file()
        if f is not None:
            model_utils.set_stream_info(li, f)

        li.addContextMenuItems(self.get_context_menu_items())
        return li

    def get_infolabels(self):
        cast, roles = model_utils.convert_cast_and_role_to_legacy(self.actors)
        infolabels = {
            # ! general values
            # 'count': int, -- The info on this is vague. It's mostly used for sorting and helper functions in skins
            # 'size': long,  // added below
            'date': model_utils.get_date(self.date),

            # ! video values #
            'genre': self.tags,
            # 'country': string / list -- Probably going to be Japan, but there are some Chinese, US, and Korean ones
            'year': self.year,
            'episode': self.episode_number,
            'season': self.season,
            # 'sortepisode': int, -- This is for weird situations like a special in the middle. We don't have use for it
            # 'sortseason': int -- it could be used in mapping things like monogatari which isn't in order, but meh
            # 'episodeguide': string, -- pretty sure this is PVR only, but I could be mistaken
            # 'showlink': '', -- it's another api endpoint, but we *can* populate this
            # 'top250': int -- useless. This holds where it reached in the top 250 on charts. We don't have such info
            # 'setid': int -- like dbid, DON'T USE
            # 'tracknumber: int - only for music, not relevant and we don't have info
            'rating': self.rating,
            'userrating': self.user_rating,
            # 'watched': <-- deprecaded, don't use
            # 'playcount': 1 if self.watched else 0, -- this is set later in li.set_watched_flags()
            # 'overlay': int, -- same to above
            'cast': cast,
            'castandrole': roles,
            # 'director': string / list -- we don't have such info yet, but it could be used later
            # 'mpaa': string -- we don't have such info yet, but it could be used later
            'plot': self.overview,
            'plotoutline': self.outline,
            'title': self.name,
            'originaltitle': self.alternate_name,
            'sorttitle': model_utils.get_sort_name(self),
            # 'duration': int (in seconds) // added below
            # 'studio': string / list, -- we don't have such info yet, but it could be used later
            # 'tagline': string, -- This is for American movies mostly. I've never understood the purpose
            # 'writer': string/list, -- we don't have such info yet, but it could be used later
            'tvshowtitle': self.series_name,
            'premiered': self.date,
            # 'status': string
            # 'set': string <-- this is the 1000% way for name of Group of Series (bakamonogatari group), apiv3
            # 'setoverview': overview -- like dbid, depending on how Kodi handles it, we could use it for series plot
            # 'tag': ['nakamori', 'episode'],  <-- not working for episodes
            # 'imdbnumber': string
            # 'code': string - produciton code
            'aired': self.date,
            # 'credits': string / list -- we don't have such info yet, but it could be used later.
            # 'lastplayed': string (Y-m-d h:m:s) -- we aren't given this info from API, but it could be used later
            # 'album': string -- we don't have the info, kodi might not take it unless we mark it as a music video
            # 'artist': list -- we don't have the info, kodi might not take it unless we mark it as a music video
            'votes': self.votes,
            'path': self.url,
            # 'trailer': string -- url to a trailer video. We don't have this info, but we might be able to later
            # 'dateadded': string (Y-m-d h:m:s) // added below
            'mediatype': self.item_type,
            # 'dbid' <-- forbidden to use
        }

        f = self.items[0] if len(self.items) > 0 else None  # type: File
        if f is not None:
            more_infolabels = {
                'duration': kodi_proxy.duration_to_kodi(f.duration),
                'size': f.size,
                'dateadded': f.date_added
            }
            for key in more_infolabels:
                infolabels[key] = more_infolabels[key]
        return infolabels

    def process_children(self, json_node):
        for _file in json_node.get('files', []):
            try:
                f = File(_file, True)

                # add only video files to items list
                if f.isVideo:
                    self.items.append(f)

                # TODO REPLACE WITH PROPER UPDATE DATE MOVE THIS OUT HERE
                if self.update_date is None:
                    self.update_date = f.date_added
                if self.hash_content is None:
                    self.hash_content = str(self.get_plugin_url()).encode('utf-8')
                    if f.size is not None:
                        self.hash_content += str(f.size).encode('utf-8')
                    if f.date_added is not None and len(f.date_added) >= 10:
                        # datetime im broken this one should work but is not, and im not using 8 line funny workaround
                        # str(datetime.strptime(str(f.date_added), '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y')).encode('utf-8')
                        # https://bugs.python.org/issue27400
                        x = str(f.date_added)[8:10] + '.' +str(f.date_added)[5:7] + '.' + str(f.date_added)[0:4]
                        self.hash_content += str(x).encode('utf-8')
            except Exception as ex:
                eh.exception(eh.ErrorPriority.HIGHEST, ex)

    def get_context_menu_items(self):
        # Calls to Plugin from Context Menus need 'RunPlugin(%s)' %
        context_menu = []
        # Play
        if plugin_addon.getSetting('context_show_play') == 'true':
            # I change this to play, because with 'show info' this does not play file
            url = plugin_utils.url_play_video(self.id, self.get_file().id, runplugin=True)
            context_menu.append((localize(30065), url))
            # context_menu.append((localize(30065), 'Action(Select)'))

        # Resume
        if self.get_file() is not None and self.get_file().resume_time > 0 \
                and plugin_addon.getSetting('file_resume') == 'true':
            label = localize(30141) + ' (%s)' % time.strftime('%H:%M:%S', time.gmtime(self.get_file().resume_time))
            url = plugin_utils.url_resume_video(self.id, self.get_file().id, runplugin=True)
            context_menu.append((label, url))

        # Play (No Scrobble)
        if plugin_addon.getSetting('context_show_play_no_watch') == 'true':
            context_menu.append((localize(30132), plugin_utils.url_play_video_without_marking(self.id, self.get_file().id, runplugin=True)))

        # Play (transcode)
        if plugin_addon.getSetting('context_show_force_transcode') == 'true' and plugin_addon.getSetting('eigakan_handshake') == 'true':
            context_menu.append((localize(30174), plugin_utils.url_transcode_play_video(self.id, self.get_file().id, runplugin=True)))

        # Play (Direct)
        if plugin_addon.getSetting('enableEigakan') == 'true' and plugin_addon.getSetting('context_show_directplay') == 'true':
            if plugin_addon.getSetting('context_pick_file') == 'true' and len(self.items) > 1:
                context_menu.append((localize(30175), plugin_utils.url_direct_play_video(self.id, runplugin=True)))
            else:
                context_menu.append((localize(30175), plugin_utils.url_direct_play_video(self.id, self.get_file().id, runplugin=True)))

        # Inspect
        if plugin_addon.getSetting('context_pick_file') == 'true' and len(self.items) > 1:
            context_menu.append((localize(30133), script_utils.url_file_list(self.id)))

        # Mark as watched/unwatched
        watched_item = (localize(30128), script_utils.url_episode_watched_status(self.id, True))
        unwatched_item = (localize(30129), script_utils.url_episode_watched_status(self.id, False))
        if plugin_addon.getSetting('context_krypton_watched') == 'true':
            if self.watched:
                context_menu.append(unwatched_item)
            else:
                context_menu.append(watched_item)
        else:
            context_menu.append(watched_item)
            context_menu.append(unwatched_item)

        # Play From Here
        if plugin_addon.getSetting('context_playlist') == 'true':
            # context_menu.append((localize(30130), 'TO BE ADDED TO SCRIPT'))
            pass

        # Vote Episode
        if plugin_addon.getSetting('context_show_vote_Episode') == 'true':
            context_menu.append((localize(30125), script_utils.url_vote_for_episode(self.id)))

        # Vote Series
        if plugin_addon.getSetting('context_show_vote_Series') == 'true' and self.series_id != 0:
            context_menu.append((localize(30124), script_utils.url_vote_for_series(self.series_id)))

        # Metadata
        if plugin_addon.getSetting('context_show_info') == 'true':
            context_menu.append((localize(30123), 'Action(Info)'))

        # View Cast
        # this was comment out, leaving until clean up
        #if plugin_addon.getSetting('context_view_cast') == 'true' and self.series_id != 0:
            # context_menu.append((localize(30134), 'RunPlugin(%s&cmd=viewCast)'))
        #    pass

        # Probe
        if plugin_addon.getSetting('enableEigakan') == 'true' and plugin_addon.getSetting('context_show_probe') == 'true':
            if plugin_addon.getSetting('context_pick_file') == 'true' and len(self.items) > 1:
                context_menu.append((localize(30177), script_utils.url_probe_episode(ep_id=self.id)))
            else:
                file_ = self.get_file()
                file_id = file_.id
                context_menu.append((localize(30177), script_utils.url_probe_file(file_id=file_id)))

        # Transcode
        if plugin_addon.getSetting('enableEigakan') == 'true':
            if plugin_addon.getSetting('context_pick_file') == 'true' and len(self.items) > 1:
                context_menu.append((localize(30176), script_utils.url_transcode_episode(ep_id=self.id)))
            else:
                file_ = self.get_file()
                file_id = file_.id
                context_menu.append((localize(30176), script_utils.url_transcode_file(file_id=file_id)))

        # Playlist Mode
        if not self.watched:
            context_menu.append((localize(30130), script_utils.url_playlist_series(series_id=self.series_id)))

        # the default ones that say the rest are kodi's
        context_menu += Directory.get_context_menu_items(self)

        return context_menu

    def vote(self, value):
        Directory.vote(self, value)
        xbmc.executebuiltin('XBMC.Notification(%s, %s %i, 7500, %s)' % (script_addon.getLocalizedString(30023),
                                                                        script_addon.getLocalizedString(30022),
                                                                        value, plugin_addon.getAddonInfo('icon')))

    def hide_images(self):
        if plugin_addon.getSetting('hide_images') == 'true' and self.is_watched() != WatchedStatus.WATCHED:
            self.apply_image_override('hidden.png')

    def hide_title(self, infolabels):
        if plugin_addon.getSetting('hide_title') == 'Never' or self.is_watched() == WatchedStatus.WATCHED:
            return
        if self.episode_type == 'Special':
            if plugin_addon.getSetting('hide_title') == 'Episodes':  # both,specials
                return
            infolabels['title'] = localize(30076) + ' ' + str(self.episode_number)
        elif self.episode_type == 'Episode':
            if plugin_addon.getSetting('hide_title') == 'Specials':  # both,episodes
                return
            infolabels['title'] = localize(30076) + ' ' + str(self.episode_number)

    def hide_ratings(self, infolabels):
        if plugin_addon.getSetting('hide_rating_type') == 'Series':  # Episodes|Both
            return
        if plugin_addon.getSetting('hide_rating') == 'Always':
            del infolabels['rating']
            return
        if plugin_addon.getSetting('hide_rating') == 'Unwatched':
            if self.is_watched() == WatchedStatus.WATCHED:
                return
            del infolabels['rating']
            return
        if plugin_addon.getSetting('hide_rating') == 'All Unwatched':
            if self.is_watched() != WatchedStatus.UNWATCHED:
                return
            del infolabels['rating']


# noinspection Duplicates
class File(Directory):
    """
    A file object, contains a unified method of representing a json_node file, with convenient converters
    """
    def __init__(self, json_node, build_full_object=False):
        """
        Create a file object from a json node, containing everything that is relevant to a ListItem
        :param json_node: the json response from things like api/file
        :type json_node: Union[list,dict]
        """
        Directory.__init__(self, json_node)
        self.server_path = ''
        self.file_url = ''

        # don't redownload info on an okay object
        if build_full_object and self.size < 0:
            json_node = self.get_full_object()
            Directory.__init__(self, json_node)
        # check again, as we might have replaced it above
        if isinstance(json_node, int) or pyproxy.is_unicode_or_string(json_node):
            eh.spam(self)
            return

        self.name = os.path.split(pyproxy.decode(json_node.get('filename', 'None')))[-1]
        # mark file if it contains video or not (by checking for subtitles extension - which is smaller pool)
        self.file_name, self.file_extension = os.path.splitext(self.name)
        self.isVideo = False if self.file_extension in ['.srt', '.sub', '.sbv', '.vtt', '.idx', '.ssa', '.ass',
                                                        '.smi', '.psb', '.usf', '.ssf', '.ttml', '.dfxp', '.xml',
                                                        '.smil'] else True

        self.resume_time = int(int(json_node.get('offset', '0')) / 1000)

        # Check for empty duration from MediaInfo check fail and handle it properly
        self.duration = json_node.get('duration', 1)

        self.size = pyproxy.safe_int(json_node.get('size', 0))
        # this is the only URL that is given not as a short URL, because proxies and BS, we need to rewrite it
        url = pyproxy.decode(json_node.get('url', ''))
        url = url[url.rindex(':') + 1:]
        url = url[url.index('/'):]
        self.file_url = server + url
        self.server_path = json_node.get('server_path', '')

        self.date_added = pyproxy.decode(json_node.get('created', '')).replace('T', ' ')
        self.group = json_node.get('group_full', '')

        if len(json_node.get('media', {})) > 0:
            try:
                self.video_streams = model_utils.get_video_streams(json_node['media'])
            except:
                self.video_streams = {}
            try:
                self.audio_streams = model_utils.get_audio_streams(json_node['media'])
            except:
                self.audio_streams = {}
            try:
                self.sub_streams = model_utils.get_sub_streams(json_node['media'])
            except:
                self.sub_streams = {}
        else:
            self.video_streams = {}
            self.audio_streams = {}
            self.sub_streams = {}

        eh.spam(self)

    def get_full_object(self):
        url = self.get_api_url()
        json_body = pyproxy.get_json(url, True)
        if json_body is None:
            return None
        json_node = json.loads(json_body)
        return json_node

    def get_api_url(self):
        url = self.base_url()
        url = nakamori_utils.model_utils.add_default_parameters(url, self.id, 1)
        return url

    def url_prefix(self):
        return 'file'

    def get_plugin_url(self):
        return plugin_utils.url_play_video_without_marking(0, self.id)

    @property
    def remote_url_for_player(self):
        return self.file_url

    @property
    def url_for_player(self):
        if os.path.isfile(pyproxy.encode(self.server_path)):
            if self.server_path.startswith(u'\\\\'):
                return u'smb:' + self.server_path.replace('\\', '/')
            return self.server_path
        return self.file_url

    def get_listitem(self):
        """
        This should only be used as a temp object to feed to the player or it is unrecognized
        :rtype: ListItem
        """
        url = self.get_plugin_url()
        li = ListItem(self.name, path=url)
        li.setPath(url)
        infolabels = self.get_infolabels()
        li.setInfo(type='video', infoLabels=infolabels)

        # Files don't have watched states in the API, so this is all that's needed
        if self.resume_time > 0 and plugin_addon.getSetting('file_resume') == 'true':
            li.setProperty('ResumeTime', str(self.resume_time))

        model_utils.set_stream_info(li, self)
        li.set_art(self)
        li.addContextMenuItems(self.get_context_menu_items())
        return li

    def get_infolabels(self):
        """
        :param self:
        :type self: File
        :return:
        """
        infolabels = {

            'path': self.get_plugin_url(),
            'mediatype': 'episode',
            'duration': kodi_proxy.duration_to_kodi(self.duration),
            'size': self.size,
            'dateadded': self.date_added
        }
        return infolabels

    def get_context_menu_items(self):
        context_menu = [
            (localize(30120), script_utils.url_rescan_file(self.id)),
            (localize(30121), script_utils.url_rehash_file(self.id))
        ]
        # the default ones that say the rest are kodi's
        context_menu += Directory.get_context_menu_items(self)
        return context_menu

    def set_watched_status(self, watched):
        if watched:
            return
        self.set_resume_time(0)
        # this isn't really supported atm, so no need for the rest of the stuff here

    def set_resume_time(self, current_time):
        """
        sync offset of played file
        :param current_time: current time in seconds
        """
        offset_url = server + '/api/file/offset'
        offset_body = '"id":%i,"offset":%i' % (self.id, current_time)
        pyproxy.post_json(offset_url, offset_body)
        
    def rehash(self):
        shoko_utils.rehash_file(self.id)

    def rescan(self):
        shoko_utils.rescan_file(self.id)


class Sizes(object):
    def __init__(self):
        self.local_episodes = 0
        self.local_specials = 0
        self.local_total = 0
        self.watched_episodes = 0
        self.watched_specials = 0
        self.watched_total = 0
        self.total_episodes = 0
        self.total_specials = 0
        self.total = 0


def get_sizes(json_node):
    result = Sizes()
    local_sizes = json_node.get('local_sizes', {})
    result.local_episodes = pyproxy.safe_int(local_sizes.get('Episodes', 0))
    result.local_specials = pyproxy.safe_int(local_sizes.get('Specials', 0))
    result.local_total = pyproxy.safe_int(json_node.get('localsize', 0))
    watched_sizes = json_node.get('watched_sizes', {})
    result.watched_episodes = pyproxy.safe_int(watched_sizes.get('Episodes', 0))
    result.watched_specials = pyproxy.safe_int(watched_sizes.get('Specials', 0))
    result.watched_total = pyproxy.safe_int(json_node.get('watchedsize', 0))
    total_sizes = json_node.get('total_sizes', {})
    result.total_episodes = pyproxy.safe_int(total_sizes.get('Episodes', 0))
    result.total_specials = pyproxy.safe_int(total_sizes.get('Specials', 0))
    result.total = pyproxy.safe_int(json_node.get('size', 0))
    return result


@eh.try_function(eh.ErrorPriority.NORMAL)
def get_series_for_episode(ep_id):
    url = server + '/api/serie/fromep'
    url = nakamori_utils.model_utils.add_default_parameters(url, ep_id, 0)
    json_body = pyproxy.get_json(url)
    json_node = json.loads(json_body)
    return Series(json_node)


class ImportFolder(object):
    def __init__(self, json_node, build_full_object=False):
        self.id = 0
        self.name = ''
        self.type = ''
        self.location = ''
        self.isDropSource = False
        self.isDropDestination = False
        self.isWatched = False
        self.filesize = 0
        self.size = 0
        self.capacity = ''

        if isinstance(json_node, int):
            self.id = int(json_node)
            return

        if build_full_object:
            json_node = self.get_full_object()
        self.process(json_node)
        self.plugin_url = plugin_utils.url_show_folder_menu(self.id)
        self.extra_data()

    def extra_data(self):
        json_extra = pyproxy.get_json(server + '/api/serie/infobyfolder?id=%s' % self.id)
        if json_extra is not None:
            json_extra = json.loads(json_extra)
            self.size = int(json_extra.get('size', 0))
            self.filesize = int(json_extra.get('filesize', 0))
            capacity, units = convert_units(self.filesize)
            self.capacity = '%s %s' % (capacity, units)

    def process(self, json_node):
        body = json_node
        self.id = int(body.get('ImportFolderID', 0))
        self.location = body.get('ImportFolderLocation' '')
        self.name = body.get('ImportFolderName', 'NA')
        if self.name == 'NA':
            self.name = self.location
        self.type = int(body.get('ImportFolderType', 0))
        self.isDropSource = True if int(body.get('isDropSource', 0)) == 1 else False
        self.isDropDestination = True if int(body.get('isDropDestination', 0)) == 1 else False
        self.isWatched = True if int(body.get('isWatched', 0)) == 1 else False

    def get_full_object(self):
        url = self.get_api_url()
        json_body = pyproxy.get_json(url)
        if json_body is None:
            return None
        json_node = json.loads(json_body)
        return json_node

    def get_api_url(self):
        url = self.base_url()
        return url

    def base_url(self):
        return server + '/api/' + self.url_prefix()

    def url_prefix(self):
        return 'folder/%s' % self.id

    def get_plugin_url(self):
        return self.plugin_url

    def get_infolabels(self):
        return {'Title': self.name, 'Plot': self.capacity}

    def get_listitem(self):
        url = self.get_plugin_url()
        li = ListItem(self.name, path=url)
        li.setPath(url)
        infolabels = self.get_infolabels()
        li.setInfo(type='video', infoLabels=infolabels)
        # li.set_art(self)
        context = self.get_context_menu_items()
        if context is not None and len(context) > 0:
            li.addContextMenuItems(context)
        return li

    def get_context_menu_items(self):
        context_menu = []
        # TODO edit folder https://github.com/ShokoAnime/ShokoServer/blob/master/Shoko.Server/API/v2/Modules/Common.cs#L93
        # TODO delete folder https://github.com/ShokoAnime/ShokoServer/blob/master/Shoko.Server/API/v2/Modules/Common.cs#L121

        context_menu += [('rescan this folder', script_utils.url_folder_scan(self.id))]
        context_menu += [('  ', 'empty'), ('  ', 'empty'), (plugin_addon.getLocalizedString(30147), 'empty')]
        return context_menu


class ImportFolders(object):
    def __init__(self):
        self.items = []
        self.size = 0

        json_node = self.get_full_object()
        if json_node is not None:
            self.process_children(json_node)

    def process_children(self, json_node):
        for i in json_node:
            try:
                self.items.append(ImportFolder(i))
            except:
                pass
        self.size = len(self.items)

    def get_full_object(self):
        url = self.get_api_url()
        json_body = pyproxy.get_json(url)
        if json_body is None:
            return None
        json_node = json.loads(json_body)
        return json_node

    def get_api_url(self):
        url = self.base_url()
        return url

    def base_url(self):
        return server + '/api/' + self.url_prefix()

    def url_prefix(self):
        return 'folder/list'


class Queue(object):
    def __init__(self, role):
        self.count = 0
        self.isrunning = False
        self.state = ''

        self.role = role

        json_node = self.get_full_object()
        if json_node is not None:
            self.process(json_node)

    def process(self, json_node):
        self.count = int(json_node.get('count', 0))
        self.isrunning = True if str(json_node.get('isrunning', 'False')) == 'True' else False
        self.state = json_node.get('state', 'Idle')

    def get_full_object(self):
        url = self.get_api_url()
        json_body = pyproxy.get_json(url)
        if json_body is None:
            return None
        json_node = json.loads(json_body)
        return json_node

    def get_api_url(self):
        url = self.base_url()
        return url

    def base_url(self):
        return server + '/api/' + self.url_prefix()

    def url_prefix(self):
        return 'queue/%s/get' % self.role

    def pause(self):
        url = server + '/api/queue/%s/stop' % self.role
        pyproxy.get_json(url)
        self.isrunning = False

    def start(self):
        url = server + '/api/queue/%s/start' % self.role
        pyproxy.get_json(url)
        self.isrunning = True

    def clear(self):
        url = server + '/api/queue/%s/clear' % self.role
        pyproxy.get_json(url)

    def get_context_menu_items(self):
        context_menu = []
        if self.isrunning:
            context_menu += [(localize(30220), script_utils.url_command_queue(self.role, 'stop'))]
        else:
            context_menu += [(localize(30219), script_utils.url_command_queue(self.role, 'start'))]
        context_menu += [(localize(30228), script_utils.url_command_queue(self.role, 'clear'))]
        return context_menu

    def get_infolabels(self):
        return {'Title': self.role, 'Plot': self.state}

    def get_listitem(self):
        url = ''  # self.get_plugin_url()
        li = ListItem(self.get_name(), path=url)
        li.setPath(url)
        infolabels = self.get_infolabels()
        li.setInfo(type='video', infoLabels=infolabels)

        context = self.get_context_menu_items()
        if context is not None and len(context) > 0:
            li.addContextMenuItems(context)
        return li

    def get_name(self):
        color = 'red'
        if self.isrunning:
            color = "green"
        name = '[COLOR %s]%s[/COLOR] %s' % (color, self.role, self.count if self.count > 0 else '')
        return name


class QueueHasher(Queue):
    def __init__(self):
        Queue.__init__(self, 'hasher')


class QueueImages(Queue):
    def __init__(self):
        Queue.__init__(self, 'images')


class QueueGeneral(Queue):
    def __init__(self):
        Queue.__init__(self, 'general')


def convert_units(input):
    size = int(input)
    # 2**10 = 1024
    power = 2 ** 10
    n = 0
    power_labels = {0: '', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti', 5: 'Pi', 6: 'Ei', 7: 'Zi', 8: 'Yi'}
    while size > power:
        size /= power
        n += 1
    return size, power_labels[n] + 'B'




