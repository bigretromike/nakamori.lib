# -*- coding: utf-8 -*-
from nakamori_utils import model_utils


def get_infolabels_for_group(group):
    infolabels = {}

    return infolabels


def get_infolabels_for_series(series):
    infolabels = {}

    return infolabels


def get_infolabels_for_episode(episode):

    infolabels = {
        "aired": episode.date,
        "date": model_utils.get_date(episode.date),
        "episode": episode.episode_number,
        "originaltitle": episode.alternate_name,
        "plot": episode.overview,
        "premiered": episode.date,
        "rating": episode.rating,
        "season": episode.season,
        "title": episode.name,
        "sorttitle": model_utils.get_sort_name(episode),
        "userrating": episode.user_rating,
        "votes": episode.votes,
        "mediatype": "episode",
    }

    file = episode.items[0] if len(episode.items) > 0 else None  # type: File
    if file is not None:
        more_infolabels = {
            "duration": file.duration,
            "size": file.size,
            "dateadded": file.date_added
        }
        for key in more_infolabels:
            infolabels[key] = more_infolabels[key]
    return infolabels
