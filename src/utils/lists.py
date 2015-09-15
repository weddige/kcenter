__author__ = 'Konstantin Weddige'
import logging
logger = logging.getLogger(__name__)

def glue_together(*lists, unconnected=False):
    """
    Glues lists together.

    Example: glue_together([1, 2, 3], [3, 4, 5]) -> [1, 2, 3, 4, 5]

    :param *lists: list of lists
    :param unconnected: bool
    :return: list
    """
    result = list()
    remaining = lists
    while remaining:
        points = list(remaining[0])
        unmatched = list(remaining[1:])
        remaining = list()
        while unmatched:
            gap = True
            for way in unmatched:
                if way[0] == points[-1]:
                    points += way[1:]
                    unmatched.remove(way)
                    gap = False
                    break
                elif way[-1] == points[-1]:
                    points += list(reversed(way))[1:]
                    unmatched.remove(way)
                    gap = False
                    break
            if gap:
                if unconnected:
                    remaining.extend(unmatched)
                    unmatched = list()
                else:
                    raise ValueError('Lists not connected.')
        result.append(points)
    if not unconnected and result:
        return result[0]
    else:
        return result

def split(nested_lists):
    """
    Splits nested lists.

    Example: split([[1, 2], [1, 2]]) -> [1, 1], [2, 2]

    :param nested_lists: list of lists
    :return: list of list
    """
    result = []
    for nested_list in nested_lists:
        for i in range(len(nested_list)):
            if i >= len(result):
                result.append([])
            result[i].append(nested_list[i])
    return result