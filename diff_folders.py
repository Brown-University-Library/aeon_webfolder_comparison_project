import argparse
import filecmp
import json
import os
from datetime import datetime
from pathlib import Path


def collect_files(base_dir: Path) -> dict[str, Path]:
    """
    Collects files under base_dir and returns a mapping of relative POSIX paths to absolute Paths.
    Only includes files (not directories).
    """
    base_dir = base_dir.resolve()
    mapping: dict[str, Path] = {}
    for root, _dirs, files in os.walk(base_dir):
        root_path = Path(root)
        for fname in files:
            abs_path = root_path / fname
            rel_path = abs_path.relative_to(base_dir).as_posix()
            mapping[rel_path] = abs_path
    return mapping


def compare_common_files(old_map: dict[str, Path], new_map: dict[str, Path]) -> tuple[list[str], list[str]]:
    """
    Compares content of files present in both maps and returns (same, different) lists.
    Returns:
      - same: list of relative paths with identical content
      - different: list of relative paths with differing content
    """
    same: list[str] = []
    different: list[str] = []

    common_keys = old_map.keys() & new_map.keys()
    for key in sorted(common_keys):
        old_file = old_map[key]
        new_file = new_map[key]
        try:
            # filecmp.cmp with shallow=False compares file content
            if filecmp.cmp(old_file, new_file, shallow=False):
                same.append(key)
            else:
                different.append(key)
        except OSError:
            # If either file can't be read, consider it different and proceed
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
    """
    old_map = collect_files(old_dir)
    new_map = collect_files(new_dir)

    old_keys = set(old_map.keys())
    new_keys = set(new_map.keys())

    old_only = sorted(list(old_keys - new_keys))
    new_only = sorted(list(new_keys - old_keys))

    same, different = compare_common_files(old_map, new_map)

    return {
        'old_only': old_only,
        'new_only': new_only,
        'different': sorted(different),
        'same': sorted(same),
    }


def write_json_output(output_dir: Path, data: dict) -> Path:
    """
    Writes diff results to a timestamped JSON file under output_dir/diff/.

    Args:
        output_dir: Base directory where a 'diff' subfolder will be created.
        data: The diff results to serialize to JSON.

    Returns:
        The path to the written JSON file.
    """
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    diff_dir = output_dir / 'diff'
    diff_dir.mkdir(parents=True, exist_ok=True)
    out_path = diff_dir / f'diff_{timestamp}.json'
    with out_path.open('w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return out_path


def print_summary(result: dict[str, list[str]]) -> None:
    """
    Prints a concise summary of diff results to stdout.
    """
    print('Folder diff results:')
    print(f'- old_only: {len(result["old_only"])}')
    print(f'- new_only: {len(result["new_only"])}')
    print(f'- different: {len(result["different"])}')
    print(f'- same: {len(result["same"])}')


def parse_args() -> argparse.Namespace:
    """
    Parses and returns CLI arguments for directory comparison.
    """
    parser = argparse.ArgumentParser(
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
    """
    args = parse_args()

    old_dir = Path(args.old_dir_path)
    new_dir = Path(args.new_dir_path)
    output_dir = Path(args.output_dir_path)

    if not old_dir.is_dir():
        raise SystemExit(f'old_dir_path is not a directory: {old_dir}')
    if not new_dir.is_dir():
        raise SystemExit(f'new_dir_path is not a directory: {new_dir}')

    result = diff_directories(old_dir, new_dir)

    # Print summary to stdout
    print_summary(result)

    # Write JSON to timestamped file
    out_path = write_json_output(output_dir, result)
    print(f'Wrote JSON diff to: {out_path}')


if __name__ == '__main__':
    main()
