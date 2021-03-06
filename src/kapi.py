#!/bin/env python
__author__ = 'Konstantin Weddige'
import json
import datetime
import multiprocessing.pool
import math
import logging
import argparse
import operator
import time

import copy
import matplotlib


matplotlib.use('Agg')

import tornado
import tornado.web
import tornado.ioloop
import pylab
import io
import hashlib
import networkx
from shapely.geometry import MultiPolygon, shape
import shapely
import shapely.ops
import fiona
import timeout_decorator
import descartes
import utm

import geometry.kcenter
import graph.kcenter

logger = logging.getLogger(__name__)

TTL = 120
TIMEOUT = 10


def hash_args(*args):
    return hashlib.sha1(str(args).encode('utf-8')).hexdigest()


def resolve_args(algorithm, *args):
    result = []
    alg = ALGORITHMS[algorithm]
    for value in args:
        try:
            value = alg['arg_types'][len(result)](value)
        except:
            raise ValueError()
        if value in alg['args'][len(result)]:
            if isinstance(alg['args'][len(result)], dict):
                result.append(alg['args'][len(result)][value])
            else:
                result.append(value)
        else:
            raise ValueError()
    return result


def nearest_center(point, centers):
    return min(range(len(centers)), key=lambda i: math.hypot((point[0] - centers[i][0]), (point[1] - centers[i][1])))


def plot_small_geometric(task):
    args = resolve_args(task._algorithm, *task._args)
    points = args[1]

    fig = pylab.figure(figsize=(5, 5))
    pylab.axis('off')
    ax = fig.add_subplot(111)
    ax.xaxis.set_major_locator(pylab.NullLocator())
    ax.yaxis.set_major_locator(pylab.NullLocator())
    ax.set_aspect('equal')

    for center in task._result:
        circle = pylab.Circle(center, task._objective, color=CENTER_COLORS[task._result.index(center)], alpha=0.2)
        fig.gca().add_artist(circle)

    x = [p[0] for p in points]
    y = [p[1] for p in points]
    colors = [COLORS[nearest_center(p, task._result)] for p in points]

    minx = min(x)
    maxx = max(x)
    extrax = 0.1 * (maxx - minx)
    miny = min(y)
    maxy = max(y)
    extray = 0.1 * (maxy - miny)
    ax.set_ylim([miny - extray, maxy + extray])
    ax.set_xlim([minx - extrax, maxx + extrax])

    ax.scatter(x, y, c=colors, s=80)

    x = [p[0] for p in task._result]
    y = [p[1] for p in task._result]
    colors = CENTER_COLORS[:len(task._result)]

    ax.scatter(x, y, c=colors, s=100, marker='p')

    # ax.set_ylim([-5, 105])
    # ax.set_xlim([-5, 105])

    stream = io.BytesIO()
    fig.savefig(stream, format='png', bbox_inches='tight', pad_inches=0)

    return stream.getvalue()


def plot_big_geometric(task):
    args = resolve_args(task._algorithm, *task._args)
    points = args[1]

    fig = pylab.figure(figsize=(5, 5))
    pylab.axis('off')
    ax = fig.add_subplot(111)
    ax.xaxis.set_major_locator(pylab.NullLocator())
    ax.yaxis.set_major_locator(pylab.NullLocator())
    ax.set_aspect('equal')

    for center in task._result:
        circle = pylab.Circle(center, task._objective, color=CENTER_COLORS[task._result.index(center)], alpha=0.2)
        fig.gca().add_artist(circle)

    x = [p[0] for p in points]
    y = [p[1] for p in points]
    colors = [CENTER_COLORS[nearest_center(p, task._result)] for p in points]

    minx = min(x)
    maxx = max(x)
    extrax = 0.1 * (maxx - minx)
    miny = min(y)
    maxy = max(y)
    extray = 0.1 * (maxy - miny)
    ax.set_ylim([miny - extray, maxy + extray])
    ax.set_xlim([minx - extrax, maxx + extrax])

    ax.scatter(x, y, c=colors, s=5, linewidth=0)

    x = [p[0] for p in task._result]
    y = [p[1] for p in task._result]
    colors = CENTER_COLORS[:len(task._result)]

    ax.scatter(x, y, c=colors, s=100, marker='p')

    stream = io.BytesIO()
    fig.savefig(stream, format='png', bbox_inches='tight', pad_inches=0)

    return stream.getvalue()


def plot_small_graph(task):
    args = resolve_args(task._algorithm, *task._args)
    data = args[1]

    def nearest_center(node, centers):
        logger.debug(node, centers)
        return min(range(len(centers)),
                   key=lambda i: networkx.shortest_path_length(data, node, centers[i], weight='weight'))

    fig = pylab.figure(figsize=(5, 5))
    pylab.axis('off')
    ax = fig.add_subplot(111)
    ax.xaxis.set_major_locator(pylab.NullLocator())
    ax.yaxis.set_major_locator(pylab.NullLocator())
    ax.set_aspect('equal')

    node_colors = list()
    center_colors = list()
    width = [1 for e in data.edges()]
    for n in data.nodes():
        if n in task._result:
            center_colors.append(CENTER_COLORS[task._result.index(n)])
        else:
            center = nearest_center(n, task._result)
            node_colors.append(COLORS[center])
            shortest_path = networkx.shortest_path(data, n, task._result[center], weight='weight')
            for i in range(len(shortest_path) - 1):
                try:
                    width[data.edges().index((shortest_path[i], shortest_path[i + 1]))] = 3
                except:
                    width[data.edges().index((shortest_path[i + 1], shortest_path[i]))] = 3
    pos = networkx.get_node_attributes(data, 'pos')
    nodes = data.nodes().copy()
    for c in task._result:
        nodes.remove(c)

    networkx.draw_networkx(data, pos, with_labels=False, node_size=100, node_color=node_colors, width=width,
                           nodelist=nodes)
    networkx.draw_networkx_nodes(data, pos, with_labels=False, node_size=100, node_color=center_colors,
                                 nodelist=task._result, node_shape='p')

    x = [p[0] for p in pos.values()]
    y = [p[1] for p in pos.values()]

    minx = min(x)
    maxx = max(x)
    extrax = 0.1 * (maxx - minx)
    miny = min(y)
    maxy = max(y)
    extray = 0.1 * (maxy - miny)
    ax.set_ylim([miny - extray, maxy + extray])
    ax.set_xlim([minx - extrax, maxx + extrax])

    stream = io.BytesIO()
    fig.savefig(stream, format='png', bbox_inches='tight', pad_inches=0)

    return stream.getvalue()


def plot_big_graph(task):
    args = resolve_args(task._algorithm, *task._args)
    data = args[1]

    fig = pylab.figure(figsize=(5, 5))
    pylab.axis('off')
    ax = fig.add_subplot(111)
    ax.xaxis.set_major_locator(pylab.NullLocator())
    ax.yaxis.set_major_locator(pylab.NullLocator())
    ax.set_aspect('equal')

    pos = networkx.get_node_attributes(data, 'pos')
    nodes = data.nodes().copy()
    for c in task._result:
        nodes.remove(c)

    distance = {c: networkx.bellman_ford(data, c)[1] for c in task._result}
    node_colors = [
        COLORS[min(range(len(task._result)), key=lambda i: distance[task._result[i]].get(n, float('inf')))]
        for n in nodes
    ]

    networkx.draw_networkx(data, pos, with_labels=False, node_size=5, nodelist=nodes, node_color=node_colors,
                           linewidths=0)
    networkx.draw_networkx_nodes(data, pos, with_labels=False, node_size=100, node_color=COLORS,
                                 nodelist=task._result, node_shape='p')

    x = [p[0] for p in pos.values()]
    y = [p[1] for p in pos.values()]

    minx = min(x)
    maxx = max(x)
    extrax = 0.1 * (maxx - minx)
    miny = min(y)
    maxy = max(y)
    extray = 0.1 * (maxy - miny)
    ax.set_ylim([miny - extray, maxy + extray])
    ax.set_xlim([minx - extrax, maxx + extrax])

    stream = io.BytesIO()
    fig.savefig(stream, format='png', bbox_inches='tight', pad_inches=0)

    return stream.getvalue()


def plot_shape(task):
    args = resolve_args(task._algorithm, *task._args)
    data = args[1]

    fig = pylab.figure(figsize=(5, 5))
    pylab.axis('off')
    ax = fig.add_subplot(111)
    ax.xaxis.set_major_locator(pylab.NullLocator())
    ax.yaxis.set_major_locator(pylab.NullLocator())
    ax.set_aspect('equal')

    margin = 0.4
    x_min, y_min, x_max, y_max = data.bounds
    dx = x_max - x_min
    dy = y_max - y_min
    ax.set_xlim([x_min - margin * dx, x_max + margin * dx])
    ax.set_ylim([y_min - margin * dy, y_max + margin * dy])

    if data.geom_type == 'MultiPolygon':
        for poly in data:
            patch = descartes.PolygonPatch(poly, fc='#999999', ec='#000000', fill=True, zorder=-1)
            ax.add_patch(patch)
    else:
        patch = descartes.PolygonPatch(data, fc='#EEEEEE', ec='#000000', fill=True, zorder=-1)
        ax.add_patch(patch)

    grid = []
    step = geometry.kcenter._step_size(data, args[3])
    r = math.sqrt(2) * step[4] / 2
    for x, y in geometry.kcenter._grid_iter(*step):
        if data.distance(shapely.geometry.Point(x, y)) < r:
            grid.append((x, y))

    x = [p[0] for p in grid]
    y = [p[1] for p in grid]
    ax.scatter(x, y, s=5, c='k')

    for center in task._result:
        circle = pylab.Circle(center, task._objective, color=CENTER_COLORS[task._result.index(center)], alpha=0.2)
        fig.gca().add_artist(circle)

    x = [p[0] for p in task._result]
    y = [p[1] for p in task._result]
    colors = CENTER_COLORS[:len(task._result)]

    ax.scatter(x, y, c=colors, s=100)

    extrax = 0.1 * (x_max - x_min)
    extray = 0.1 * (y_max - y_min)
    ax.set_ylim([y_min - extray, y_max + extray])
    ax.set_xlim([x_min - extrax, x_max + extrax])

    stream = io.BytesIO()
    fig.savefig(stream, format='png', bbox_inches='tight', pad_inches=0)

    return stream.getvalue()


def approx_shape_objective(shape, centers, fraction):
    grid = []
    step = geometry.kcenter._step_size(shape, fraction)
    r = math.sqrt(2) * step[4] / 2
    for x, y in geometry.kcenter._grid_iter(*step):
        if shape.distance(shapely.geometry.Point(x, y)) < r:
            grid.append((x, y))
    return geometry.kcenter.objective(grid, centers) + r


CENTER_COLORS = ['#F0A3FF', '#0075DC', '#993F00', '#4C005C', '#191919', '#005C31', '#2BCE48', '#FFCC99', '#808080',
                 '#94FFB5', '#8F7C00', '#9DCC00', '#C20088', '#003380', '#FFA405', '#FFA8BB', '#426600', '#FF0010',
                 '#5EF1F2', '#00998F', '#E0FF66', '#740AFF', '#990000', '#FFFF80', '#FFFF00', '#FF5005']
COLORS = CENTER_COLORS
# NODE_COLORS = ['#ffb9ff', '#00baff', '#ff7200', '#e000ff', '#8c8c8c', '#00d06e', '#37ff5c', '#ffdea6', '#bfbfbf',
#               '#9fffc3', '#dbbe00', '#bef700', '#ff00da', '#0089ff', '#ffc105', '#ffbfd4', '#82ca00', '#ff0016',
#               '#68ffff', '#00e6d7', '#eaff6a', '#c310ff', '#ff0000', '#ffff82', '#ffff00', '#ff6a06']

GRAPH_INSTANCES = {
    'random': networkx.read_gpickle('../data/Random.network'),
    'muenchen': networkx.read_gpickle('../data/Muenchen.reduced.network'),
    'muenchen centre': networkx.read_gpickle('../data/Muenchen.centre.reduced.network'),
}

GRAPH_PLOTTER = {
    'random': plot_small_graph,
    'muenchen': plot_big_graph,
    'muenchen centre': plot_big_graph,
}

GEOMETRIC_INSTANCES = {
    'random': [node[1]['pos'] for node in GRAPH_INSTANCES['random'].nodes(data=True)],
    'muenchen': [node[1]['pos'] for node in GRAPH_INSTANCES['muenchen'].nodes(data=True)],
    'muenchen centre': [node[1]['pos'] for node in GRAPH_INSTANCES['muenchen centre'].nodes(data=True)],
}

GEOMETRIC_PLOTTER = {
    'random': plot_small_geometric,
    'muenchen': plot_big_geometric,
    'muenchen centre': plot_big_geometric,
}

utm_zone_number = None


def utm_transformation(lon, lat):
    global utm_zone_number
    result = utm.from_latlon(lat, lon, force_zone_number=utm_zone_number)
    if not utm_zone_number:
        utm_zone_number = result[2]
    return result[:2]

muenchen_shp = MultiPolygon([shape(pol['geometry']) for pol in fiona.open('../data/Muenchen.shp')])
muenchen_shp = shapely.ops.transform(utm_transformation, muenchen_shp)

muenchen_centre_shp = MultiPolygon([shape(pol['geometry']) for pol in fiona.open('../data/Muenchen.centre.shp')])
muenchen_centre_shp = shapely.ops.transform(utm_transformation, muenchen_centre_shp)

SHAPE_INSTANCES = {
    'random': MultiPolygon([shape(pol['geometry']) for pol in fiona.open('../data/Random.shp')]),
    'muenchen': muenchen_shp,
    'muenchen centre': muenchen_centre_shp,
}

SHAPE_PLOTTER = {
    'random': plot_shape,
    'muenchen': plot_shape,
    'muenchen centre': plot_shape,
}

ALGORITHMS = {
    'Gonzalez (euclidean)': {
        'algorithm': geometry.kcenter.gonzalez,
        'objective': geometry.kcenter.objective,
        'plotter': GEOMETRIC_PLOTTER,
        'args': [
            range(1, len(CENTER_COLORS) + 1),
            GEOMETRIC_INSTANCES,
        ],
        'arg_titles': [
            'k',
            'instance',
        ],
        'arg_types': [
            int,
            str,
        ],
        'arg_pattern': [
            operator.lt,
            None
        ]
    },
    'Gonzalez (metric)': {
        'algorithm': graph.kcenter.gonzalez,
        'objective': graph.kcenter.objective,
        'plotter': GRAPH_PLOTTER,
        'args': [
            range(1, len(CENTER_COLORS) + 1),
            GRAPH_INSTANCES,
        ],
        'arg_titles': [
            'k',
            'instance',
        ],
        'arg_types': [
            int,
            str,
        ],
        'arg_pattern': [
            operator.lt,
            None
        ]
    },
    'Ilhan-Pinar': {
        'algorithm': graph.kcenter.ilhan_pinar,
        'objective': graph.kcenter.objective,
        'plotter': GRAPH_PLOTTER,
        'args': [
            range(1, len(CENTER_COLORS) + 1),
            GRAPH_INSTANCES,
        ],
        'arg_titles': [
            'k',
            'instance',
        ],
        'arg_types': [
            int,
            str,
        ],
        'arg_pattern': [
            operator.lt,
            None
        ]
    },
    'Brandenberg-Roth': {
        'algorithm': geometry.kcenter.brandenberg_roth,
        'objective': geometry.kcenter.objective,
        'plotter': GEOMETRIC_PLOTTER,
        'args': [
            range(1, len(CENTER_COLORS) + 1),
            GEOMETRIC_INSTANCES,
            [1, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1],
        ],
        'arg_titles': [
            'k',
            'instance',
            'epsilon',
        ],
        'arg_types': [
            int,
            str,
            float,
        ],
        'arg_pattern': [
            operator.lt,
            None,
            operator.gt
        ]
    },
    'Grid approximation': {
        'algorithm': geometry.kcenter.grid_approximation,
        'objective': approx_shape_objective,
        'plotter': SHAPE_PLOTTER,
        'args': [
            range(1, len(CENTER_COLORS) + 1),
            SHAPE_INSTANCES,
            [1, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1],
            [1 / 5, 1 / 25, 1 / 50]
        ],
        'arg_titles': [
            'k',
            'instance',
            'epsilon',
            'fraction',
        ],
        'arg_types': [
            int,
            str,
            float,
            float,
        ],
        'arg_pattern': [
            operator.lt,
            None,
            operator.gt,
            operator.gt
        ]
    }
}


def decide(*args):
    result = DECISIONS
    for arg in args:
        if arg in result:
            # This yields an error if there are more args
            result = None
        else:
            for choices, options in result:
                if arg in choices:
                    result = options
                    break
    if isinstance(result[0], tuple):
        result_ = []
        for choice in result:
            result_.extend(choice[0])
        return sorted(result_)
    else:
        return sorted(result)


def build_decisions(data, types):
    if data:
        deeper = build_decisions(data[1:], types[1:])
        if deeper:
            return [
                (list(map(types[0], data[0])), deeper)
            ]
        else:
            return list(map(types[0], data[0]))


def train(pattern, *args):
    global DECISIONS
    DECISIONS = _train(args, pattern, DECISIONS)


def _train(args, pattern, decisions):
    try:
        result = decisions[:]
        if pattern[0]:
            if args[0] in decisions:
                for arg in decisions:
                    if not pattern[0](arg, args[0]):
                        result.remove(arg)
            else:
                for choices, options in decisions:
                    if args[0] in choices:
                        print(options)
                        low, high = [], []
                        for arg in choices:
                            if pattern[0](arg, args[0]):
                                low.append(arg)
                            else:
                                high.append(arg)
                        result.remove((choices, options))
                        result.append((high, _train(args[1:], pattern[1:], copy.deepcopy(options))))
                        if low:
                            result.append((low, options))
                        break
        else:
            if args[0] in decisions:
                result.remove(args[0])
            else:
                for choices, options in decisions:
                    if args[0] in choices:
                        result.remove((choices, options))
                        result.append(([args[0]], _train(args[1:], pattern[1:], copy.deepcopy(options))))
                        choices.remove(args[0])
                        if choices:
                            result.append((choices, options))
                        break
        return result
    except ValueError:
        return decisions


DECISIONS = [
    ([algo], build_decisions(ALGORITHMS[algo]['args'], ALGORITHMS[algo]['arg_types'])) for algo in ALGORITHMS
]

_tasks = dict()
_workers = multiprocessing.pool.ThreadPool(2)
_enqueue = True


class Task:
    result = None
    _callback = None

    def __init__(self, algorithm, *args):
        self.uuid = hash_args(algorithm, *args)
        self.state = 'pending'
        self._algorithm = algorithm
        self._args = args
        self.created = datetime.datetime.now()
        self.plot = None
        self._start = None
        self._stop = None

    def run(self, callback=None):
        self._callback = callback

        def _run():
            logger.debug('Start {0}'.format(self.uuid))
            self.state = 'started'
            self._start = time.clock()
            return timeout_decorator.timeout(
                TIMEOUT * 60, use_signals=False
            )(
                ALGORITHMS[self._algorithm]['algorithm']
            )(
                *resolve_args(self._algorithm, *self._args)
            )

        _workers.apply_async(_run, callback=self._on_finished, error_callback=self._on_error)
        # self._on_finished(_run())
        logger.info('{0} started'.format(self.uuid))

    def _on_finished(self, result):
        self._stop = time.clock()
        self._result = result
        logger.info('Compute objective for {0}'.format(self.uuid))
        # This expects the instance to be the second argument
        args = resolve_args(self._algorithm, *self._args)
        if self._algorithm == 'Grid approximation':
            # A better solution for this would be nice
            self._objective = ALGORITHMS[self._algorithm]['objective'](args[1], result, args[3])
        else:
            self._objective = ALGORITHMS[self._algorithm]['objective'](args[1], result)
        logger.info('{0} finished'.format(self.uuid))
        self.state = 'finished'
        if self._callback:
            self._callback(self)

    def _on_error(self, exception):
        logger.warn('{0} failed with {1}'.format(self.uuid, exception))
        train([None] + ALGORITHMS[self._algorithm]['arg_pattern'], self._algorithm,
              *[cast(value) for cast, value in zip(ALGORITHMS[self._algorithm]['arg_types'], self._args)])
        self.state = 'failed'

    @property
    def duration(self):
        if self._start and self._stop:
            return self._stop - self._start
        else:
            return float('inf')

    @property
    def ttl(self):
        return datetime.timedelta(minutes=TTL) - (datetime.datetime.now() - self.created)

    @property
    def info(self):
        if self.state == 'finished':
            return {
                'state': self.state,
                'description': str(self),
                'uri': application.reverse_url('task', self.uuid),
                'result': self._result,
                'objective': self._objective,
                'img': application.reverse_url('image', self.uuid),
                'duration': self.duration,
            }
        else:
            return {
                'state': self.state,
                'description': str(self),
                'uri': application.reverse_url('task', self.uuid)
            }

    @property
    def result(self):
        if self.state == 'finished':
            return {
                'description': str(self),
                'uri': application.reverse_url('algorithm', self._algorithm, '/' + '/'.join(self._args)),
                'result': self._result,
                'objective': self._objective,
                'img': application.reverse_url('image', self.uuid),
                'duration': self.duration,
            }
        else:
            return None

    def __str__(self):
        return '{algorithm}{args}'.format(
            algorithm=self._algorithm,
            args=self._args,
        )


class TasksHandler(tornado.web.RequestHandler):
    def get(self, uid=None):
        self.set_header('Access-Control-Allow-Origin', '*')
        if uid:
            if uid in _tasks:
                response = _tasks[uid].info
            else:
                raise tornado.web.HTTPError(404)
        else:
            response = dict()
            for uid, task in list(_tasks.items()):
                if task.ttl.total_seconds() > 0:
                    response[uid] = task.info
                else:
                    del _tasks[uid]
        self.write(json.dumps(response))


class ImageHandler(tornado.web.RequestHandler):
    def get(self, uid):
        if uid in _tasks:
            task = _tasks[uid]
            if task.result:
                self.set_header('Content-Type', 'image/png')
                if not task.plot:
                    # This requires the instance to be the second arg. TODO: Think of a better solution
                    task.plot = ALGORITHMS[task._algorithm]['plotter'][task._args[1]](task)
                self.write(task.plot)
            else:
                raise tornado.web.HTTPError(404)
        else:
            raise tornado.web.HTTPError(404)


class AlgorithmHandler(tornado.web.RequestHandler):
    def get(self, algorithm='', args=''):
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Access-Control-Expose-Headers', 'Location')
        if algorithm:
            try:
                alg = ALGORITHMS[algorithm]
                if args:
                    args = args.split('/')[1:]
                else:
                    args = []
                cleaned_args = resolve_args(algorithm, *args)
                if len(cleaned_args) < len(alg['args']):
                    answer = {
                        'title': alg['arg_titles'][len(cleaned_args)],
                        # 'suggestions': list(alg['args'][len(cleaned_args)])
                        'suggestions': decide(algorithm, *[cast(value) for cast, value in
                                                           zip(ALGORITHMS[algorithm]['arg_types'], args)]),
                    }
                    self.write(json.dumps(answer))
                else:
                    uid = hash_args(algorithm, *args)
                    if uid in _tasks:
                        if _tasks[uid].result:
                            self.write(json.dumps(_tasks[uid].result))
                        else:
                            self.set_status(202, 'Accepted')
                            self.set_header('Location', self.reverse_url('task', uid))
                    else:
                        _tasks[uid] = Task(algorithm, *args)
                        self.set_status(202, 'Accepted')
                        self.set_header('Location', self.reverse_url('task', uid))
                        _tasks[uid].run()
            except IndexError:
                raise tornado.web.HTTPError(404)
        else:
            answer = {
                'title': 'Algorithm',
                'suggestions': list(list(ALGORITHMS))
            }
            self.write(json.dumps(answer))


class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('Hallo Welt!')


application = tornado.web.Application([
    tornado.web.URLSpec(r'/tasks/(?P<uid>[a-z0-9-]+)', TasksHandler, name='task'),
    (r'/tasks', TasksHandler),
    tornado.web.URLSpec(r'/images/(?P<uid>[a-z0-9-]+)', ImageHandler, name='image'),
    tornado.web.URLSpec(r'/algorithms/([^/]+)(.*)', AlgorithmHandler, name='algorithm'),
    (r'/algorithms', AlgorithmHandler),
    (r'/', IndexHandler),
])

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--logging', help='Set log level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        default='INFO')
    parser.add_argument('-c', '--cython', help='Compile algorithms with cython', action='store_true')
    parser.add_argument('-p', '--port', help='Set port', type=int, default=8887)

    args = parser.parse_args()
    logging.basicConfig(level=args.logging)

    if args.cython:
        import pyximport

        pyximport.install()

        geometry.kcenter = pyximport.load_module('geometry.kcenter', 'geometry/kcenter.py')
        graph.kcenter = pyximport.load_module('graph.kcenter', 'graph/kcenter.py')

    application.listen(args.port)
    print('Press strg-c to exit')
    try:
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        print('Shut down...')
