import xbmcgui


class ListItem(xbmcgui.ListItem):
    def __init__(self):
        xbmcgui.ListItem.__init__()

    def __init__(self, label, label2='', icon_image='', thumbnail_image='', path='', offscreen=False):
        xbmcgui.ListItem.__init__(self, label, label2, icon_image, thumbnail_image, path, offscreen)

    def __init__(self, series):
        """
        Init and fill info from a series object
        :param series:
        :type series: shoko_models.v2.series.Series
        """
        self.__init__()
