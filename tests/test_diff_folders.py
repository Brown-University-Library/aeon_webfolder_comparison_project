import json
import unittest
from importlib import import_module
from pathlib import Path
import types

# Import the module under test
module_path = 'diff_folders'
df: types.ModuleType = import_module(module_path)

PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
TEST_ROOT: Path = (PROJECT_ROOT / 'test_files' / 'test_diffs_directory').resolve()
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
        out_path: Path = df.write_json_output(OUTPUT_DIR, result)
        self.assertTrue(out_path.exists())
        self.assertTrue(out_path.name.startswith('diff_'))
        self.assertEqual(out_path.suffix, '.json')
        with out_path.open() as f:
            data: dict[str, list[str]] = json.load(f)
        self.assertEqual(data['same'], ['a.txt'])
        self.assertEqual(data['different'], ['sub/c.txt', 'w.txt'])


if __name__ == '__main__':
    unittest.main()
