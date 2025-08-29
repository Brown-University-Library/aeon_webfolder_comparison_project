"""
Tests file diff core behavior using compare_files().
"""

import unittest
from pathlib import Path
import b__diff_files

PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]


class TestDiffFilesCore(unittest.TestCase):
    """
    Verifies compare_files() reports correct sameness and diff hunks.
    """

    def test_compare_reports_same_for_identical_files(self) -> None:
        """
        Uses identical fixtures and asserts same is True with no diff hunks.
        """
        # Use static fixtures under test_files/test_file_diffs
        old_file: Path = PROJECT_ROOT / 'test_files' / 'test_file_diffs' / 'old_files' / 'same.txt'
        new_file: Path = PROJECT_ROOT / 'test_files' / 'test_file_diffs' / 'new_files' / 'same.txt'

        result: dict[str, object] = b__diff_files.compare_files(old_file, new_file)
        self.assertIn('same', result)
        self.assertIn('unified_diff_hunks', result)
        self.assertTrue(bool(result['same']))
        self.assertEqual(result['unified_diff_hunks'], [])

    def test_compare_reports_different_for_different_files(self) -> None:
        """
        Uses fixtures with differences and asserts same is False and at least one hunk exists.
        """
        old_file: Path = PROJECT_ROOT / 'test_files' / 'test_file_diffs' / 'old_files' / 'different.txt'
        new_file: Path = PROJECT_ROOT / 'test_files' / 'test_file_diffs' / 'new_files' / 'different.txt'

        result: dict[str, object] = b__diff_files.compare_files(old_file, new_file)
        self.assertIn('same', result)
        self.assertIn('unified_diff_hunks', result)
        self.assertFalse(bool(result['same']))
        self.assertGreaterEqual(len(result['unified_diff_hunks']), 1)

    def test_compare_reports_multiple_hunks_when_multiple_sections_differ(self) -> None:
        """
        Uses multihunk fixtures and asserts at least two diff hunks are returned.
        """
        old_file: Path = PROJECT_ROOT / 'test_files' / 'test_file_diffs' / 'old_files' / 'multihunk2.txt'
        new_file: Path = PROJECT_ROOT / 'test_files' / 'test_file_diffs' / 'new_files' / 'multihunk2.txt'

        result: dict[str, object] = b__diff_files.compare_files(old_file, new_file)
        self.assertFalse(bool(result['same']))
        self.assertIn('unified_diff_hunks', result)
        self.assertGreaterEqual(len(result['unified_diff_hunks']), 2)


if __name__ == '__main__':
    unittest.main()
