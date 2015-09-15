__author__ = 'Konstantin Weddige'
import unittest

import networkx
import networkx.generators.random_graphs

import graph


class TestGraph(unittest.TestCase):
    def test_add_missing_edges(self):
        input = networkx.generators.cycle_graph(10)
        self.assertEqual(graph.add_missing_edges(input).number_of_edges(), 45)

    def test_dominating_set(self):
        input = networkx.generators.cycle_graph(10)
        output = graph.dominating_set(input, 4)
        self.assertEqual(len(output), 4)
        self.assertTrue(networkx.is_dominating_set(input, output))
        output = graph.dominating_set(input, 3)
        self.assertIsNone(output)

if __name__ == '__main__':
    unittest.main()