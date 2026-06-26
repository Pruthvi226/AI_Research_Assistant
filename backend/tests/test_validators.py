import unittest

from utils.validators import PDF_EXTENSIONS, require_query, validate_extension


class ValidatorsTest(unittest.TestCase):
    def test_require_query_strips_valid_input(self):
        self.assertEqual("summarize", require_query("  summarize  "))

    def test_require_query_rejects_empty_input(self):
        with self.assertRaises(ValueError):
            require_query("   ")

    def test_validate_extension_accepts_case_insensitive_suffix(self):
        validate_extension("Paper.PDF", PDF_EXTENSIONS)

    def test_validate_extension_rejects_unknown_suffix(self):
        with self.assertRaises(ValueError):
            validate_extension("paper.exe", PDF_EXTENSIONS)


if __name__ == "__main__":
    unittest.main()