"""
Ths tool converts graph data.

.. code-block:: none

   usage: convert.py INPUT OUTPUT
"""
__author__ = 'Konstantin Weddige'
import argparse
from networkx import write_gpickle, read_gpickle, read_gml, write_gml, read_graphml, write_graphml
from os.path import splitext
import timeit

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('INPUT')
    parser.add_argument('OUTPUT')
    args = parser.parse_args()

    input_file = args.INPUT
    input_extension = splitext(input_file)[1]
    if input_extension in {'.network', '.gpickle'}:
        input_format = read_gpickle
    elif input_extension == '.gml':
        input_format = read_gml
    elif input_extension == '.graphml':
        input_format = read_graphml
    else:
        input_format = None

    output_file = args.OUTPUT
    output_extension = splitext(output_file)[1]
    if output_extension in {'.network', '.gpickle'}:
        output_format = write_gpickle
    elif output_extension == '.gml':
        output_format = write_gml
    elif output_extension == '.graphml':
        output_format = write_graphml
    else:
        output_format = None

    if input_format and output_format:
        print('Read {0}'.format(input_file))
        graph = input_format(input_file)
        print('Write {0}'.format(output_file))
        output_format(graph, output_file)
    else:
        print('Unsupported file types')

