#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json

from abc import abstractmethod
from collections import defaultdict

import nakamoriplugin
from kodi_models.kodi_models import ListItem
from nakamori_utils.globalvars import *
from nakamori_utils import nakamoritools as nt
from nakamori_utils import model_utils

from proxy.kodi_version_proxy import kodi_proxy
from proxy.python_version_proxy import python_proxy as pyproxy

# TODO Context menu handlers
# TODO better listitem info for series and groups
# TODO stream info
# TODO playing files


# noinspection Duplicates
class Directory(object):
    """
    A directory object, the base for Groups, Series, Episodes, etc
    """
    def __init__(self, json_node):
        """
        Create a directory object from a json node, containing only what is needed to form a ListItem.
        :param json_node: the json response from things like api/serie
        :type json_node: Union[list,dict]
        """
        if isinstance(json_node, (str, int, unicode)):
            self.id = json_node
        self.items = []
        self.fanart = ''
        self.poster = ''
        self.banner = ''
        
        # check again, as we might have replaced it above
        if isinstance(json_node, (str, int, unicode)):
            return

        self.id = json_node.get('id', 0)
        self.name = model_utils.get_title(json_node)
        self.size = json_node.get('size', 0)

        self.process_art(json_node)

        self.items = []

    @abstractmethod
    def get_api_url(self):
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
            if len(json_node["art"]["thumb"]) > 0:
                thumb = json_node["art"]["thumb"][0]["url"]
                if thumb is not None and ":" not in thumb:
                    thumb = server + thumb

            if len(json_node["art"]["fanart"]) > 0:
                fanart = json_node["art"]["fanart"][0]["url"]
                if fanart is not None and ":" not in fanart:
                    fanart = server + fanart

            if len(json_node["art"]["banner"]) > 0:
                banner = json_node["art"]["banner"][0]["url"]
                if banner is not None and ":" not in banner:
                    banner = server + banner
        except:
            pass
        self.fanart = fanart
        self.poster = thumb
        self.banner = banner

    def process_children(self, json_node):
        pass

    @abstractmethod
    def get_listitem(self):
        """
        This creates a ListItem based on the model.
        :return:
        """
        pass

    @abstractmethod
    def get_context_menu_items(self):
        pass

    def __iter__(self):
        for i in self.items:
            yield i


# noinspection Duplicates
class Filter(Directory):
    """
    A filter object, contains a unified method of representing a filter, with convenient converters
    """
    def __init__(self, json_node, build_full_object=False):
        """
        Create a filter object from a json node, containing everything that is relevant to a ListItem.
        You can also pass an ID for a small helper object.
        :param json_node: the json response from things like api/filter
        :type json_node: Union[list,dict]
        """
        Directory.__init__(self, json_node)
        if build_full_object:
            json_node = self.get_full_object()
        # check again, as we might have replaced it above
        if isinstance(json_node, (str, int, unicode)):
            return

        self.size = int(json_node.get('size', '0'))
        self.directory_filter = json_node.get('type', 'filter') == 'filters'

        self.apply_built_in_overrides()
        self.process_children(json_node)

    def get_api_url(self):
        url = self.base_url()
        url = nt.add_default_parameters(url, self.id, 1)
        return url

    def url_prefix(self):
        """
        the /api/ extension point
        :return:
        """
        return 'filter'

    def get_plugin_url(self):
        return nakamoriplugin.routing_plugin.url_for(nakamoriplugin.show_filter_menu, self.id)

    def apply_built_in_overrides(self):
        if self.name == 'Continue Watching (SYSTEM)':
            self.name = 'Continue Watching'
        elif self.name == 'Unsort':
            self.name = 'Unsorted Files'

    def process_children(self, json_node):
        items = json_node.get('filters', [])
        for i in items:
            try:
                self.items.append(Filter(i))
            except:
                pass
        items = json_node.get('groups', [])
        for i in items:
            try:
                group = Group(i)
                if len(group.items) == 1 and group.items[0] is not None:
                    group = group.items[0]
                    if group.name is None:
                        group = Series(group.id, True)
                self.items.append(group)
            except:
                pass

    def get_listitem(self):
        url = self.get_plugin_url()
        li = ListItem(self.name, path=url)
        li.setPath(url)
        li.setInfo(type="Video", infoLabels={"Title": self.name, "Plot": self.name})
        li.set_art(self)
        return li

    def get_context_menu_items(self):
        pass


# noinspection Duplicates
class Group(Directory):
    """
    A group object, contains a unified method of representing a group, with convenient converters
    """
    def __init__(self, json_node, build_full_object=False, filter_id=0):
        """
        Create a group object from a json node, containing everything that is relevant to a ListItem.
        You can also pass an ID for a small helper object.
        :param json_node: the json response from things like api/group
        :param filter_id: used to filter groups when Apply To Series is enabled for a filter
        :type json_node: Union[list,dict]
        :type filter_id: int
        """
        self.filter_id = 0
        Directory.__init__(self, json_node)
        if build_full_object:
            json_node = self.get_full_object()
        if filter_id != 0 and filter_id != '0':
            self.filter_id = filter_id

        # check again, as we might have replaced it above
        if isinstance(json_node, (str, int, unicode)):
            return

        self.actors = model_utils.get_cast_info(json_node)
        self.date = model_utils.get_date(json_node)

        self.process_children(json_node)

    def get_api_url(self):
        url = self.base_url()
        url = nt.add_default_parameters(url, self.id, 1)
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
        return nakamoriplugin.routing_plugin.url_for(nakamoriplugin.show_group_menu, self.id, self.filter_id)

    def get_listitem(self):
        url = self.get_plugin_url()
        li = ListItem(self.name, path=url)
        li.setPath(url)
        li.setInfo(type="Video", infoLabels={"Title": self.name, "Plot": self.name})
        li.set_art(self)
        return li

    def process_children(self, json_node):
        items = json_node.get('series', [])
        for i in items:
            try:
                self.items.append(Series(i))
            except:
                pass

    def get_context_menu_items(self):
        pass


# noinspection Duplicates
class Series(Directory):
    """
    A series object, contains a unified method of representing a series, with convenient converters
    """
    def __init__(self, json_node, build_full_object=False):
        """
        Create a series object from a json node, containing everything that is relevant to a ListItem
        :param json_node: the json response from things like api/serie
        :type json_node: Union[list,dict]
        """
        Directory.__init__(self, json_node)
        if build_full_object:
            json_node = self.get_full_object()
        self.episode_types = []
        # check again, as we might have replaced it above
        if isinstance(json_node, (str, int, unicode)):
            return

        self.season = json_node.get('season', '1')
        self.date = model_utils.get_date(json_node)
        self.actors = model_utils.get_cast_info(json_node)
        self.process_children(json_node)

    def get_api_url(self):
        url = self.base_url()
        url = nt.add_default_parameters(url, self.id, 2)
        return url

    def url_prefix(self):
        return 'serie'

    def get_plugin_url(self):
        return nakamoriplugin.routing_plugin.url_for(nakamoriplugin.show_series_menu, self.id)

    def get_listitem(self):
        url = self.get_plugin_url()
        li = ListItem(self.name, path=url)
        li.setPath(url)
        li.setInfo(type="Video", infoLabels={"Title": self.name, "Plot": self.name})
        li.set_art(self)
        return li

    def process_children(self, json_node):
        items = json_node.get('eps', [])
        episode_types = []
        for i in items:
            try:
                episode = Episode(i)
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
        Directory.__init__(self, json_node)
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
        return nakamoriplugin.routing_plugin.url_for(nakamoriplugin.show_series_episode_types_menu, self.id, self.name)


# noinspection Duplicates
class Episode(Directory):
    """
    An episode object, contains a unified method of representing an episode, with convenient converters
    """
    def __init__(self, json_node, build_full_object=False):
        """
        Create an episode object from a json node, containing everything that is relevant to a ListItem
        :param json_node: the json response from things like api/serie.eps[]
        :type json_node: Union[list,dict]
        """
        Directory.__init__(self, json_node)
        if build_full_object:
            json_node = self.get_full_object()
        # check again, as we might have replaced it above
        if isinstance(json_node, (str, int, unicode)):
            return

        self.episode_type = json_node.get('eptype', 'Other')
        self.date = model_utils.get_date(json_node)
        self.tvdb_episode = json_node.get('season', '0x0')

        try:
            for _file in json_node['files']:
                self.items.append(File(_file))
        except:
            pass

        if self.name is None:
            self.name = 'Episode ' + str(json_node.get('epnumber', '??'))

        self.watched = json_node.get("view", '0') != '0'
        self.year = nt.safe_int(json_node.get('year', ''))
        self.episode_number = nt.safe_int(json_node.get('epnumber', ''))
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

    def get_api_url(self):
        # this one doesn't matter much atm, but I'll prolly copy and paste for APIv3, so I'll leave it in
        url = self.base_url()
        url = nt.add_default_parameters(url, self.id, 1)
        return url

    def url_prefix(self):
        return 'ep'

    def get_plugin_url(self):
        return nakamoriplugin.routing_plugin.url_for(nakamoriplugin.show_filter_menu, self.id)

    def get_listitem(self):
        # TODO more ListItem info for files
        url = self.get_plugin_url()
        li = ListItem(self.name, path=url)
        li.setPath(url)
        li.setInfo(type="Video", infoLabels={"Title": self.name, "Plot": self.overview})
        li.set_art(self)
        return li

    def get_context_menu_items(self):
        pass


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
        if build_full_object:
            json_node = self.get_full_object()
        # check again, as we might have replaced it above
        if isinstance(json_node, (str, int, unicode)):
            return

        # Check for empty duration from MediaInfo check fail and handle it properly
        duration = json_node.get('duration', '1')
        if duration != 1:
            duration = kodi_proxy.duration(duration)

        self.size = nt.safe_int(json_node.get('size', '0'))
        self.duration = duration
        self.resume_time = int(int(json_node.get('offset', '0')) / 1000)
        self.url = json_node.get('url', '')

        video_streams = defaultdict(dict)
        audio_streams = defaultdict(dict)
        sub_streams = defaultdict(dict)

        try:
            # Information about streams inside json_node file
            if len(json_node.get("media", {})) > 0:
                self.video_streams = model_utils.get_video_streams(json_node['media'], video_streams)
                self.audio_streams = model_utils.get_audio_streams(json_node['media'], audio_streams)
                self.sub_streams = model_utils.get_sub_streams(json_node['media'], sub_streams)
        except:
            pass

    def get_api_url(self):
        url = self.base_url()
        url = nt.add_default_parameters(url, self.id, 1)
        return url

    def url_prefix(self):
        return 'file'

    def get_plugin_url(self):
        return nakamoriplugin.routing_plugin.url_for(nakamoriplugin.show_filter_menu, self.id)

    def get_listitem(self):
        """
        This should only be used as a temp object to feed to the player or it is unrecognized
        """
        url = self.get_plugin_url()
        li = ListItem(self.name, path=url)
        li.setPath(url)
        li.setInfo(type="Video", infoLabels={"Title": self.name, "Plot": self.name})
        li.set_art(self)
        return li

    def get_context_menu_items(self):
        pass

