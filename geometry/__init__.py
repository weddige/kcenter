__author__ = 'Konstantin Weddige'
import math
import itertools


def distance(a, b):
    """
    Calculates the distance of two points.
    :param a: (float, float)
    :param b: (float, float)
    :return: float
    """
    return math.hypot(a[0] - b[0], a[1] - b[1])


def d(points):
    """
    Calculates d(points, B(0, 1)) in O(n²).
    :param points: list of (float, float)
    :return: float
    """
    return max([distance(p, q) / 2 for p, q in itertools.combinations(points, 2)])