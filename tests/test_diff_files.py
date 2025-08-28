"""
Tests file diff CLI behavior and JSON output for identical files.

Usage:
 uv run -m unittest discover -v -s tests -p 'test_*\\.py'
 ...or:
 uv run -m unittest --verbose discover --start-directory tests --pattern 'test_*\\.py'

The "discover" option means "discover and run all tests in the 'tests' directory and its subdirectories."
"""

import json
import subprocess
import unittest
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
OUTPUT_DIR: Path = (PROJECT_ROOT.parent / 'output_dir').resolve()
DIFF_DIR: Path = OUTPUT_DIR / 'diffed_files'


class TestDiffFilesCLIIdentical(unittest.TestCase):
    """
    Verifies that running the file-compare CLI reports identical files as the same.
    """

    def setUp(self) -> None:
        """
        Ensures the output directory exists for test writes.
        """
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        DIFF_DIR.mkdir(parents=True, exist_ok=True)

    def _latest_json(self) -> Path | None:
        """
        Returns latest JSON file under DIFF_DIR if present, else None.
        """
        if not DIFF_DIR.exists():
            return None
        jsons: list[Path] = sorted(DIFF_DIR.glob('diff_*.json'))
        return jsons[-1] if jsons else None

    def test_cli_reports_same_for_identical_files(self) -> None:
        """
        Creates two identical temp files, runs the CLI, and asserts JSON marks them as same.
        """
        # Use static fixtures under test_files/test_file_diffs
        old_file: Path = PROJECT_ROOT / 'test_files' / 'test_file_diffs' / 'old_files' / 'same.txt'
        new_file: Path = PROJECT_ROOT / 'test_files' / 'test_file_diffs' / 'new_files' / 'same.txt'

        cmd: list[str] = [
            'uv',
            'run',
            str(PROJECT_ROOT / 'diff_files.py'),
            '--old_file_path',
            str(old_file),
            '--new_file_path',
            str(new_file),
            '--output_dir_path',
            str(OUTPUT_DIR),
        ]
        # Intentionally allow failure until diff_files.py is implemented
        proc = subprocess.run(cmd, capture_output=True, text=True)

        # Expect stdout to be JSON containing an 'output_path' to the written JSON
        try:
            stdout_json: dict[str, object] = json.loads(proc.stdout)
        except Exception as exc:  # noqa: BLE001
            self.fail(f'Expected JSON on stdout but got:\n{proc.stdout}\n\nstderr=\n{proc.stderr}\nError: {exc}')

        self.assertIn('output_path', stdout_json)
        output_path = Path(str(stdout_json['output_path']))
        self.assertTrue(output_path.exists(), msg=f'Output path does not exist: {output_path}')

        with output_path.open('r', encoding='utf-8') as fh:
            data: dict[str, object] = json.load(fh)

        # Basic schema checks (proposed contract for diff_files.py)
        self.assertIn('comparison_files', data)
        self.assertIn('results', data)

        comp_files: dict[str, str] = data['comparison_files']  # type: ignore[assignment]
        self.assertEqual(comp_files['old_file'], str(old_file.resolve()))
        self.assertEqual(comp_files['new_file'], str(new_file.resolve()))

        results: dict[str, object] = data['results']  # type: ignore[assignment]
        # Expectation for identical content
        self.assertIn('same', results)
        self.assertIn('different', results)
        self.assertTrue(bool(results['same']))
        self.assertFalse(bool(results['different']))


if __name__ == '__main__':
    unittest.main()
