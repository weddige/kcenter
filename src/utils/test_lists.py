__author__ = 'Konstantin Weddige'
import unittest
from utils import lists

class TestListUtils(unittest.TestCase):
    def test_glue_together(self):
        input = [[1, 2, 3], [3, 4, 5]]
        self.assertEqual(lists.glue_together(*input), [1, 2, 3, 4, 5])

    def test_split(self):
        input = [[1, 2], [1, 2]]
        self.assertEqual(lists.split(input), [[1, 1], [2, 2]])

if __name__ == '__main__':
    unittest.main()