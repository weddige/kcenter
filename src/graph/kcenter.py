"""
Algorithms for k-center problems on graphs
"""
__author__ = 'Konstantin Weddige'
import networkx
import random
import itertools
import pulp
import numpy
import scipy.optimize

from graph import squared_graph, dominating_set, add_missing_edges


def objective(graph, centers):
    """Calculates the distance between nodes and centers.

    :param graph: Graph
    :param centers: list
    :return: float
    """
    if centers:
        # For big k networkx.floyd_warshall_numpy can be faster:
        # distance = networkx.floyd_warshall_numpy(graph)
        # return distance[numpy.ix_([graph.nodes().index(c) for c in centers])].min(axis=0).max(axis=1)[0,0]
        distance = {c: networkx.bellman_ford(graph, c)[1] for c in centers}
        return max([min([distance[c].get(n, float('inf')) for c in centers]) for n in graph.nodes_iter()])
    else:
        return float("inf")


def gonzalez(k, graph, randomized=True, heuristic=None, bellman_ford=True):
    """This function gives a 2-approximation for the k-center problem on a graph.
    See "Clustering to minimize the maximum intercluster distance" by
    Teofilo F. Gonzalez for more details.

    :param k: int
    :param graph: Graph
    :return: list
    """

    def distance(node, target):
        try:
            # return networkx.dijkstra_path_length(graph, node, target)
            return networkx.astar_path_length(graph, node, target, heuristic=heuristic)
        except networkx.NetworkXNoPath:
            return float('inf')

    if randomized:
        result = [random.choice(graph.nodes())]
    else:
        result = [graph.nodes()[0], ]
    for l in range(k - 1):
        dist = 0
        head = None
        if bellman_ford:
            distance = {c: networkx.bellman_ford(graph, c)[1] for c in result}
            head = max([
                (n, min([(c, distance[c].get(n, float('inf'))) for c in result], key=lambda i: i[1])[1])
                for n in graph.nodes_iter()
            ], key=lambda i: i[1])[0]
        else:
            for node in graph.nodes():
                tmp_dist = min(distance(node, target) for target in result)
                if tmp_dist > dist:
                    dist = tmp_dist
                    head = node
        if head:
            result.append(head)
        else:
            return result
    return result


def hochbaum_shmoys(k, graph):
    """This function gives a 2-approximation for the k-center problem on a complete graph.
    See "A best possible heuristic for the k-center problem" by
    Dorit S. Hochbaum and David B. Shmoys for more details.

    This implementation follows "k-Center in Verkehrsnetzwerken – ein Vergleich geometrischer
    und graphentheoretischer Ansätze" by Valentin Breuß.

    :param k: int
    :param graph: Graph
    :return: list
    """
    edges = list()
    for edge in sorted(graph.edges(data=True), key=lambda e: e[2]['weight']):
        edges.append(edge)
        squared = networkx.Graph(edges)
        squared.add_nodes_from(graph.nodes())
        squared = squared_graph(squared)
        maximal_independent_set = networkx.maximal_independent_set(squared)
        if len(maximal_independent_set) <= k:
            return maximal_independent_set


def ilhan_pinar(k, graph, sites=None, demand=None):
    """This function solves k-center on a graph.
    See "An Efficient Exact Algorithm for the Vertex p-Center Problem"
    by Taylan Ilhan and Mustafa C. Pinar for more details.

    :param k: int
    :param graph: Graph
    :return: list
    """
    D = networkx.floyd_warshall_numpy(graph)
    
    reshape = False
    if not sites:
        sites = graph.nodes()
        reshape = True
    if not demand:
        demand = graph.nodes()
        reshape = True
    if reshape:
        D = D[numpy.ix_([graph.nodes().index(c) for c in demand],[graph.nodes().index(c) for c in sites])]
    u = D.max()
    l = D.min()
    while True:
        epsilon = l + (u - l)/2
        B = 1 * (D <= epsilon)
        #"""
        prog = pulp.LpProblem('MILP', pulp.LpMinimize)
        x = pulp.LpVariable.dicts('centre', range(len(sites)), 0, 1)
        #prog += 0, 'No objective needed'
        for j in range(len(demand)):
            prog += pulp.lpSum([B[j,i] * x[i] for i in range(len(sites))]) >= 1, 'Reach node {0}'.format(j)
        prog += pulp.lpSum([x[i] for i in range(len(sites))]) <= k
        
        prog.solve()
        
        if prog.status == 1: # 'Optimal'
            u = epsilon
        elif prog.status == -1: # 'Infeasible'
            l = epsilon
        else:
            raise RuntimeError(pulp.LpStatus[prog.status])
        """
        A = numpy.concatenate([
                -1 * B,
                [[1] * B.shape[1]],
                numpy.diag([1] * B.shape[1]),
                numpy.diag([-1] * B.shape[1]),
            ])
        b = numpy.concatenate([[-1] * B.shape[0], [k] ,[1] * B.shape[1], [0] * B.shape[1]])
        lp = scipy.optimize.linprog([0] * B.shape[1], A, b)

        if lp.status == 0:
            u = epsilon
        elif lp.status == 2:
            l = epsilon
        else:
            raise RuntimeError(lp)
        """
        #if u - l < 1:
        if u < l * 1.05:
            break
    epsilon = l
    while True:
        B = 1 * (D <= epsilon)

        prog = pulp.LpProblem('MILP', pulp.LpMinimize)
        x = pulp.LpVariable.dicts('centre', range(len(sites)), 0, 1, pulp.LpInteger)
        #prog += 0, 'No objective needed'
        for j in range(len(demand)):
            prog += pulp.lpSum([B[j,i] * x[i] for i in range(len(sites))]) >= 1, 'Reach node {0}'.format(j)
        prog += pulp.lpSum([x[i] for i in range(len(sites))]) <= k

        prog.solve()

        # See pulp.LpStatus for status codes
        if prog.status == 1: # 'Optimal'
            return list(itertools.compress(sites, [var.value() for var in x.values()]))
        elif prog.status == -1: # 'Infeasible'
            epsilon = D[D > epsilon].min()
        else:
            raise RuntimeError(prog)
            
def sample_approximation(k, graph, m=1):
    sites = random.sample(graph.nodes(), int(len(graph) * m))
    ilhan_pinar(k, graph, sites=sites)


def brute_force(k, graph):
    """This function solves the k-center problem on graphs by exhaustive calculations.

    :param k: int
    :param graph: Graph
    :return: list
    """
    graph = add_missing_edges(graph)
    test_graph = networkx.Graph()
    test_graph.add_nodes_from(graph.nodes())
    for edge in sorted(graph.edges(data=True), key=lambda e: e[2]['weight']):
        test_graph.add_edge(*edge)
        result = dominating_set(test_graph, k)  # Das ist langsam
        if result:
            return result


solve = ilhan_pinar
approximate = gonzalez