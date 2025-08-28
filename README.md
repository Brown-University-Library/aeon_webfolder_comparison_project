# aeon_webfolder_comparison_project readme

on this page:
- [About](#about)
- [Notes](#notes)
- [TODO](#todo)

---


## About

This is an experimental project to compare Aeon webfolders.

The challenge we have is that we have an existing Aeon webfolder ("old_folder") that has customizations. And we have a new Aeon webfolder ("new_folder") that upgrades various html, css, and js files.

The goal is to update the existing webfolder with the new files, while preserving the customizations.

This repo will contain code for:
- Comparing the two webfolders, producing json indicating files that are different.
- Given a pair of files ("old" and "new"), looking at each diff "hunk", and attempting to determine if the hunk is a customization or an upgrade, or a mix. It will output json indicating a probability that the hunk is a customization or an upgrade, or a mix.
- Running the file-pair comparison in a loop, and outputting json indicating a probability that each file is a customization or an upgrade, or a mix.

---


## Notes

### Running tests...

All examples assume running from the `aeon_webfolder_comparison_project/` directory.

#### Usage -- all tests...
```bash
 uv run -m unittest discover -v -s tests -p 'test_*.py'
 ...or:
 uv run -m unittest discover --verbose --start-directory tests --pattern 'test_*.py'
```

The "discover" option means "discover and run all tests in the 'tests' directory and its subdirectories."

#### Usage -- single test file...

- Single file (by path):
  ```bash
  uv run -m unittest -v tests/test_diff_files.py
  uv run -m unittest -v tests/test_diff_folders.py
  ```

#### Usage -- single test case...

- Single test case (by dotted path):
  ```bash
  uv run -m unittest -v tests.test_diff_files.TestDiffFilesCLIIdentical
  ```

#### Usage -- single test method...

- Single test method (by dotted path):
  ```bash
  uv run -m unittest -v tests.test_diff_files.TestDiffFilesCLIIdentical.test_cli_reports_same_for_identical_files
  ```

---


## TODO

Compare two folders...
- [x] create `a__diff_folders.py` code that will be run via:
    ```
    uv run a__diff_folders.py --old_dir_path "foo" --new_dir_path "bar" --output_dir_path "baz"
    ```
- [x] running that that should show:
    - files in old that are not in new
    - files in new that are not in old
    - files that are different
    - files that are the same
- [x] running that should output json for the above results, saving it to a datestamped file in a "diff" directory.
 - [x] running that should output JSON for the above results, saving it to a datestamped file in a "diffed_dirs" directory.

Compare two files...
- [x] create a test that will run `b__diff_files.py` on a pair of files that are the same, and verify that the output.json indicates they're the same.
- [x] create a test that will run `b__diff_files.py` on a pair of files that are different, and verify that the output.json indicates they're different.
- [x] create `b__diff_files.py` code that will be run via:
    ```
    uv run b__diff_files.py --old_file_path "foo" --new_file_path "bar" --output_dir_path "baz"
    ```
- [x] running that should output JSON for the above results, saving it to a datestamped file in a "diffed_files" directory.

Diff all files...
- [x] create `c__diff_all_files.py` code that will be run via:
    ```
    uv run c__diff_all_files.py --directory_diff_file_path "foo" --output_json_path "bar"
    ```
    This code should:
    - load the `directory_diff_file_path` json file, then 
    - loop over each file in the `different` list, and run `b__diff_files.py` on each file pair, then 
    - assemble the results from each of the diffed-files into a single json file, then 
    - output the big list of results to the `output_json_path` json file.
- [x] running that should output a JSON file for the above results, saving it to a datestamped file in a "diffed_files_combined" directory.

---
