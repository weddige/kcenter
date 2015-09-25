__author__ = 'Konstantin Weddige'
import itertools
import math
import logging

import networkx
from random import choice, uniform


logger = logging.getLogger(__name__)

def squared_graph(graph):
    """
    Computes the squared graph.

    :param graph: Graph
    :return: Graph
    """
    squared = graph.copy()
    for node in squared.nodes():
        for a, b in itertools.combinations(graph.neighbors(node), 2):
            edge = graph.get_edge_data(a, b)
            weight = squared.get_edge_data(node, a)['weight'] + squared.get_edge_data(node, b)['weight']
            if (edge and edge['weight'] > weight) or not edge:
                squared.add_edge(a, b, weight=weight)
    return squared


def dominating_set(graph, size):
    """
    Tries to compute dominating set of size k.

    :param graph: Graph
    :param size: int
    :return: list
    """
    for nodes in itertools.combinations(graph.nodes(), size):
        if networkx.is_dominating_set(graph, nodes):
            return nodes


def minimal_dominating_set(graph):
    """
    Computes a minimal dominating set with brute force.

    :param graph: Graph
    :return: list
    """
    k = 1
    while True:
        for nodes in itertools.combinations(graph.nodes(), k):
            if networkx.is_dominating_set(graph, nodes):
                return nodes
        k += 1


def _ccw(a, b, c):
    """
    counterclockwise

    :param a: tuple
    :param b: tuple
    :param c: tuple
    :return: 1, 0 or -1
    """
    dx1 = b[0] - a[0]
    dy1 = b[1] - a[1]
    dx2 = c[0] - a[0]
    dy2 = c[1] - a[1]
    if dx1 * dy2 > dy1 * dx2:
        return 1
    if dx1 * dy2 < dy1 * dx2:
        return -1
    if dx1 * dy2 == dy1 * dx2:
        if (dx1 * dx2 < 0) or (dy1 * dy2 < 0):
            return -1
        elif (dx1 * dx1 + dy1 * dy1) >= (dx2 * dx2 + dy2 * dy2):
            return 0
        else:
            return 1


def edge_crossings(graph, x=None, y=None):
    """
    Returns if there are edge crossings in graph.

    :param graph: Graph
    :param x: edge
    :param y: edge
    :return: bool
    """
    if not (x is None or y is None):
        a = graph.node[x]['pos']
        b = graph.node[y]['pos']
        for edge in graph.edges():
            if edge[0] == x or edge[1] == x or edge[0] == y or edge[1] == y:
                continue
            c = graph.node[edge[0]]['pos']
            d = graph.node[edge[1]]['pos']
            if ((_ccw(a, b, c) * _ccw(a, b, d)) <= 0) and ((_ccw(c, d, a) * _ccw(c, d, b)) <= 0):
                return True
    else:
        for edge in graph.edges():
            if edge_crossings(graph, x=edge[0], y=edge[1]):
                return True
    return False


def erdos_renyi_random_planar_graph(n, p=0.5, radius=2/3):
    """
    Returns a random planar graph.

    :param n: int
    :param p: [0,1]
    :param radius: [0,1]
    :return: Graph
    """
    size = 100
    graph = networkx.Graph()
    for node in range(n):
        graph.add_node(node, pos=(uniform(0, size), uniform(0, size)))
    for edge in itertools.combinations(graph.nodes(data=True), 2):
        weight = math.sqrt((edge[0][1]['pos'][0] - edge[1][1]['pos'][0])**2 +
                           (edge[0][1]['pos'][1] - edge[1][1]['pos'][1])**2)
        if uniform(0, 1) < p and weight < size * radius:
            if not edge_crossings(graph, edge[0][0], edge[1][0]):
                graph.add_edge(edge[0][0], edge[1][0], weight=weight)
    return graph


def get_nodes_within(graph, x, r):
    """
    Returns nodes within radius r of x.

    :param graph: Graph
    :param x: node
    :param r: positive number
    :return: list of nodes
    """
    result = list()
    for y in graph.nodes():
        if not x == y:
            d = math.sqrt((graph.node[x]['pos'][0] - graph.node[y]['pos'][0])**2 +
                          (graph.node[x]['pos'][1] - graph.node[y]['pos'][1])**2)
            if d < r:
                result.append(y)
    return result


def growing_random_planar_graph(n, m=5, f=lambda: uniform(2, 5)):
    """
    See Random planar graphs and the London street network
    by A.P. Masuccia, D. Smith, A. Crooks, and M. Batty
    for further information.

    :param n: int
    :param m: int
    :return: Graph
    """
    result = networkx.Graph()
    result.add_node(0, pos=(0, 0))
    tries = 0
    tries_bound = m #  Choose good bound tor tries
    while result.number_of_nodes() < n:
        x, data = choice(result.nodes(data=True))
        r = f()
        if (result.number_of_edges() + 1) % m == 0 and tries < tries_bound:
            neighbourhood = get_nodes_within(result, x, r)
            if neighbourhood:
                y = choice(neighbourhood)
                if not edge_crossings(result, x=x, y=y):
                    weight = math.sqrt((data['pos'][0] - result.node[y]['pos'][0])**2 +
                                       (data['pos'][1] - result.node[y]['pos'][1])**2)
                    result.add_edge(x, y, weight=weight)
                    tries = 0
                else:
                    tries += 1
            else:
                tries += 1
        else:
            if tries:
                tries = 0
            phi = uniform(0, 2 * math.pi)
            pos = (data['pos'][0] + r * math.sin(phi), data['pos'][1] + r * math.cos(phi))
            y = result.number_of_nodes()
            result.add_node(y, pos=pos)
            if not edge_crossings(result, x=x, y=y):
                result.add_edge(x, y, weight=r)
            else:
                result.remove_node(y)
    return result


def build_grid(n, m, l=1):
    """
    See Random planar graphs and the London street network
    by A.P. Masuccia, D. Smith, A. Crooks, and M. Batty
    for further information.
    """
    result = networkx.grid_2d_graph(n, n)
    for a in result.nodes():
        result.node[a]['pos'] = (l * a[0], l * a[1])
    for e in result.edges():
        result.edge[e[0]][e[1]]['weight'] = l
    for i in range(m):
        e = choice(result.edges())
        sigma = result.edge[e[0]][e[1]]['weight']
        apos = (
            (result.node[e[0]]['pos'][0] + result.node[e[1]]['pos'][0]) / 2,
            (result.node[e[0]]['pos'][1] + result.node[e[1]]['pos'][1]) / 2
        )
        a = result.number_of_nodes()
        bpos = (
            apos[0] + (result.node[e[0]]['pos'][1] - result.node[e[1]]['pos'][1]) / 3,
            apos[1] + (result.node[e[0]]['pos'][0] - result.node[e[1]]['pos'][0]) / 3
        )
        result.add_node(a, pos=apos)
        result.add_node(a + 1, pos=bpos)
        result.add_edge(a, a + 1, weight=sigma / 3)
        result.add_edge(e[0], a, weight=sigma / 2)
        result.add_edge(e[1], a, weight=sigma / 2)
        result.remove_edge(e[0], e[1])
    return result

def add_missing_edges(graph):
    """
    Returns a complete graph.

    :param graph: Graph
    :return: Graph
    """
    result = graph.copy()
    for edge in itertools.combinations(result.nodes(), 2):
        if not result.has_edge(*edge):
            try:
                weight = networkx.shortest_path_length(result, *edge, weight='weight')
                result.add_edge(*edge, weight=weight)
            except networkx.NetworkXNoPath:
                pass
    return result