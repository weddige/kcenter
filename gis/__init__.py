import math

__author__ = 'Konstantin'


def distance(lat1, lon1, lat2, lon2):
    """
    Computes the distance between two points on earth's surface.

    :param lat1: radians
    :param lon1: radians
    :param lat2: radians
    :param lon2: radians
    :return: m
    """
    radius = 6373 * 1000
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = (math.sin(dlat/2))**2 + math.cos(lat1) * math.cos(lat2) * (math.sin(dlon/2))**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return radius * c