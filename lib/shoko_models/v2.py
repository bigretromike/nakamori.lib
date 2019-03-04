#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import os
import time

from abc import abstractmethod

import nakamoriplugin
from kodi_models.kodi_models import ListItem, WatchedStatus
from nakamori_utils.globalvars import *
from nakamori_utils import nakamoritools as nt, infolabel_utils
from nakamori_utils import model_utils

from proxy.kodi_version_proxy import kodi_proxy
from proxy.python_version_proxy import python_proxy as pyproxy

# TODO Context menu handlers
# TODO better listitem info for series and groups
# TODO stream info
# TODO playing files


localize = plugin_addon.getLocalizedString
url_for = nakamoriplugin.routing_plugin.url_for


# noinspection Duplicates
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
        self.name = None
        self.items = []
        self.fanart = ''
        self.poster = ''
        self.banner = ''
        self.size = -1
        self.get_children = get_children
        self.sort_index = 0
        if isinstance(json_node, (str, int, unicode)):
            self.id = json_node
            return

        self.id = json_node.get('id', 0)
        self.name = model_utils.get_title(json_node)
        self.size = int(json_node.get('size', '0'))

        self.process_art(json_node)

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
        json_body = nt.get_json(url)
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
            nt.get_json(url)
        else:
            xbmc.executebuiltin('XBMC.Action(ToggleWatched)')

        if plugin_addon.getSetting('watchedbox') == 'true':
            msg = localize(30201) + ' ' + (localize(30202) if watched else localize(30203))
            xbmc.executebuiltin('XBMC.Notification(' + localize(30200) + ', ' + msg + ', 2000, ' +
                                plugin_addon.getAddonInfo('icon') + ')')
        nt.refresh()

    @abstractmethod
    def get_listitem(self):
        """
        This creates a ListItem based on the model.
        :return:
        """
        pass

    def get_context_menu_items(self):
        context_menu = [('  ', 'empty'), (plugin_addon.getLocalizedString(30147), 'empty'),
                        (plugin_addon.getLocalizedString(30148), 'empty')]
        return context_menu

    def __iter__(self):
        for i in self.items:
            yield i


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
        # we are making this overrideable for Unsorted and such

        Directory.__init__(self, json_node, get_children)
        self.plugin_url = self.get_plugin_url()
        # don't redownload info on an okay object
        if build_full_object and (self.size < 0 or get_children):
            json_node = self.get_full_object()
            Directory.__init__(self, json_node, get_children)

        # check again, as we might have replaced it above
        if isinstance(json_node, (str, int, unicode)):
            return

        self.size = int(json_node.get('size', '0'))
        self.directory_filter = json_node.get('type', 'filter') == 'filters'

        self.apply_built_in_overrides()
        if get_children:
            self.process_children(json_node)

    def get_api_url(self):
        url = self.base_url()
        url = nt.add_default_parameters(url, self.id, 1 if self.get_children else 0)
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
        return url_for(nakamoriplugin.show_filter_menu, self.id)

    def apply_built_in_overrides(self):
        # {'Airing Today': 0, 'Calendar': 1, 'Seasons': 2, 'Years': 3, 'Tags': 4, 'Unsort': 5}
        if self.name == 'Continue Watching (SYSTEM)':
            self.name = 'Continue Watching'
        elif self.name == 'Seasons':
            self.sort_index = 3
        elif self.name == 'Years':
            self.sort_index = 4
        elif self.name == 'Tags':
            self.sort_index = 5
        elif self.name == 'Unsort':
            self.name = 'Unsorted Files'
            self.sort_index = 6
            self.plugin_url = url_for(nakamoriplugin.show_unsorted_menu)

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
                group = Group(json_node, build_full_object=True, get_children=True, filter_id=self.id)
                group = group.items[0]
                if group.size < 0:
                    group = Series(group.id, build_full_object=True)
        return group

    def get_listitem(self):
        url = self.plugin_url
        li = ListItem(self.name, path=url)
        li.setPath(url)
        li.setInfo(type='video', infoLabels={'Title': self.name, 'Plot': self.name})
        li.set_art(self)
        return li

    def get_context_menu_items(self):
        pass

    def set_watched_status(self, watched):
        pass


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
        if build_full_object and (self.size < 0 or get_children):
            json_node = self.get_full_object()
            Directory.__init__(self, json_node, get_children)
        if filter_id != 0 and filter_id != '0':
            self.filter_id = filter_id

        # check again, as we might have replaced it above
        if isinstance(json_node, (str, int, unicode)):
            return

        self.date = model_utils.get_airdate(json_node)
        self.rating = float(str(json_node.get('rating', '0')).replace(',', '.'))
        self.user_rating = float(str(json_node.get('userrating', '0')).replace(',', '.'))
        self.actors = model_utils.get_cast_info(json_node)
        self.sizes = get_sizes(json_node)
        self.tags = model_utils.get_tags(json_node.get('tags', {}))
        self.overview = pyproxy.decode(json_node.get('summary', ''))

        if get_children:
            self.process_children(json_node)

    def get_api_url(self):
        url = self.base_url()
        url = nt.add_default_parameters(url, self.id, 1 if self.get_children else 0)
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
        return url_for(nakamoriplugin.show_group_menu, self.id, self.filter_id)

    def get_listitem(self):
        url = self.get_plugin_url()
        li = ListItem(self.name, path=url)
        infolabels = infolabel_utils.get_infolabels_for_group(self)
        li.setPath(url)
        li.set_watched_flags(infolabels, is_watched(self), 1)
        li.setInfo(type='video', infoLabels=infolabels)
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
        pass


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
        if build_full_object and (self.size < 0 or get_children):
            json_node = self.get_full_object()
            Directory.__init__(self, json_node, get_children)
        self.episode_types = []
        # check again, as we might have replaced it above
        if isinstance(json_node, (str, int, unicode)):
            return

        self.alternate_name = model_utils.get_title(json_node, 'en', 'official')
        self.overview = pyproxy.decode(json_node.get('summary', ''))

        self.season = json_node.get('season', '1')
        self.date = model_utils.get_airdate(json_node)
        self.rating = float(str(json_node.get('rating', '0')).replace(',', '.'))
        self.user_rating = float(str(json_node.get('userrating', '0')).replace(',', '.'))
        self.actors = model_utils.get_cast_info(json_node)
        self.sizes = get_sizes(json_node)
        self.tags = model_utils.get_tags(json_node.get('tags', {}))
        if get_children:
            self.process_children(json_node)

    def get_api_url(self):
        url = self.base_url()
        url = nt.add_default_parameters(url, self.id, 2 if self.get_children else 0)
        return url

    def url_prefix(self):
        return 'serie'

    def get_plugin_url(self):
        return url_for(nakamoriplugin.show_series_menu, self.id)

    def get_listitem(self):
        url = self.get_plugin_url()
        li = ListItem(self.name, path=url)
        infolabels = infolabel_utils.get_infolabels_for_series(self)
        li.setPath(url)
        li.set_watched_flags(infolabels, is_watched(self), 1)
        li.setInfo(type='video', infoLabels=infolabels)
        li.set_art(self)
        return li

    def process_children(self, json_node):
        items = json_node.get('eps', [])
        episode_types = []
        for i in items:
            try:
                episode = Episode(i, build_full_object=True)
                self.items.append(episode)
                if episode.episode_type not in episode_types:
                    episode_types.append(episode.episode_type)
            except:
                pass
        for i in episode_types:
            self.episode_types.append(SeriesTypeList(self.id, i))

    def get_context_menu_items(self):
        pass


# noinspection Duplicates
class SeriesTypeList(Series):
    """
    The Episode Type List for a series
    """
    def __init__(self, json_node, episode_type):
        Directory.__init__(self, json_node, True)
        json_node = self.get_full_object()
        self.name = episode_type

        items = json_node.get('eps', [])
        for i in items:
            try:
                episode = Episode(i)
                if episode.episode_type != episode_type:
                    continue
                self.items.append(episode)
            except:
                pass

    def get_plugin_url(self):
        return url_for(nakamoriplugin.show_series_episode_types_menu, self.id, self.name)


# noinspection Duplicates
class Episode(Directory):
    """
    An episode object, contains a unified method of representing an episode, with convenient converters
    """
    def __init__(self, json_node, series_id=0, build_full_object=False):
        """
        Create an episode object from a json node, containing everything that is relevant to a ListItem
        :param json_node: the json response from things like api/serie.eps[]
        :type json_node: Union[list,dict]
        """
        self.series_id = series_id
        Directory.__init__(self, json_node, True)
        # don't redownload info on an okay object
        if build_full_object and self.size < 0:
            json_node = self.get_full_object()
            Directory.__init__(self, json_node)
        # check again, as we might have replaced it above
        if isinstance(json_node, (str, int, unicode)):
            return

        self.episode_number = nt.safe_int(json_node.get('epnumber', ''))
        self.episode_type = json_node.get('eptype', 'Other')
        self.date = model_utils.get_airdate(json_node)
        self.tvdb_episode = json_node.get('season', '0x0')

        self.process_children(json_node)

        if self.name is None:
            self.name = 'Episode ' + str(json_node.get('epnumber', '??'))
        self.alternate_name = model_utils.get_title(json_node, 'x-jat', 'main')

        self.watched = nt.safe_int(json_node.get('view', 0)) != 0
        self.year = nt.safe_int(json_node.get('year', ''))

        self.rating = float(str(json_node.get('rating', '0')).replace(',', '.'))
        self.user_rating = float(str(json_node.get('UserRating', '0')).replace(',', '.'))
        self.overview = nt.remove_anidb_links(pyproxy.decode(json_node.get('summary', '')))
        self.votes = nt.safe_int(json_node.get('votes', ''))

        if str(json_node['eptype']) != 'Special':
            season = str(json_node.get('season', '1'))
            if 'x' in season:
                season = season.split('x')[0]
                if season == '0':
                    season = '1'
        else:
            season = '0'
        self.season = nt.safe_int(season)

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
        url = nt.add_default_parameters(url, self.id, 1)
        return url

    def url_prefix(self):
        return 'ep'

    def get_plugin_url(self):
        return url_for(nakamoriplugin.play_video, self.id, self.get_file().id)

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
        elif not self.watched:
            li.set_watched_flags(infolabels, WatchedStatus.UNWATCHED)
        elif self.get_file() is not None and self.get_file().resume_time > 0:
            li.set_watched_flags(infolabels, WatchedStatus.PARTIAL, self.get_file().resume_time)

        li.setInfo(type='video', infoLabels=infolabels)
        li.set_art(self)
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
        context_menu = []
        # Play
        if plugin_addon.getSetting('context_show_play') == 'true':
            context_menu.append((localize(30065), 'Action(Select)'))

        # Resume
        if self.get_file() is not None and self.get_file().resume_time > 0 \
                and plugin_addon.getSetting('file_resume') == 'true':
            label = localize(30141) + ' (%s)' % time.strftime('%H:%M:%S', time.gmtime(self.get_file().resume_time))
            url = RunPlugin(url_for(nakamoriplugin.resume_video, self.id, self.get_file().id))
            context_menu.append((label, url))

        # Play (No Scrobble)
        if plugin_addon.getSetting('context_show_play_no_watch') == 'true':
            context_menu.append((localize(30132), RunPlugin(url_for(nakamoriplugin.play_video_without_marking, self.get_file().id,
                                                            self.id))))

        # Inspect
        if plugin_addon.getSetting('context_pick_file') == 'true' and len(self.items) > 1:
            context_menu.append((localize(30133), 'REPLACE ME'))

        # Mark as watched/unwatched
        watched_item = (localize(30128), RunPlugin(url_for(nakamoriplugin.set_episode_watched_status, self.id, True)))
        unwatched_item = (localize(30129), RunPlugin(url_for(nakamoriplugin.set_episode_watched_status, self.id, False)))
        if plugin_addon.getSetting('context_krypton_watched') == 'true':
            if self.watched:
                context_menu.append(unwatched_item)
            else:
                context_menu.append(watched_item)
        else:
            context_menu.append(watched_item)
            context_menu.append(unwatched_item)

        # Playlist Mode
        if plugin_addon.getSetting('context_playlist') == 'true':
            context_menu.append((localize(30130), 'REPLACE ME'))

        # Vote Episode
        if plugin_addon.getSetting('context_show_vote_Episode') == 'true':
            context_menu.append((localize(30125), 'REPLACE ME'))

        # Vote Series
        if plugin_addon.getSetting('context_show_vote_Series') == 'true' and self.series_id != 0:
            context_menu.append((localize(30124), 'REPLACE ME'))

        # Metadata
        if plugin_addon.getSetting('context_show_info') == 'true':
            context_menu.append((localize(30123), 'Action(Info)'))

        if plugin_addon.getSetting('context_view_cast') == 'true' and self.series_id != 0:
            context_menu.append((localize(30134), 'RunPlugin(%s&cmd=viewCast)'))

        if plugin_addon.getSetting('context_refresh') == 'true':
            context_menu.append((localize(30131), 'REPLACE ME'))

        # the default ones that say the rest are kodi's
        context_menu += Directory.get_context_menu_items(self)

        return context_menu


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
        # don't redownload info on an okay object
        if build_full_object and self.size < 0:
            json_node = self.get_full_object()
            Directory.__init__(self, json_node)
        # check again, as we might have replaced it above
        if isinstance(json_node, (str, int, unicode)):
            return

        self.name = pyproxy.decode(json_node.get('filename', 'None'))
        self.name = os.path.split(self.name)[-1]
        self.resume_time = int(int(json_node.get('offset', '0')) / 1000)

        # Check for empty duration from MediaInfo check fail and handle it properly
        duration = json_node.get('duration', 1) / 1000
        if duration != 1:
            duration = kodi_proxy.duration(duration)
        self.duration = duration

        self.size = nt.safe_int(json_node.get('size', 0))
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

    def get_api_url(self):
        url = self.base_url()
        url = nt.add_default_parameters(url, self.id, 1)
        return url

    def url_prefix(self):
        return 'file'

    def get_plugin_url(self):
        return url_for(nakamoriplugin.play_video_without_marking, 0, self.id)

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
        return li

    def get_context_menu_items(self):
        pass

    def set_watched_status(self, watched):
        if watched:
            return
        nt.sync_offset(self.id, 0)
        # this isn't really supported atm, so no need for the rest of the stuff here


def is_watched(dir_obj):
    local_only = plugin_addon.getSetting('local_total') == 'true'
    no_specials = nt.get_kodi_setting_bool('ignore_specials_watched')
    sizes = dir_obj.sizes
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


def get_sizes(json_node):
    result = Sizes()
    local_sizes = json_node.get('local_sizes', {})
    result.local_episodes = nt.safe_int(local_sizes.get('Episodes', 0))
    result.local_specials = nt.safe_int(local_sizes.get('Specials', 0))
    result.local_total = nt.safe_int(json_node.get('localsize', 0))
    watched_sizes = json_node.get('watched_sizes', {})
    result.watched_episodes = nt.safe_int(watched_sizes.get('Episodes', 0))
    result.watched_specials = nt.safe_int(watched_sizes.get('Specials', 0))
    result.watched_total = nt.safe_int(json_node.get('watchedsize', 0))
    total_sizes = json_node.get('total_sizes', {})
    result.total_episodes = nt.safe_int(total_sizes.get('Episodes', 0))
    result.total_specials = nt.safe_int(total_sizes.get('Specials', 0))
    result.total = nt.safe_int(json_node.get('size', 0))
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


def RunPlugin(url):
    return 'RunPlugin(' + url + ')'
