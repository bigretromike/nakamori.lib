#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import time

from abc import abstractmethod
import error_handler as eh
import nakamori_utils.model_utils
import xbmcplugin

try:
    import nakamoriplugin
    # This puts a dependency on plugin, which is a no no. It'll need to be replaced later
    puf = nakamoriplugin.routing_plugin.url_for
except:
    import sys
    if len(sys.argv) > 2:
        eh.exception(eh.ErrorPriority.BLOCKING)

from kodi_models import ListItem, WatchedStatus
from nakamori_utils.globalvars import *
from nakamori_utils import infolabel_utils, kodi_utils, shoko_utils, script_utils
from nakamori_utils import model_utils


from proxy.kodi_version_proxy import kodi_proxy
from proxy.python_version_proxy import python_proxy as pyproxy

# TODO Context menu handlers


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
        self.IsKodiFolder = True
        self.name = None
        self.items = []
        self.fanart = ''
        self.poster = ''
        self.banner = ''
        self.size = -1
        self.get_children = get_children
        self.sort_index = 0
        self.sizes = None
        if isinstance(json_node, (str, int, unicode)):
            self.id = json_node
            return

        self.id = json_node.get('id', 0)
        self.name = model_utils.get_title(json_node)
        self.size = int(json_node.get('size', '0'))

        self.process_art(json_node)

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

    def get_full_object(self):
        url = self.get_api_url()
        json_body = pyproxy.get_json(url)
        json_node = json.loads(json_body)
        return json_node

    def process_art(self, json_node):
        thumb = ''
        fanart = ''
        banner = ''
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
        except:
            pass
        self.fanart = fanart
        self.poster = thumb
        self.banner = banner

    def process_children(self, json_node):
        pass

    def set_watched_status(self, watched):
        if isinstance(watched, str) or isinstance(watched, unicode):
            watched = watched.lower() != 'false'

        url = self.base_url()
        url += '/watch' if watched else '/unwatch'
        url = pyproxy.set_parameter(url, 'id', self.id)
        if plugin_addon.getSetting('syncwatched') == 'true':
            pyproxy.get_json(url)
        else:
            xbmc.executebuiltin('XBMC.Action(ToggleWatched)')

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
        li = ListItem(self.name, path=url)
        li.setPath(url)
        li.setInfo(type='video', infoLabels={'Title': self.name, 'Plot': self.name})
        li.set_art(self)
        return li

    def get_context_menu_items(self):
        context_menu = [('  ', 'empty'), (plugin_addon.getLocalizedString(30147), 'empty'),
                        (plugin_addon.getLocalizedString(30148), 'empty')]
        return context_menu

    def __iter__(self):
        for i in self.items:
            yield i

    def apply_sorting(self, handle):
        pass

    def is_watched(self):
        local_only = plugin_addon.getSetting('local_total') == 'true'
        no_specials = kodi_utils.get_kodi_setting_bool('ignore_specials_watched')
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
        no_specials = kodi_utils.get_kodi_setting_bool('ignore_specials_watched')
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
        no_specials = kodi_utils.get_kodi_setting_bool('ignore_specials_watched')
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
        if not kodi_utils.get_kodi_setting_bool('videolibrary.showunwatchedplots')\
                or plugin_addon.getSetting('hide_plot') == 'true':
            infolabels['plot'] = localize(30079)


class CustomItem(Directory):
    def __init__(self, name, image, plugin_url, sort_index, is_folder=True):
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
        self.name = name
        self.plugin_url = plugin_url
        self.image = image
        self.IsKodiFolder = is_folder
        self.apply_image_override(image)

        self.size = 0
        self.sort_index = sort_index
        self.directory_filter = False

    def get_api_url(self):
        return None

    def url_prefix(self):
        return None

    def get_plugin_url(self):
        """
        :type: str
        """
        return self.plugin_url

    def get_context_menu_items(self):
        pass

    def set_watched_status(self, watched):
        pass


# noinspection Duplicates
class Filter(Directory):
    """
    A filter object, contains a unified method of representing a filter, with convenient converters
    """
    def __init__(self, json_node, build_full_object=False, get_children=False):
        """
        Create a filter object from a json node, containing everything that is relevant to a ListItem.
        You can also pass an ID for a small helper object.
        :param json_node: the json response from things like api/filter
        :type json_node: Union[list,dict]
        """
        Directory.__init__(self, json_node, get_children)
        # we are making this overrideable for Unsorted and such
        self.plugin_url = 'plugin://plugin.video.nakamori/menu/filter/%s' % self.id
        self.directory_filter = False

        if build_full_object:
            # don't redownload info on an okay object
            if self.size < 0:
                # First, download basic info
                json_node = self.get_full_object()
                self.plugin_url = 'plugin://plugin.video.nakamori/menu/filter/%s' % self.id
                Directory.__init__(self, json_node, get_children)
                self.directory_filter = json_node.get('type', 'filter') == 'filters'
            # then download children, optimized for type
            if get_children and len(self.items) < 1:
                json_node = self.get_full_object()

        # check again, as we might have replaced it above
        if isinstance(json_node, (str, int, unicode)):
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
        url = nakamori_utils.model_utils.add_default_parameters(url, self.id, level)
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
            self.plugin_url = puf(nakamoriplugin.show_unsorted_menu)

    def process_children(self, json_node):
        items = json_node.get('filters', [])
        for i in items:
            try:
                self.items.append(Filter(i, build_full_object=True))
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
        group = Group(json_node, build_full_object=True, filter_id=self.id)
        if group.size == 1:
            if len(group.items) == 1 and group.items[0] is not None:
                group = group.items[0]
                if group.size < 0:
                    group = Series(group.id, True)
            else:
                group = Group(json_node, build_full_object=True, filter_id=self.id)
                group = group.items[0]
                if group.size < 0:
                    group = Series(group.id, build_full_object=True)
        return group

    def get_context_menu_items(self):
        pass

    def set_watched_status(self, watched):
        pass

    def apply_sorting(self, handle):
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_TITLE_IGNORE_THE)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_DATE)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_VIDEO_RATING)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_VIDEO_USER_RATING)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)

        sorting_setting = plugin_addon.getSetting('default_sort_filter')
        kodi_utils.set_user_sort_method(sorting_setting)


# noinspection Duplicates
class Group(Directory):
    """
    A group object, contains a unified method of representing a group, with convenient converters
    """
    def __init__(self, json_node, build_full_object=False, get_children=False, filter_id=0):
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
        # don't redownload info on an okay object
        if build_full_object and (self.size < 0 or (get_children and len(self.items) < 1)):
            json_node = self.get_full_object()
            Directory.__init__(self, json_node, get_children)
        if filter_id != 0 and filter_id != '0':
            self.filter_id = filter_id

        # check again, as we might have replaced it above
        if isinstance(json_node, (str, int, unicode)):
            eh.spam(self)
            return

        self.date = model_utils.get_airdate(json_node)
        self.rating = float(str(json_node.get('rating', '0')).replace(',', '.'))
        self.user_rating = float(str(json_node.get('userrating', '0')).replace(',', '.'))
        self.votes = pyproxy.safe_int(json_node.get('votes', 0))
        self.actors = model_utils.get_cast_info(json_node)
        self.sizes = get_sizes(json_node)
        self.tags = model_utils.get_tags(json_node.get('tags', {}))
        self.overview = model_utils.remove_anidb_links(pyproxy.decode(json_node.get('summary', '')))

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
        return puf(nakamoriplugin.show_group_menu, self.id, self.filter_id)

    def get_listitem(self):
        """

        :return:
        :rtype: ListItem
        """
        url = self.get_plugin_url()
        li = ListItem(self.name, path=url)
        infolabels = infolabel_utils.get_infolabels_for_group(self)
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

    def process_children(self, json_node):
        items = json_node.get('series', [])
        for i in items:
            try:
                self.items.append(Series(i, build_full_object=True))
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

    def apply_sorting(self, handle):
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_TITLE_IGNORE_THE)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_DATE)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_VIDEO_RATING)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_VIDEO_USER_RATING)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)

        sorting_setting = plugin_addon.getSetting('default_sort_filter')
        kodi_utils.set_user_sort_method(sorting_setting)


# noinspection Duplicates
class Series(Directory):
    """
    A series object, contains a unified method of representing a series, with convenient converters
    """
    def __init__(self, json_node, build_full_object=False, get_children=False):
        """
        Create a series object from a json node, containing everything that is relevant to a ListItem
        :param json_node: the json response from things like api/serie
        :type json_node: Union[list,dict]
        """
        Directory.__init__(self, json_node, get_children)
        # don't redownload info on an okay object
        if build_full_object and (self.size < 0 or (get_children and len(self.items) < 1)):
            json_node = self.get_full_object()
            Directory.__init__(self, json_node, get_children)
        self.episode_types = []
        # check again, as we might have replaced it above
        if isinstance(json_node, (str, int, unicode)):
            eh.spam(self)
            return

        self.alternate_name = model_utils.get_title(json_node, 'en', 'official')
        self.overview = model_utils.remove_anidb_links(pyproxy.decode(json_node.get('summary', '')))

        self.anidb_id = pyproxy.safe_int(json_node.get('aid', 0))
        self.season = json_node.get('season', '1')
        self.date = model_utils.get_airdate(json_node)
        self.rating = float(str(json_node.get('rating', '0')).replace(',', '.'))
        self.user_rating = float(str(json_node.get('userrating', '0')).replace(',', '.'))
        self.votes = pyproxy.safe_int(json_node.get('votes', 0))
        self.actors = model_utils.get_cast_info(json_node)
        self.sizes = get_sizes(json_node)
        self.tags = model_utils.get_tags(json_node.get('tags', {}))
        self.is_movie = json_node.get('ismovie', 0) == 1
        self.process_children(json_node)

        eh.spam(self)

    def get_api_url(self):
        url = self.base_url()
        url = nakamori_utils.model_utils.add_default_parameters(url, self.id, 2 if self.get_children else 0)
        return url

    def url_prefix(self):
        return 'serie'

    def get_plugin_url(self):
        return puf(nakamoriplugin.show_series_menu, self.id)

    def get_listitem(self):
        """

        :return:
        :rtype: ListItem
        """
        url = self.get_plugin_url()

        # We need to assume not airing, as there is no end date provided in API
        name = model_utils.title_coloring(self.name, self.sizes.local_episodes, self.sizes.total_episodes,
                                          self.sizes.local_specials, self.sizes.total_specials, False)

        li = ListItem(name, path=url)
        infolabels = infolabel_utils.get_infolabels_for_series(self)
        li.setPath(url)
        li.set_watched_flags(infolabels, self.is_watched(), 1)

        li.setUniqueIDs({'anidb': self.anidb_id})
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
            self.episode_types.append(SeriesTypeList(self.id, i))

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

        # TODO Things to add: View Cast, Play All, Related, Similar

        return context_menu

    def vote(self, value):
        Directory.vote(self, value)
        xbmc.executebuiltin('XBMC.Notification(%s, %s %s, 7500, %s)' % (script_addon.getLocalizedString(30021),
                                                                        script_addon.getLocalizedString(30022),
                                                                        str(value), plugin_addon.getAddonInfo('icon')))

    def apply_sorting(self, handle):
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_EPISODE)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_TITLE_IGNORE_THE)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_DATE)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_VIDEO_RATING)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_VIDEO_USER_RATING)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)

        sorting_setting = plugin_addon.getSetting('default_sort_episodes')
        kodi_utils.set_user_sort_method(sorting_setting)


# noinspection Duplicates
class SeriesTypeList(Series):
    """
    The Episode Type List for a series
    """
    def __init__(self, json_node, episode_type):
        Directory.__init__(self, json_node, True)
        self.episode_type = episode_type
        json_node = self.get_full_object()
        Series.__init__(self, json_node)

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
        return puf(nakamoriplugin.show_series_episode_types_menu, self.id, self.episode_type)

    def apply_sorting(self, handle):
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_EPISODE)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_TITLE_IGNORE_THE)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_DATE)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_VIDEO_RATING)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_VIDEO_USER_RATING)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)

        sorting_setting = plugin_addon.getSetting('default_sort_episodes')
        kodi_utils.set_user_sort_method(sorting_setting)

    def get_listitem(self):
        """

        :return:
        :rtype: ListItem
        """
        url = self.get_plugin_url()

        li = ListItem(self.episode_type, path=url)
        infolabels = infolabel_utils.get_infolabels_for_series_type(self)
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
        self.series_anidb_id = 0
        self.actors = []
        if series is not None:
            self.series_id = series.id
            self.series_name = series.name
            self.actors = series.actors
            self.series_anidb_id = series.anidb_id

        Directory.__init__(self, json_node, True)
        # don't redownload info on an okay object
        if build_full_object and self.size < 0:
            json_node = self.get_full_object()
            Directory.__init__(self, json_node)
        # check again, as we might have replaced it above
        if isinstance(json_node, (str, int, unicode)):
            eh.spam(self)
            return

        self.episode_number = pyproxy.safe_int(json_node.get('epnumber', ''))
        self.episode_type = json_node.get('eptype', 'Other')
        self.date = model_utils.get_airdate(json_node)
        self.tvdb_episode = json_node.get('season', '0x0')

        self.process_children(json_node)

        if self.name is None:
            self.name = 'Episode ' + str(json_node.get('epnumber', '??'))
        self.alternate_name = model_utils.get_title(json_node, 'x-jat', 'main')

        self.watched = pyproxy.safe_int(json_node.get('view', 0)) != 0
        self.year = pyproxy.safe_int(json_node.get('year', ''))

        self.rating = float(str(json_node.get('rating', '0')).replace(',', '.'))
        self.user_rating = float(str(json_node.get('UserRating', '0')).replace(',', '.'))
        self.overview = model_utils.remove_anidb_links(pyproxy.decode(json_node.get('summary', '')))
        self.votes = pyproxy.safe_int(json_node.get('votes', ''))

        if str(json_node['eptype']) != 'Special':
            season = str(json_node.get('season', '1'))
            if 'x' in season:
                season = season.split('x')[0]
                if season == '0':
                    season = '1'
        else:
            season = '0'
        self.season = pyproxy.safe_int(season)

        eh.spam(self)

    def get_file(self):
        """
        :return: the first file in the list, or None if not populated
        :rtype: File
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

    def get_plugin_url(self):
        return puf(nakamoriplugin.play_video, self.id, self.get_file().id)

    def is_watched(self):
        if self.watched:
            return WatchedStatus.WATCHED
        f = self.get_file()
        if f is not None and f.resume_time > 0:
            return WatchedStatus.PARTIAL
        return WatchedStatus.UNWATCHED

    def get_listitem(self):
        """

        :return:
        :rtype: ListItem
        """
        url = self.get_plugin_url()
        li = ListItem(self.name, path=url)
        li.setPath(url)
        infolabels = infolabel_utils.get_infolabels_for_episode(self)

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
        f = self.get_file()
        if f is not None:
            model_utils.set_stream_info(li, f)
        li.addContextMenuItems(self.get_context_menu_items())

        return li

    def process_children(self, json_node):
        for _file in json_node.get('files', []):
            try:
                self.items.append(File(_file, True))
            except:
                pass

    def get_context_menu_items(self):
        # Calls to Plugin from Context Menus need 'RunPlugin(%s)' %
        context_menu = []
        # Play
        if plugin_addon.getSetting('context_show_play') == 'true':
            context_menu.append((localize(30065), 'Action(Select)'))

        # Resume
        if self.get_file() is not None and self.get_file().resume_time > 0 \
                and plugin_addon.getSetting('file_resume') == 'true':
            label = localize(30141) + ' (%s)' % time.strftime('%H:%M:%S', time.gmtime(self.get_file().resume_time))
            url = 'RunPlugin(%s)' % puf(nakamoriplugin.resume_video, self.id, self.get_file().id)
            context_menu.append((label, url))

        # Play (No Scrobble)
        if plugin_addon.getSetting('context_show_play_no_watch') == 'true':
            context_menu.append((localize(30132), 'RunPlugin(%s)' % puf(nakamoriplugin.play_video_without_marking,
                                                                        self.id, self.get_file().id)))

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
            context_menu.append((localize(30130), 'TO BE ADDED TO SCRIPT'))

        # Vote Episode
        if plugin_addon.getSetting('context_show_vote_Episode') == 'true':
            context_menu.append((localize(30125), script_utils.url_show_episode_vote_dialog(self.id)))

        # Vote Series
        if plugin_addon.getSetting('context_show_vote_Series') == 'true' and self.series_id != 0:
            context_menu.append((localize(30124), script_utils.url_show_series_vote_dialog(self.series_id)))

        # Metadata
        if plugin_addon.getSetting('context_show_info') == 'true':
            context_menu.append((localize(30123), 'Action(Info)'))

        # View Cast
        if plugin_addon.getSetting('context_view_cast') == 'true' and self.series_id != 0:
            # context_menu.append((localize(30134), 'RunPlugin(%s&cmd=viewCast)'))
            pass

        # Refresh
        if plugin_addon.getSetting('context_refresh') == 'true':
            context_menu.append((localize(30131), 'Container.Refresh'))

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
            infolabels['title'] = localize(30076) + str(self.episode_number)
        elif self.episode_type == 'Episode':
            if plugin_addon.getSetting('hide_title') == 'Specials':  # both,episodes
                return
            infolabels['title'] = localize(30076) + str(self.episode_number)

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
        if isinstance(json_node, (str, int, unicode)):
            eh.spam(self)
            return

        self.name = pyproxy.decode(json_node.get('filename', 'None'))
        self.name = os.path.split(self.name)[-1]
        self.resume_time = int(int(json_node.get('offset', '0')) / 1000)

        # Check for empty duration from MediaInfo check fail and handle it properly
        duration = json_node.get('duration', 1) / 1000
        if duration != 1:
            duration = kodi_proxy.duration(duration)
        self.duration = duration

        self.size = pyproxy.safe_int(json_node.get('size', 0))
        self.file_url = json_node.get('url', '')
        self.server_path = json_node.get('server_path', '')

        self.date_added = pyproxy.decode(json_node.get('created', '')).replace('T', ' ')

        try:
            # Information about streams inside json_node file
            if len(json_node.get('media', {})) > 0:
                self.video_streams = model_utils.get_video_streams(json_node['media'])
                self.audio_streams = model_utils.get_audio_streams(json_node['media'])
                self.sub_streams = model_utils.get_sub_streams(json_node['media'])
            else:
                self.video_streams = {}
                self.audio_streams = {}
                self.sub_streams = {}
        except Exception:
            self.video_streams = {}
            self.audio_streams = {}
            self.sub_streams = {}

        eh.spam(self)

    def get_api_url(self):
        url = self.base_url()
        url = nakamori_utils.model_utils.add_default_parameters(url, self.id, 1)
        return url

    def url_prefix(self):
        return 'file'

    def get_plugin_url(self):
        return puf(nakamoriplugin.play_video_without_marking, 0, self.id)

    @property
    def url_for_player(self):
        if os.path.isfile(self.server_path):
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
        li.setInfo(type='video', infoLabels={'Title': self.name, 'Plot': self.name})

        # Files don't have watched states in the API, so this is all that's needed
        if self.resume_time > 0 and plugin_addon.getSetting('file_resume') == 'true':
            li.setProperty('ResumeTime', str(self.resume_time))

        model_utils.set_stream_info(li, self)
        li.set_art(self)
        li.addContextMenuItems(self.get_context_menu_items())
        return li

    def get_context_menu_items(self):
        context_menu = [
            (localize(30120), script_utils.url_rescan_file(self.id)),
            (localize(30121), script_utils.url_rehash_file(self.id))
        ]
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
        offset_body = '"id":%i,"offset":%i' % (self.id, current_time * 1000)
        pyproxy.post_json(offset_url, offset_body)
        
    def rehash(self):
        shoko_utils.rehash_file(self.id)

    def rescan(self):
        shoko_utils.rescan_file(self.id)


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


@eh.try_function(eh.ErrorPriority.NORMAL)
def get_series_for_episode(ep_id):
    url = server + '/api/serie/fromep'
    url = nakamori_utils.model_utils.add_default_parameters(url, ep_id, 0)
    json_body = pyproxy.get_json(url)
    json_node = json.loads(json_body)
    return Series(json_node)
