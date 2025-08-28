"""
Aggregates per-file diffs for all files listed as different in a directory diff JSON.

Usage:
  uv run c__diff_all_files.py \
    --directory_diff_file_path "/path/to/diffed_dirs/diff_YYYYMMDD-HHMMSS.json" \
    --output_json_path "/absolute/path/to/output_dir/diffed_files_combined/diff_all.json"

Example (using the sample mini JSON in this repo):
  uv run c__diff_all_files.py \
    --directory_diff_file_path "../output_dir/diffed_dirs/mini_output.json" \
    --output_json_path "../output_dir/diffed_files_combined/diff_all_sample.json"

Output (stdout):
  {"output_path": "/absolute/path/to/.../diff_all_YYYYMMDD-HHMMSS.json"}

Environment:
  LOG_LEVEL=[DEBUG|INFO]  (optional; defaults to INFO)
"""

import argparse
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

# Local module import
import b__diff_files as diff_files

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


def _load_directory_diff(path: Path) -> dict[str, Any]:
    """
    Loads and minimally validates the directory diff JSON structure.

    Called by main().
    """
    with path.open('r', encoding='utf-8') as fh:
        data: dict[str, Any] = json.load(fh)

    if 'comparison_directories' not in data or 'results' not in data:
        raise SystemExit('Invalid directory diff JSON: missing required keys')

    comp: dict[str, str] = data['comparison_directories']  # type: ignore[assignment]
    if 'old_dir' not in comp or 'new_dir' not in comp:
        raise SystemExit('Invalid directory diff JSON: missing old_dir/new_dir in comparison_directories')

    results: dict[str, Any] = data['results']  # type: ignore[assignment]
    if 'different' not in results or not isinstance(results['different'], list):
        raise SystemExit("Invalid directory diff JSON: 'results.different' must be a list")

    return data


def _assemble_output_path(output_json_path: Path) -> Path:
    """
    Ensures parent directory exists and returns an absolute file path to write.

    Called by main().
    """
    output_json_path = output_json_path.resolve()

    # If the provided path looks like a directory, synthesize a timestamped filename.
    if output_json_path.suffix.lower() != '.json':
        timestamp: str = datetime.now().strftime('%Y%m%d-%H%M%S')
        output_json_path = (output_json_path / f'diff_all_{timestamp}.json')

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    return output_json_path


def diff_all_files(directory_diff_file: Path, output_json_path: Path) -> Path:
    """
    Runs per-file diffs for each relative path listed in the directory diff JSON's 'different' list.

    Returns the path to the combined JSON written.

    Called by main().
    """
    data: dict[str, Any] = _load_directory_diff(directory_diff_file)

    comp_dirs: dict[str, str] = data['comparison_directories']  # type: ignore[assignment]
    old_dir = Path(comp_dirs['old_dir'])
    new_dir = Path(comp_dirs['new_dir'])

    rel_paths: list[str] = list(data['results']['different'])  # type: ignore[index]

    combined_results: list[dict[str, Any]] = []
    processed: int = 0
    skipped: int = 0

    for rel in rel_paths:
        old_file: Path = (old_dir / rel)
        new_file: Path = (new_dir / rel)
        if not old_file.is_file() or not new_file.is_file():
            log.warning('Skipping missing pair: %s | %s', old_file, new_file)
            skipped += 1
            continue
        try:
            result: dict[str, Any] = diff_files.compare_files(old_file, new_file)
        except Exception as exc:  # noqa: BLE001
            log.exception('Error diffing files %s and %s: %s', old_file, new_file, exc)
            skipped += 1
            continue

        combined_results.append({
            'relative_path': rel,
            'comparison_files': {
                'old_file': str(old_file.resolve()),
                'new_file': str(new_file.resolve()),
            },
            'results': result,
        })
        processed += 1

    payload: dict[str, Any] = {
        'comparison_directories': {
            'old_dir': str(old_dir.resolve()),
            'new_dir': str(new_dir.resolve()),
        },
        'summary': {
            'requested': len(rel_paths),
            'processed': processed,
            'skipped': skipped,
        },
        'files': combined_results,
    }

    out_path: Path = _assemble_output_path(output_json_path)
    with out_path.open('w', encoding='utf-8') as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    return out_path


# cli --------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """
    Parses and returns CLI arguments for aggregating per-file diffs from a directory diff JSON.

    Called by main().
    """
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description=(
            'Given a directory diff JSON (from a__diff_folders.py), run per-file diffs for each entry in the\n'
            "'results.different' list and write a combined JSON report."
        )
    )
    parser.add_argument(
        '--directory_diff_file_path',
        required=True,
        help='Path to the directory-diff JSON produced by a__diff_folders.py',
    )
    parser.add_argument(
        '--output_json_path',
        required=True,
        help=(
            'Target JSON file path to write. If a directory is provided instead of a .json file, '
            'a timestamped filename will be created within it.'
        ),
    )
    return parser.parse_args()


# manager ----------------------------------------------------------


def main() -> None:
    """
    Coordinates reading the directory diff, running all per-file diffs, and writing combined JSON.

    Called by __main__.
    """
    _configure_logging()
    args: argparse.Namespace = parse_args()

    directory_diff_file = Path(args.directory_diff_file_path)
    output_json_path = Path(args.output_json_path)

    if not directory_diff_file.is_file():
        raise SystemExit(f'directory_diff_file_path is not a file: {directory_diff_file}')

    out_path: Path = diff_all_files(directory_diff_file, output_json_path)

    # Print machine-readable location for tests/automation
    print(json.dumps({'output_path': str(out_path)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
