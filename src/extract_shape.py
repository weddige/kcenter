"""
Ths tool extracts a boundary from OSM data.

.. code-block:: none

   usage: extract_shape.py BOUNDARY_ID INPUT [OUTPUT]
"""
__author__ = 'Konstantin Weddige'
import argparse
from pyosm.parsing import iter_osm_file
from pyosm.model import Way, Node, Relation
from os.path import splitext
import timeit
from shapely.geometry import mapping, Polygon, MultiPolygon
import fiona
from utils.lists import glue_together

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('BOUNDARY_ID')
    parser.add_argument('INPUT')
    parser.add_argument('OUTPUT', nargs='?')
    args = parser.parse_args()

    input_file = args.INPUT
    output_file = args.OUTPUT or '{0}.shp'.format(*splitext(input_file))

    start = timeit.default_timer()

    print('Read {0}'.format(input_file))

    nodes = dict()
    outer = list()
    inner = list()

    items = 0
    ways = set()
    for item in iter_osm_file(input_file):
        tags = {i.key: i.value for i in item.tags}
        if 'boundary' in tags and item.id == int(args.BOUNDARY_ID): # 1015139
            if isinstance(item, Relation):
                for member in item.members:
                    if member.role == 'outer':
                        ways.add(member.ref)
                items += 1
            else:
                print('Object is not a relation!')
    for item in iter_osm_file(input_file):
        if item.id in ways:
            if isinstance(item, Way):
                tmp = list()
                for node in item.nds:
                    nodes[node] = None
                    tmp.append(node)
                    items += 1
                outer.append(tmp)
                items += 1
            else:
                print('Object is not a way!')

    for item in iter_osm_file(input_file):
        if item.id in nodes:
            if isinstance(item, Node):
                nodes[item.id] = (item.lon, item.lat)
                items += 1
            else:
                print('Object is not a node!')

    print('{0} items processed'.format(items))

    polygons = glue_together(*outer, unconnected=True)


    shapes = list()
    for polygon in polygons:
        points = [nodes[p] for p in polygon]
        shapes.append(Polygon(points))

    print('Found {0} polygons'.format(len(shapes)))

    # Define a polygon feature geometry with on e attribute
    schema = {
        'geometry': 'Polygon',
        'properties': {'id': 'int'},
    }

    print('Write {0}'.format(output_file))
    with fiona.open(output_file, 'w', 'ESRI Shapefile', schema) as c:
        for shape in shapes:
            c.write({
                'geometry': mapping(shape),
                'properties': {'id': 123},
            })

    stop = timeit.default_timer()
    print('Program ran in {0} seconds'.format(stop - start))