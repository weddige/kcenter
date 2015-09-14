"""
Ths tool simplifies imported data.

.. code-block:: none

   usage: simplify.py [-h] INPUT [OUTPUT]
"""
__author__ = 'Konstantin Weddige'
import argparse
from networkx import write_gpickle, read_gpickle, connected_component_subgraphs, union_all, astar_path_length
from os.path import splitext
import math
import timeit

import gis

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('INPUT')
    parser.add_argument('OUTPUT', nargs='?')
    args = parser.parse_args()

    # motorway, trunk, primary, secondary, tertiary, unclassified, residential, service,
    # motorway_link, trunk_link, primary_link, secondary_link, tertiary_link,
    # living_street, pedestrian, track, bus_guideway, raceway, road

    input_file = args.INPUT
    output_file = args.OUTPUT or '{0}.simple.network'.format(*splitext(input_file))
    distance_threshold = 1000  # 1km
    connectivity_threshold = 10  # 10%
    highway_types = {'living_street', 'residential', 'secondary', 'tertiary', 'unclassified',
                     'tertiary_link', 'primary_link', 'primary', 'trunk_link', 'trunk', 'motorway_link',
                     'secondary_link', 'motorway', 'road'}

    start = timeit.default_timer()

    print('Read {0}'.format(input_file))
    graph = read_gpickle(input_file)

    print('Remove undesirable highways')
    highways = set()
    items, edges_removed = 0, 0
    for edge in list(graph.edges(data=True)):
        if not edge[2]['type'] in highway_types:
            graph.remove_edge(*edge[:2])
            edges_removed += 1
            highways.add(edge[2]['type'])
        items += 1
        print('{0} items processed'.format(items), end='\r')
    print('{0} items processed'.format(items))
    print('Deleted {0} edges'.format(edges_removed))
    print('The types of the deleted edges were {0}'.format(highways))

    print('Delete orphaned nodes')
    nodes_removed = 0
    for node in list(graph.nodes()):
        if graph.degree(node) == 0:
            graph.remove_node(node)
            nodes_removed += 1
    print('Deleted {0} nodes'.format(nodes_removed))

    print('Remove disconnected components')
    components = list()
    nodes_discarded = 0
    threshold = graph.size() / connectivity_threshold
    for component in list(connected_component_subgraphs(graph)):
        if component.size() >= threshold:
            components.append(component)
        else:
            nodes_discarded += component.size()
    graph = union_all(components)
    print('Deleted {0} nodes'.format(nodes_discarded))
    print('{0} connected components remaining'.format(len(components)))

    def heuristic(a, b):
        lat1 = math.radians(graph.node[a]['lat'])
        lon1 = math.radians(graph.node[a]['lon'])
        lat2 = math.radians(graph.node[b]['lat'])
        lon2 = math.radians(graph.node[b]['lon'])
        return gis.distance(lat1, lon1, lat2, lon2)

    print('Remove short edges')
    items, edges_removed, violates_triangle_inequality = 0, 0, 0
    for node in graph.nodes_iter():
        if graph.degree(node) == 2:
            weight = 0
            neighbours = dict(graph[node])
            for n in neighbours:
                weight += graph[node][n]['weight']
            if weight <= distance_threshold:
                a, b = list(neighbours)
                dist = astar_path_length(graph, a, b, heuristic=heuristic)
                if dist < weight:
                    violates_triangle_inequality += 1
                else:
                    # Only look at first type
                    type = graph[node][a]['type']
                    graph.remove_edge(node, a)
                    graph.remove_edge(node, b)
                    graph.add_edge(a, b, weight=weight, type=type)
                    edges_removed += 2
        items += 1
        print('{0} items processed'.format(items), end='\r')
    print('{0} items processed'.format(items))
    print('Deleted {0} edges'.format(edges_removed))
    print('Kept {0} edges to preserve triangle inequality'.format(violates_triangle_inequality))

    items = 0
    orphaned = set()
    for node in graph.nodes_iter():
        if graph.degree(node) == 0:
            orphaned.add(node)
        items += 1
        print('{0} items processed'.format(items), end='\r')

    print('{0} items processed'.format(items))
    print('Delete {0} orphaned nodes'.format(len(orphaned)))
    graph.remove_nodes_from(orphaned)
    print('Write {0}'.format(output_file))
    write_gpickle(graph, output_file)
    
    stop = timeit.default_timer()
    print('Program ran in {0} seconds'.format(stop - start))