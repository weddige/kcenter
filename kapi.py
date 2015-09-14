#!/bin/env python
__author__ = 'Konstantin Weddige'
import json
import datetime
import multiprocessing.pool
import math
import logging
import argparse

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
import fiona
import timeout_decorator

import geometry.kcenter
import graph.kcenter

logger = logging.getLogger(__name__)

TTL = 120
TIMEOUT = 5


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


def plot_geometric(task):
    args = resolve_args(task._algorithm, *task._args)
    points = args[1]

    fig = pylab.figure(figsize=(5, 5))
    pylab.axis('off')
    ax = fig.add_subplot(111)
    ax.xaxis.set_major_locator(pylab.NullLocator())
    ax.yaxis.set_major_locator(pylab.NullLocator())

    for center in task._result:
        circle = pylab.Circle(center, task._objective, color=CENTER_COLORS[task._result.index(center)], alpha=0.2)
        fig.gca().add_artist(circle)

    x = [p[0] for p in points]
    y = [p[1] for p in points]
    colors = [NODE_COLORS[nearest_center(p, task._result)] for p in points]

    ax.scatter(x, y, c=colors, s=100)

    x = [p[0] for p in task._result]
    y = [p[1] for p in task._result]
    colors = CENTER_COLORS[:len(task._result)]

    ax.scatter(x, y, c=colors, s=100)

    # ax.set_ylim([-5, 105])
    # ax.set_xlim([-5, 105])

    stream = io.BytesIO()
    fig.savefig(stream, format='png', bbox_inches='tight', pad_inches=0)

    return stream.getvalue()


def plot_graph(task):
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

    colors = list()
    width = [1 for e in data.edges()]
    for n in data.nodes():
        if n in task._result:
            colors.append(CENTER_COLORS[task._result.index(n)])
        else:
            center = nearest_center(n, task._result)
            colors.append(NODE_COLORS[center])
            shortest_path = networkx.shortest_path(data, n, task._result[center], weight='weight')
            for i in range(len(shortest_path) - 1):
                try:
                    width[data.edges().index((shortest_path[i], shortest_path[i + 1]))] = 3
                except:
                    width[data.edges().index((shortest_path[i + 1], shortest_path[i]))] = 3
    pos = networkx.get_node_attributes(data, 'pos')
    networkx.draw_networkx(data, pos, with_labels=False, node_size=100, node_color=colors, ax=ax, width=width)

    stream = io.BytesIO()
    fig.savefig(stream, format='png', bbox_inches='tight', pad_inches=0)

    return stream.getvalue()


CENTER_COLORS = ['#F0A3FF', '#0075DC', '#993F00', '#4C005C', '#191919', '#005C31', '#2BCE48', '#FFCC99', '#808080',
                 '#94FFB5', '#8F7C00', '#9DCC00', '#C20088', '#003380', '#FFA405', '#FFA8BB', '#426600', '#FF0010',
                 '#5EF1F2', '#00998F', '#E0FF66', '#740AFF', '#990000', '#FFFF80', '#FFFF00', '#FF5005']
NODE_COLORS = ['#ffffff', '#64d9ff', '#fda364', '#b064c0', '#7d7d7d', '#64c095', '#8fffac', '#fffffd', '#e4e4e4',
               '#f8ffff', '#f3e064', '#ffff64', '#ff64ec', '#6497e4', '#ffff69', '#ffffff', '#a6ca64', '#ff6474',
               '#c2ffff', '#64fdf3', '#ffffca', '#d86eff', '#fd6464', '#ffffe4', '#ffff64', '#ffb469']

GRAPH_INSTANCES = {
    'random': graph.erdos_renyi_random_planar_graph(100, 0.8),
    'muenchen': networkx.read_gpickle('../data/Muenchen.simple.network'),
    'pappenheim': networkx.read_gpickle('../data/Pappenheim.simple.network'),
}

GEOMETRIC_INSTANCES = {
    'random': [node[1]['pos'] for node in GRAPH_INSTANCES['random'].nodes(data=True)],
    'muenchen': [node[1]['pos'] for node in GRAPH_INSTANCES['muenchen'].nodes(data=True)],
    'pappenheim': [node[1]['pos'] for node in GRAPH_INSTANCES['pappenheim'].nodes(data=True)],
}

SHAPE_INSTANCES = {
    'muenchen': MultiPolygon([shape(pol['geometry']) for pol in fiona.open('../data/Muenchen.shp')]),
    'pappenheim': MultiPolygon([shape(pol['geometry']) for pol in fiona.open('../data/Pappenheim.shp')]),
}

ALGORITHMS = {
    'geometric_gonzalez': {
        'algorithm': geometry.kcenter.gonzalez,
        'objective': geometry.kcenter.objective,
        'plotter': plot_geometric,
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
        ]
    },
    'gonzalez': {
        'algorithm': graph.kcenter.gonzalez,
        'objective': graph.kcenter.objective,
        'plotter': plot_graph,
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
        ]
    },
    'brandenberg_roth': {
        'algorithm': geometry.kcenter.brandenberg_roth,
        'objective': geometry.kcenter.objective,
        'plotter': plot_geometric,
        'args': [
            range(1, 3 + 1),
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
        ]
    }
}

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

    def run(self, callback=None):
        self._callback = callback

        def _run():
            logger.debug('Start {0}'.format(self.uuid))
            self.state = 'started'
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
        logger.info('Compute objective for {0}'.format(self.uuid))
        self._result = result
        # This expects the instance to be the second argument
        args = resolve_args(self._algorithm, *self._args)
        self._objective = ALGORITHMS[self._algorithm]['objective'](args[1], result)
        logger.info('{0} finished'.format(self.uuid))
        self.state = 'finished'
        if self._callback:
            self._callback(self)

    def _on_error(self, exception):
        logger.warn('{0} failed with {1}'.format(self.uuid, exception))
        self.state = 'failed'

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
                    task.plot = ALGORITHMS[task._algorithm]['plotter'](task)
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
                        'suggestions': list(alg['args'][len(cleaned_args)])
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
    tornado.web.URLSpec(r'/algorithms/([a-z0-9_]+)(.*)', AlgorithmHandler, name='algorithm'),
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
