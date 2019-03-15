# -*- coding: utf-8 -*-
from nakamori_utils import model_utils


def get_infolabels_for_group(group):
    cast, roles = model_utils.convert_cast_and_role_to_legacy(group.actors)
    infolabels = {
        'aired': group.date,
        'date': model_utils.get_date(group.date),
        'genre': group.tags,
        'plot': group.overview,
        'premiered': group.date,
        'rating': group.rating,
        'title': group.name,
        'userrating': group.user_rating,
        'path': group.get_plugin_url(),
        'cast': cast,
        'castandrole': roles,
        'mediatype': 'tvshow',
    }

    return infolabels


def get_infolabels_for_series(series):
    cast, roles = model_utils.convert_cast_and_role_to_legacy(series.actors)
    infolabels = {
        'aired': series.date,
        'date': model_utils.get_date(series.date),
        'originaltitle': series.alternate_name,
        'genre': series.tags,
        'plot': series.overview,
        'premiered': series.date,
        'rating': series.rating,
        'season': series.season,
        'title': series.name,
        'userrating': series.user_rating,
        'path': series.get_plugin_url(),
        'cast': cast,
        'castandrole': roles,
        'mediatype': 'tvshow',
    }

    return infolabels


def get_infolabels_for_series_type(series):
    infolabels = {
        'aired': series.date,
        'date': model_utils.get_date(series.date),
        'originaltitle': series.alternate_name,
        'genre': series.tags,
        'plot': series.overview,
        'premiered': series.date,
        'rating': series.rating,
        'season': series.season,
        'title': series.episode_type,
        'userrating': series.user_rating,
        'path': series.get_plugin_url(),
        'mediatype': 'tvshow',
    }

    return infolabels


def get_infolabels_for_episode(episode):
    cast, roles = model_utils.convert_cast_and_role_to_legacy(episode.actors)
    infolabels = {
        'aired': episode.date,
        'date': model_utils.get_date(episode.date),
        'episode': episode.episode_number,
        'originaltitle': episode.alternate_name,
        'plot': episode.overview,
        'premiered': episode.date,
        'rating': episode.rating,
        'season': episode.season,
        'title': episode.name,
        'sorttitle': model_utils.get_sort_name(episode),
        'userrating': episode.user_rating,
        'votes': episode.votes,
        'path': episode.get_plugin_url(),
        'cast': cast,
        'castandrole': roles,
        'tvshowtitle': episode.series_name,
        'mediatype': 'episode',
    }

    file = episode.items[0] if len(episode.items) > 0 else None  # type: File
    if file is not None:
        more_infolabels = {
            'duration': file.duration,
            'size': file.size,
            'dateadded': file.date_added
        }
        for key in more_infolabels:
            infolabels[key] = more_infolabels[key]
    return infolabels


def get_infolabels_for_file(f):

    infolabels = {
        'path': f.get_plugin_url(),
        'mediatype': 'episode',
        'duration': f.duration,
        'size': f.size,
        'dateadded': f.date_added
    }
    return infolabels
