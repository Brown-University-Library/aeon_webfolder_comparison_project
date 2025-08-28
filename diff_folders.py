"""
Compares two directories recursively and writes a JSON summary of differences.

Usage:
  uv run diff_folders.py \
    --old_dir_path "/path/to/old" \
    --new_dir_path "/path/to/new" \
    --output_dir_path "/absolute/path/to/output_dir"

  example:
    uv run diff_folders.py \
      --old_dir_path "./test_files/test_diffs_directory/old_files" \
      --new_dir_path "./test_files/test_diffs_directory/new_files" \
      --output_dir_path "../output_dir"

  output:
    ```
    Folder diff results:
    - old_only: 1
    - new_only: 1
    - different: 2
    - same: 1
    Wrote JSON diff to: ../output_dir/diff/diff_20250827-214410.json
    ```

Environment:
  LOG_LEVEL=[DEBUG|INFO]  (optional; defaults to INFO)
"""

import argparse
import filecmp
import json
import logging
import os
import pprint
from datetime import datetime
from pathlib import Path

## logging ----------------------------------------------------------
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


def collect_files(base_dir: Path) -> dict[str, Path]:
    """
    Collects files under base_dir and returns a mapping of relative POSIX paths to absolute Paths.
    Only includes files (not directories).

    Called by diff_directories().
    """
    base_dir = base_dir.resolve()
    mapping: dict[str, Path] = {}
    for root, _dirs, files in os.walk(base_dir):
        root_path: Path = Path(root)
        for fname in files:
            abs_path: Path = root_path / fname
            rel_path: str = abs_path.relative_to(base_dir).as_posix()
            mapping[rel_path] = abs_path
    log.debug(f'mapping, ``{pprint.pformat(mapping)}``')
    return mapping


def compare_common_files(old_map: dict[str, Path], new_map: dict[str, Path]) -> tuple[list[str], list[str]]:
    """
    Compares content of files present in both maps and returns (same, different) lists.
    Returns:
      - same: list of relative paths with identical content
      - different: list of relative paths with differing content

    Called by diff_directories().
    """
    same: list[str] = []
    different: list[str] = []

    common_keys: set[str] = old_map.keys() & new_map.keys()
    for key in sorted(common_keys):
        old_file: Path = old_map[key]
        new_file: Path = new_map[key]
        try:
            ## filecmp.cmp with shallow=False compares file content
            if filecmp.cmp(old_file, new_file, shallow=False):
                same.append(key)
            else:
                different.append(key)
        except OSError:
            ## If either file can't be read, consider it different and proceed
            different.append(key)
    return same, different


def diff_directories(old_dir: Path, new_dir: Path) -> dict[str, list[str]]:
    """
    Computes a recursive diff between two directories.

    Args:
        old_dir: Path to the "old" directory.
        new_dir: Path to the "new" directory.

    Returns:
        A dict with keys:
        - 'old_only': files present only in old_dir (relative POSIX paths)
        - 'new_only': files present only in new_dir
        - 'different': files present in both but with different content
        - 'same': files present in both with identical content

    Called by main().
    """
    log.debug(f'collecting old_map from {old_dir.resolve()}')
    old_map: dict[str, Path] = collect_files(old_dir)
    log.debug(f'collecting new_map from {new_dir.resolve()}')
    new_map: dict[str, Path] = collect_files(new_dir)

    old_keys: set[str] = set(old_map.keys())
    new_keys: set[str] = set(new_map.keys())

    old_only: list[str] = sorted(list(old_keys - new_keys))
    new_only: list[str] = sorted(list(new_keys - old_keys))

    same, different = compare_common_files(old_map, new_map)

    return {
        'old_only': old_only,
        'new_only': new_only,
        'different': sorted(different),
        'same': sorted(same),
    }


def write_json_output(output_dir: Path, data: dict[str, list[str]], old_dir: Path, new_dir: Path) -> Path:
    """
    Writes structured diff output to a timestamped JSON file under output_dir/diff/.

    Structure:
      {
        "comparison_directories": {"old_dir": "...", "new_dir": "..."},
        "results": {"old_only": [...], "new_only": [...], "different": [...], "same": [...]} 
      }

    Args:
        output_dir: Base directory where a 'diff' subfolder will be created.
        data: The diff results to serialize under the 'results' key.
        old_dir: The directory used as the "old" source.
        new_dir: The directory used as the "new" source.

    Returns:
        The path to the written JSON file.

    Called by main().
    """
    timestamp: str = datetime.now().strftime('%Y%m%d-%H%M%S')
    diff_dir: Path = output_dir / 'diff'
    diff_dir.mkdir(parents=True, exist_ok=True)
    out_path: Path = diff_dir / f'diff_{timestamp}.json'
    payload: dict[str, object] = {
        'comparison_directories': {
            'old_dir': str(old_dir.resolve()),
            'new_dir': str(new_dir.resolve()),
        },
        'results': data,
    }
    with out_path.open('w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return out_path


def print_summary(result: dict[str, list[str]]) -> None:
    """
    Prints a concise summary of diff results to stdout.

    Called by main().
    """
    print('Folder diff results:')
    print(f'- old_only: {len(result["old_only"])}')
    print(f'- new_only: {len(result["new_only"])}')
    print(f'- different: {len(result["different"])}')
    print(f'- same: {len(result["same"])}')


def parse_args() -> argparse.Namespace:
    """
    Parses and returns CLI arguments for directory comparison.

    Called by main().
    """
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description=('Compare two directories (old vs new) and output a JSON summary of file differences.')
    )
    parser.add_argument(
        '--old_dir_path',
        required=True,
        help="Path to the 'old' (existing/customized) webfolder",
    )
    parser.add_argument(
        '--new_dir_path',
        required=True,
        help="Path to the 'new' (upgraded) webfolder",
    )
    parser.add_argument(
        '--output_dir_path',
        required=True,
        help="Directory where the 'diff' subdirectory and JSON output will be written",
    )
    return parser.parse_args()


## manager ----------------------------------------------------------
def main() -> None:
    """
    Runs diff, prints summary, and writes JSON output.

    Called by __main__.
    """
    _configure_logging()
    args: argparse.Namespace = parse_args()

    old_dir: Path = Path(args.old_dir_path)
    new_dir: Path = Path(args.new_dir_path)
    output_dir: Path = Path(args.output_dir_path)

    if not old_dir.is_dir():
        raise SystemExit(f'old_dir_path is not a directory: {old_dir}')
    if not new_dir.is_dir():
        raise SystemExit(f'new_dir_path is not a directory: {new_dir}')

    result: dict[str, list[str]] = diff_directories(old_dir, new_dir)

    # Print summary to stdout
    print_summary(result)

    # Write JSON to timestamped file
    out_path: Path = write_json_output(output_dir, result, old_dir, new_dir)
    print(f'Wrote JSON diff to: {out_path}')


if __name__ == '__main__':
    main()
