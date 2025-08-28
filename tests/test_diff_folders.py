"""
Tests directory diff behavior and JSON output.

Usage:
 uv run -m unittest discover -v -s tests -p 'test_*\.py'
 ...or:
 uv run -m unittest discover --verbose --start-directory tests --pattern 'test_*\.py'

The "discover" option means "discover and run all tests in the 'tests' directory and its subdirectories."
"""

import json
import types
import unittest
from importlib import import_module
from pathlib import Path

# Import the module under test
module_path = 'diff_folders'
df: types.ModuleType = import_module(module_path)

PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
TEST_ROOT: Path = (PROJECT_ROOT / 'test_files' / 'test_directory_diffs').resolve()
OUTPUT_DIR: Path = (PROJECT_ROOT.parent / 'output_dir').resolve()


class TestDiffFoldersCombined(unittest.TestCase):
    def setUp(self) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def test_combined_structure(self) -> None:
        old_dir: Path = TEST_ROOT / 'old_files'
        new_dir: Path = TEST_ROOT / 'new_files'

        result: dict[str, list[str]] = df.diff_directories(old_dir, new_dir)

        # Categories present
        self.assertIn('old_only', result)
        self.assertIn('new_only', result)
        self.assertIn('different', result)
        self.assertIn('same', result)

        # Expected contents
        self.assertEqual(result['same'], ['a.txt'])
        self.assertEqual(result['different'], ['sub/c.txt', 'w.txt'])
        self.assertEqual(result['old_only'], ['y.txt'])
        self.assertEqual(result['new_only'], ['z.txt'])

        # JSON output check
        out_path: Path = df.write_json_output(OUTPUT_DIR, result, old_dir, new_dir)
        self.assertTrue(out_path.exists())
        self.assertTrue(out_path.name.startswith('diff_'))
        self.assertEqual(out_path.suffix, '.json')
        with out_path.open() as f:
            data: dict[str, object] = json.load(f)

        # Top-level keys
        self.assertIn('comparison_directories', data)
        self.assertIn('results', data)

        # Directory paths
        comp_dirs: dict[str, str] = data['comparison_directories']  # type: ignore[assignment]
        self.assertEqual(comp_dirs['old_dir'], str(old_dir.resolve()))
        self.assertEqual(comp_dirs['new_dir'], str(new_dir.resolve()))

        # Results content
        results: dict[str, list[str]] = data['results']  # type: ignore[assignment]
        self.assertEqual(results['same'], ['a.txt'])
        self.assertEqual(results['different'], ['sub/c.txt', 'w.txt'])


if __name__ == '__main__':
    unittest.main()
