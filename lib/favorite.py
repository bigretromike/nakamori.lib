# -*- coding: utf-8 -*-
try:
    from sqlite3 import dbapi2 as database
except:
    from pysqlite2 import dbapi2 as database

import os.path
import sys

import xbmc
import xbmcaddon
import xbmcgui


def decode_utf8(_string):
    if sys.version_info < (3, 0):
        return _string.decode('utf-8')
    else:
        return _string


ADDON_ID = 'plugin.video.nakamori'
addon = xbmcaddon.Addon(id=ADDON_ID)
profileDir = addon.getAddonInfo('profile')
profileDir = decode_utf8(xbmc.translatePath(profileDir))

# create profile dirs
if not os.path.exists(profileDir):
    os.makedirs(profileDir)

db_file = os.path.join(profileDir, 'favorite.db')

# connect to db
init_connection = database.connect(db_file)
init_cursor = init_connection.cursor()

# create table
try:
    init_cursor.execute('CREATE TABLE IF NOT EXISTS favorite (sid INTEGER NOT NULL);')
except:
    pass

# close connection
init_connection.close()


def get_all_favorites():
    items = []
    db_connection = None
    try:
        db_connection = database.connect(db_file)
        db_cursor = db_connection.cursor()
        db_cursor.execute('SELECT sid FROM favorite ORDER BY ROWID DESC')
        faves = db_cursor.fetchall()
        for a_row in faves:
            if len(a_row) > 0:
                items.append(a_row)
    except:
        pass
    finally:
        if db_connection is not None:
            db_connection.close()
    return items


def add_favorite(sid):
    db_connection = database.connect(db_file)
    db_cursor = db_connection.cursor()
    db_cursor.execute('INSERT INTO favorite (sid) VALUES (?)', (sid,))
    db_connection.commit()
    db_connection.close()


def remove_favorite(sid=None):
    db_connection = database.connect(db_file)
    db_cursor = db_connection.cursor()

    if sid is not None:
        db_cursor.execute('DELETE FROM favorite WHERE sid=?', (sid,))
    else:
        db_cursor.execute('DELETE FROM favorite')

    db_connection.commit()
    db_connection.close()


def check_in_database(sid):
    db_connection = database.connect(db_file)
    db_cursor = db_connection.cursor()
    db_cursor.execute('SELECT Count(sid) FROM favorite WHERE sid=?', (sid,))
    data = db_cursor.fetchone()
    return data > 0


def clear_favorite():
    do_clean = xbmcgui.Dialog().yesno('Confirm Delete', 'Are you sure you want to delete ALL Favorite entries?')
    if do_clean:
        remove_favorite()
        xbmc.executebuiltin('Container.Refresh')
