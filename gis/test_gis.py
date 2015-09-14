__author__ = 'Konstantin Weddige'
import unittest
import math
from gis import distance


class TestDistance(unittest.TestCase):
    def test_distance(self):
        # Hamburg
        lat1 = math.radians(53.550556)
        lon1 = math.radians(9.993333)
        # München
        lat2 = math.radians(48.137222)
        lon2 = math.radians(11.575556)
        # Setze Erdradius von 6373km vorraus:
        self.assertEqual(round(distance(lat1, lon1, lat2, lon2)), 612251)

if __name__ == '__main__':
    unittest.main()