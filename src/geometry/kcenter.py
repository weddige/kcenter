"""
Algorithms for k-center problems on points
"""
__author__ = 'Konstantin Weddige'
import math
import collections
import logging
import shapely.geometry
import miniball
import random

import geometry

#import pyximport
#pyximport.install()

#from geometry.utils import objective

logger = logging.getLogger(__name__)


def objective(points, centers):
    """Calculates the distance between points and centers.

    :param points: list of points
    :param centers: list of points
    :return: float"""
    if centers and points:
        return max([min([geometry.distance(p, c) for c in centers]) for p in points])
    else:
        return 0


def gonzalez(k, points, randomized=True):
    """This is an geometric version of Gonzalez's algorithm.

    :param k: int
    :param points: list of points
    :return: list of points
    """

    def distance(a, b):
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

    if randomized:
        result = [random.choice(points)]
    else:
        result = [points[0]]
    data = [(p, result[0], distance(p, result[0])) for p in points]  # O(n)
    del data[0]
    while len(result) < k:
        furthest = max(range(len(data)), key=lambda i: data[i][2])
        new_result = data[furthest][0]
        del data[furthest]
        for i in range(len(data)):
            new_distance = distance(data[i][0], new_result)
            if data[i][2] > new_distance:
                data[i] = (data[i][0], new_result, new_distance)
        result.append(new_result)
    return result


__recursion_depth = 0
__recursions = 0
__warnings = 0
__stack_trace = None
__result = None
__skip_count = 0

def brandenberg_roth(k, points, epsilon=1):
    """This function calculates a geometric k-center by applying a branch-and-bound algorithm by René Brnadenberg
    and Lucia Roth. See "New Algorithms for k-Center and Extensions" for details.

    A 2-dimensional space and unit balls as containers are assumed.

    :param k: int
    :param points: list of points
    :param epsilon: float
    :return: list of points
    """
    global __recursion_depth
    global __recursions
    global __warnings
    global __skip_count
    __recursion_depth, __recursions, __warnings, __skip_count = 0, 0, 0, 0

    State = collections.namedtuple('State', ('core', 'remainings', 'rho', 'centers',
                                             'recursion_depth', 'uid', 'error'))
    Result = collections.namedtuple('Result', ('core', 'remainings', 'rho', 'centers',
                                               'lower_bound', 'upper_bound', 'state'))

    upper_bound = float('inf')
    # estimate = geometry.kcenter.gonzalez(k, points)
    # rho_bound = objective(points, estimate)

    stack = [
        State(
            [[] for i in range(k)],  # core
            points,  # remainings
            [0 for i in range(k)],  # rho
            [(0,0) for i in range(k)],  # centers
            0,  # recursion_depth
            __recursions,  # __id
            0,  # error
        )
    ]
    result = None

    while stack:
        state = stack.pop()

        lower_bound = max(state.rho)

        if lower_bound > (upper_bound * (1 + epsilon)) * (1 + state.error):
            __skip_count += 1

        # Are any points left?
        if not state.remainings:
            __recursion_depth = max(__recursion_depth, state.recursion_depth)
            # As no more points are left, the lower bound is an upper bound
            upper_bound = min(upper_bound, lower_bound)
            # current_objective < result.upper_bound
            if not result or lower_bound < result.upper_bound:
                result = Result(state.core, state.remainings, state.rho, state.centers, lower_bound,
                                lower_bound, state.uid)
            continue

        # Compute delta and keep some results for later use
        p = max(state.remainings, key=lambda p: objective([p], state.centers))
        delta = {i: geometry.distance(p, state.centers[i]) for i in range(k)}

        delta_min = min(delta.values())  # As k is usually small, this could be over-optimization

        # Update the global upper bound
        current_objective = max(delta_min, lower_bound)
        #current_objective = objective(points, state.centers)

        upper_bound = min(upper_bound, current_objective)

        if (1 + epsilon) * lower_bound > upper_bound:#upper_bound: #delta_min:
            __recursion_depth = max(__recursion_depth, state.recursion_depth)
            if not result or current_objective < result.upper_bound: #  lower_bound < result.lower_bound:
                result = Result(state.core, state.remainings, state.rho, state.centers, lower_bound,
                                current_objective, state.uid)
            continue
        else:
            # Sort clusters descending by distance to p
            empty_set = False
            for i in sorted(delta, key=delta.get, reverse=False):
                # Skip unnessesary permutations
                if not state.core[i]:
                    if empty_set:
                        continue
                    else:
                        empty_set = True
                # Recompute c, rho, core
                # deepcopy calls are expensive!
                core = [c[:] for c in state.core]
                core[i].append(p)
                remainings = state.remainings[:]
                remainings.remove(p)
                rho = state.rho[:]
                centers = state.centers[:]

                mb = miniball.Miniball(core[i])
                if not mb.is_valid():
                    logger.debug('Invalid miniball detected')
                    __warnings += 1
                rho[i] = math.sqrt(mb.squared_radius())
                centers[i] = mb.center()

                if max(rho) <= (upper_bound * (1 + epsilon)) * (1 + mb.relative_error()):
                    logger.debug('[{recursion_depth}] Add {p} to core[{0}]: {1}'.format(
                            i, rho[i], p=p, recursion_depth=state.recursion_depth))
                    __recursions += 1
                    new_state = State(core, remainings, rho, centers,
                                      state.recursion_depth + 1, __recursions, mb.relative_error())
                    stack.append(new_state)

    if result:
        logger.info('Objective bounded by {0} and {1}'.format(result.lower_bound, upper_bound))
        return result.centers
    else:
        raise ValueError('No result found')


approximate = gonzalez


def solve(k, points):
    """This function solves the k-center problem geometrically.

    :param k: int
    :param points: list of points
    :return: list of points
    """
    return brandenberg_roth(k, points, epsilon=0)

def _iter_partitions(k, points):
    p = points[0]
    for i in range(k):
        if points[1:]:
            for partition in _iter_partitions(k, points[1:]):
                yield [(i == j) and partition[j] + [p] or partition[j] for j in range(k)]
        else:
            yield [(i == j) and [p] or [] for j in range(k)]

def brute_force(k, points):
    """This function solves the geometric k-center problem by exhaustive calculations.

    :param k: int
    :param points: list of points
    :return: list of points
    """
    result = None
    result_obj = float('inf')
    for partition in _iter_partitions(k, points):
        centers = [miniball.Miniball(subset).center() for subset in partition if subset ]
        obj = geometry.kcenter.objective(points, centers)
        if obj < result_obj:
            result = centers
            result_obj = obj
    return result

def _step_size(shape, fraction=None, delta=None):
    x_min = math.floor(shape.bounds[0])
    x_max = math.ceil(shape.bounds[2])
    y_min = math.floor(shape.bounds[1])
    y_max = math.ceil(shape.bounds[3])
    if not delta:
        delta = max((x_max - x_min) * fraction, (y_max - y_min) * fraction)
    plus_one = math.ceil(delta)

    return x_min, x_max + plus_one, y_min, y_max + plus_one, delta

def _grid_iter(x_min, x_max, y_min, y_max, delta):
    x = x_min
    while x <= x_max:
        y = y_min
        while y <= y_max:
            yield x, y
            y += delta
        x += delta

def grid_approximation(k, shape, epsilon=0.1, fraction=1/10, delta=None):
    """This function approximates a shape covering by maximal 1/fraction**2 grid points.
    If delta is set, fraction is not used.

    :param k: int
    :param shape: BaseGeometry
    :param epsilon: float
    :param fraction: float
    :param delta: float
    :return: list of points
    """
    # Calculate grid points
    grid = []
    step = _step_size(shape, fraction, delta)
    r = math.sqrt(2) / 2 * step[4]
    for x, y in _grid_iter(*step):
        if shape.distance(shapely.geometry.Point(x, y)) < r:
            grid.append((x, y))
    # Solve geometric k-center
    return brandenberg_roth(k, grid, epsilon)