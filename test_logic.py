# Tests to verify the functions are working as intended. No API key required.
import math
import unittest

from harness import grade, perturb, wilsons
from judge import cohens_kappa, is_faithful, FAITHFUL, LEAK


class TestGrade(unittest.TestCase):
    def test_must_contain_present(self):
        self.assertTrue(grade("the rate is one per million", must_contain="million"))

    def test_must_contain_absent(self):
        self.assertFalse(grade("no figure here", must_contain="million"))

    def test_must_not_contain_blocks(self):
        self.assertFalse(grade("about 20 people", must_not_contain="20"))

    def test_word_boundary(self):
        # "20" must NOT match inside "2023". Whole-word matching only
        self.assertTrue(grade("approved in 2023", must_not_contain="20"))

    def test_case_insensitive(self):
        self.assertTrue(grade("NOT IN DOCUMENT", must_contain="not in document"))

    def test_no_rules_passes(self):
        self.assertTrue(grade("anything at all")) # When no requirements are given a pass should be recorded


class TestPerturb(unittest.TestCase):
    def test_replaces(self):
        self.assertEqual(perturb("every 20 persons", [("every 20", "every 13")]), "every 13 persons") # when 20 is replaced with 13 does it equal argument 3

    def test_raises_on_noop(self):
        with self.assertRaises(AssertionError):
            perturb("nothing to change here", [("absent token", "x")]) # argument 1 is a phrase that doesn't exist in passage, thus nothing to replace, raising the assertion error for the perturb function


class TestWilsons(unittest.TestCase):
    def test_point_estimate(self):
        p, low, high = wilsons(3, 5)
        self.assertAlmostEqual(p, 0.6)
        self.assertTrue(0.0 <= low <= p <= high <= 1.0)

    def test_extreme_is_clamped_and_honest(self):
        p, low, high = wilsons(5, 5)
        self.assertEqual(p, 1.0)
        self.assertEqual(high, 1.0)   
        self.assertLess(low, 1.0)     # prevents [1.00, 1.00] that Wald CI gives


class TestCohensKappa(unittest.TestCase):
    def test_perfect_with_variation(self):
        po, k = cohens_kappa([True, False, True, False], [True, False, True, False])
        self.assertEqual(po, 1.0)
        self.assertAlmostEqual(k, 1.0)

    def test_all_one_class_is_nan(self):
        po, k = cohens_kappa([True, True, True], [True, True, True])
        self.assertEqual(po, 1.0)
        self.assertTrue(math.isnan(k))

    def test_chance_level(self):
        po, k = cohens_kappa([True, True, False, False], [True, False, True, False])
        self.assertAlmostEqual(po, 0.5)
        self.assertAlmostEqual(k, 0.0)

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            cohens_kappa([True], [True, False])

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            cohens_kappa([], [])


class TestLabels(unittest.TestCase):
    def test_is_faithful_maps_words_to_bools(self):
        self.assertTrue(is_faithful(FAITHFUL))
        self.assertFalse(is_faithful(LEAK))


if __name__ == "__main__":
    unittest.main()
