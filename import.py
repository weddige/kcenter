"""
Ths tool imports OSM data.

.. code-block:: none

   usage: import.py [-h] INPUT [OUTPUT]
"""
from gis import distance

__author__ = 'Konstantin Weddige'
import argparse
from pyosm.parsing import iter_osm_file
from pyosm.model import Way, Node
from networkx import Graph, write_gpickle
from os.path import splitext
import timeit
import math
import fiona
import utm
from shapely.geometry import Point, MultiPolygon, shape

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('INPUT')
    parser.add_argument('OUTPUT', nargs='?')
    parser.add_argument('--shape', help='Shapefile')
    args = parser.parse_args()

    input_file = args.INPUT
    output_file = args.OUTPUT or '{0}.network'.format(*splitext(input_file))
    shape_file = args.shape

    start = timeit.default_timer()

    if shape_file:
        print('Load shapefile')
        shape_file = MultiPolygon([shape(pol['geometry']) for pol in fiona.open(shape_file)])

    print('Read {0}'.format(input_file))

    graph = Graph()

    items = 0
    utm_zone_number = None
    for item in iter_osm_file(input_file):
        tags = {i.key: i.value for i in item.tags}
        if isinstance(item, Way) and 'highway' in tags:
            # Nodes are created implicitly
            last = None
            for node in item.nds:
                if last:
                    graph.add_edge(last, node, type=tags['highway'])
                    #edges += 1
                last = node
        elif isinstance(item, Node):
            pos = utm.from_latlon(item.lat, item.lon, force_zone_number=utm_zone_number)
            if not utm_zone_number:
                utm_zone_number = pos[2]
            graph.add_node(item.id, lat=item.lat, lon=item.lon, pos=pos[:2])
            #nodes += 1
        items += 1
        print('{0} items processed'.format(items), end='\r')

    print('{0} items processed'.format(items))

    if shape_file:
        n = graph.number_of_nodes()
        i = 0
        print('Apply shapefile')
        for node in graph.nodes():
            p = Point(graph.node[node]['lon'], graph.node[node]['lat'])
            if not shape_file.contains(p):
                graph.remove_node(node)
            i += 1
            print('{0}/{1} nodes processed'.format(i, n), end='\r')
        print('{0}/{1} nodes processed'.format(i, n))

    print('Search for orphaned nodes')
    orphaned = set()
    n = graph.number_of_nodes()
    i = 0
    for node in graph.nodes_iter():
        if graph.degree(node) == 0:
            orphaned.add(node)
        i += 1
        print('{0}/{1} nodes processed'.format(i, n), end='\r')
    
    print('{0}/{1} nodes processed'.format(i, n))
    print('Delete {0} orphaned nodes'.format(len(orphaned)))
    graph.remove_nodes_from(orphaned)

    print('Calculate offset')
    points = [node[1]['pos'] for node in graph.nodes(data=True)]
    min_x = min(points, key=lambda p: p[0])[0]
    min_y = min(points, key=lambda p: p[1])[1]
    for node in graph.nodes_iter():
        pos = (graph.node[node]['pos'][0] - min_x, graph.node[node]['pos'][1] - min_y)
        graph.node[node]['pos'] = pos
    print('Translated data by ({0}, {1})'.format(-min_x, -min_y))

    print('Calculate edge weights')
    n = graph.number_of_edges()
    i = 0
    for edge in graph.edges():
        lat1 = math.radians(graph.node[edge[0]]['lat'])
        lon1 = math.radians(graph.node[edge[0]]['lon'])
        lat2 = math.radians(graph.node[edge[1]]['lat'])
        lon2 = math.radians(graph.node[edge[1]]['lon'])
        graph[edge[0]][edge[1]]['weight'] = distance(lat1, lon1, lat2, lon2)
        i += 1
        print('{0}/{1} edges processed'.format(i, n), end='\r')
    print('{0}/{1} edges processed'.format(i, n))

    print('Write {0}'.format(output_file))
    write_gpickle(graph, output_file)
    
    stop = timeit.default_timer()
    print('Program ran in {0} seconds'.format(stop - start))