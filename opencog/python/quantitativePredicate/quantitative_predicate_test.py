__author__ = 'Misgana Bayetta'
import unittest
import quantitative_predicate


class quantitativePredicateTest(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_quantile_borders(self):
        test_1 = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200]
        test_2 = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        test_3 = [10, 20, 30]
        test_instance = quantitative_predicate.Start()
        self.assertEqual(test_instance.quantile_borders(test_1, 4), [10, 55, 105, 155, 200])
        self.assertEqual(test_instance.quantile_borders(test_2, 4), [10, 25, 45, 65, 100])
        self.assertEqual(test_instance.quantile_borders(test_2, 10), [10, 15, 25, 35, 45, 55, 65, 75, 85, 100])


if __name__ == "__main__":
    unittest.main()