import json
import unittest
from importlib import import_module
from pathlib import Path

# Import the module under test
module_path = 'diff_folders'
df = import_module(module_path)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_ROOT = PROJECT_ROOT / 'test_files' / 'test_diffs_directory'
OUTPUT_DIR = Path('../output_dir')


class TestDiffFoldersCase1(unittest.TestCase):
    def setUp(self):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def test_case1_structure(self):
        old_dir = TEST_ROOT / 'old_files_1'
        new_dir = TEST_ROOT / 'new_files_1'

        result = df.diff_directories(old_dir, new_dir)

        self.assertIn('old_only', result)
        self.assertIn('new_only', result)
        self.assertIn('different', result)
        self.assertIn('same', result)

        self.assertEqual(result['same'], ['a.txt'])
        self.assertEqual(result['different'], ['sub/c.txt'])
        self.assertEqual(result['old_only'], ['b.txt'])
        self.assertEqual(result['new_only'], ['d.txt'])

        # Write JSON via module API
        out_path = df.write_json_output(OUTPUT_DIR, result)
        self.assertTrue(out_path.exists())
        with out_path.open() as f:
            data = json.load(f)
        self.assertEqual(data['same'], ['a.txt'])


class TestDiffFoldersCase2(unittest.TestCase):
    def setUp(self):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def test_case2_structure(self):
        old_dir = TEST_ROOT / 'old_files_2'
        new_dir = TEST_ROOT / 'new_files_2'

        result = df.diff_directories(old_dir, new_dir)

        self.assertEqual(result['same'], ['x.txt'])
        self.assertEqual(result['different'], [])
        self.assertEqual(result['old_only'], ['y.txt'])
        self.assertEqual(result['new_only'], ['z.txt'])

        # Ensure timestamped file is created
        out_path = df.write_json_output(OUTPUT_DIR, result)
        self.assertTrue(out_path.exists())
        self.assertTrue(out_path.name.startswith('diff_'))
        self.assertTrue(out_path.suffix == '.json')


if __name__ == '__main__':
    unittest.main()
