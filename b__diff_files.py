"""
Compares two files and writes a JSON summary of whether they are the same or different.

Usage:
  uv run b__diff_files.py \
    --old_file_path "/path/to/old.txt" \
    --new_file_path "/path/to/new.txt" \
    --output_dir_path "/absolute/path/to/output_dir"

    Example:
    uv run b__diff_files.py \
        --old_file_path "./test_files/test_file_diffs/old_files/multihunk2.txt" \
        --new_file_path "./test_files/test_file_diffs/new_files/multihunk2.txt" \
        --output_dir_path "../output_dir"

Output (stdout):
  {"output_path": "/absolute/path/to/output_dir/diffed_files/diff_YYYYMMDD-HHMMSS.json"}

Environment:
  LOG_LEVEL=[DEBUG|INFO]  (optional; defaults to INFO)
"""

import argparse
import difflib
import filecmp
import json
import logging
import os
import pprint
from datetime import datetime
from pathlib import Path

# logging ----------------------------------------------------------
log: logging.Logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """
    Configures logging based on the LOG_LEVEL environment variable.

    Called by main().
    """
    LOG_LEVEL: str = os.environ.get('LOG_LEVEL', 'INFO')
    level_dict: dict[str, int] = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
    }
    logging.basicConfig(
        level=level_dict.get(LOG_LEVEL, logging.INFO),
        format='[%(asctime)s] %(levelname)s [%(module)s-%(funcName)s()::%(lineno)d] %(message)s',
        datefmt='%d/%b/%Y %H:%M:%S',
    )
    log.debug('starting log')


# core -------------------------------------------------------------


def compare_files(old_file: Path, new_file: Path) -> dict[str, object]:
    """
    Compares two files and returns a result mapping with a sameness flag and diff hunks.

    Returns a dict like:
      {
        "same": bool,
        "unified_diff_hunks": list[list[str]]  # each inner list is a unified-diff hunk (starts with '@@')
      }

    Called by main().
    """
    try:
        are_same: bool = filecmp.cmp(old_file, new_file, shallow=False)
    except OSError:
        # If either file can't be read, consider them different
        are_same = False

    if are_same:
        return {
            'same': True,
            'unified_diff_hunks': [],
        }

    # Compute unified diff when content differs
    try:
        with old_file.open('r', encoding='utf-8', errors='replace') as prev:
            old_lines: list[str] = [line.rstrip() for line in prev.readlines()]
    except Exception:
        old_lines = []
    try:
        with new_file.open('r', encoding='utf-8', errors='replace') as curr:
            new_lines: list[str] = [line.rstrip() for line in curr.readlines()]
    except Exception:
        new_lines = []

    diff: list[str] = list(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=str(old_file),
            tofile=str(new_file),
            lineterm='',
        )
    )
    log.debug(f'diff: \n{pprint.pformat(diff)}')
    # Parse into hunks: split on lines starting with '@@'
    hunks: list[list[str]] = []
    current: list[str] = []
    for line in diff:
        # if line.startswith('--- ') or line.startswith('+++ '):
        #     # skip file header; we already expose file paths separately
        #     continue
        if line.startswith('@@ '):
            if current:
                hunks.append(current)
            current = [line]
        else:
            if current:
                current.append(line)
            else:
                # If diff starts without '@@' (unlikely), start a hunk anyway
                current = [line]
    if current:
        hunks.append(current)

    return {
        'same': False,
        'unified_diff_hunks': hunks,
    }


def write_json_output(output_dir: Path, result: dict[str, object], old_file: Path, new_file: Path) -> Path:
    """
    Writes structured output to a timestamped JSON file under output_dir/diffed_files/.

    Structure:
      {
        "comparison_files": {"old_file": "...", "new_file": "..."},
        "results": {"same": bool, "unified_diff_hunks": [["@@ ...", "+added", "-removed", " context"], ...]}
      }

    Called by main().
    """
    timestamp: str = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    diff_dir: Path = output_dir / 'diffed_files'
    diff_dir.mkdir(parents=True, exist_ok=True)
    out_path: Path = diff_dir / f'diff_{timestamp}.json'

    payload: dict[str, object] = {
        'comparison_files': {
            'old_file': str(old_file.resolve()),
            'new_file': str(new_file.resolve()),
        },
        'results': result,
    }
    with out_path.open('w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return out_path


# cli --------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """
    Parses and returns CLI arguments for file comparison.

    Called by main().
    """
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description=('Compare two files (old vs new) and output a JSON summary of whether they are the same or different.')
    )
    parser.add_argument(
        '--old_file_path',
        required=True,
        help="Path to the 'old' file",
    )
    parser.add_argument(
        '--new_file_path',
        required=True,
        help="Path to the 'new' file",
    )
    parser.add_argument(
        '--output_dir_path',
        required=True,
        help="Directory where the 'diffed_files' subdirectory and JSON output will be written",
    )
    return parser.parse_args()


# manager ----------------------------------------------------------


def main() -> None:
    """
    Runs comparison and writes JSON output; prints output path JSON to stdout.

    Called by __main__.
    """
    _configure_logging()
    args: argparse.Namespace = parse_args()

    old_file: Path = Path(args.old_file_path)
    new_file: Path = Path(args.new_file_path)
    output_dir: Path = Path(args.output_dir_path)

    if not old_file.is_file():
        raise SystemExit(f'old_file_path is not a file: {old_file}')
    if not new_file.is_file():
        raise SystemExit(f'new_file_path is not a file: {new_file}')

    result: dict[str, object] = compare_files(old_file, new_file)
    out_path: Path = write_json_output(output_dir, result, old_file, new_file)

    # Print machine-readable location for tests/automation
    print(json.dumps({'output_path': str(out_path)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
