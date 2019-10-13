# -*- coding: utf-8 -*-
from nakamori_utils.globalvars import *


def show_information():
    """
    Open information, read news tag from addon.xml so the most important things are shown
    :return:
    """
    file_flag = 'news.log'
    if os.path.exists(os.path.join(plugin_home, file_flag)):
        os.remove(os.path.join(plugin_home, file_flag))
        xbmc.executebuiltin('RunScript(script.module.nakamori,?info=information)', True)

