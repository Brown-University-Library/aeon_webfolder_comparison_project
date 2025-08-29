"""
Generates an assessment of the changes between two versions of the Aeon web folder.

From ChatGPT-5-thinking...

```
How I scored “probability_of_customization”

Heuristics favor local/Brown-specific text (e.g., “JHL”, “John Hay”, “BruKnow”,
“library.brown.edu”, “Brown Digital Repository”) showing up in
removed/changed lines → pushes the score up (more likely a prior
customization).

Signals that look like upstream Aeon defaults/features added (e.g.,
transaction-label, include_scheduled_date.html, EADRequest.min.js, “Aeon - …”
titles, date/ISO8601 helpers, removal of hidden Username) push the score down
(more likely vendor upgrade adjustments).

Notes call out the strongest signals (e.g., “title change”, “removed local
terms: …”, “adds include_scheduled_date partial”, “switch to minified
EADRequest.min.js”, etc.).
```

Usage:
- `uv run ./d__generate_assessment.py`
"""

## loads libs
import json
import pathlib
import re
from datetime import datetime
from typing import Any
from collections.abc import Iterator

import polars as pl

## constants
DIFF_INPUT_PATH: pathlib.Path = pathlib.Path('../output_dir/diffed_files_combined/diff_all_real_data.json').resolve()
OUTPUT_DIR: pathlib.Path = pathlib.Path('../output_dir/diffed_reports').resolve()
CSV_FILENAME_TEMPLATE: str = 'aeon_diff_customization_assessment_{timestamp}.csv'
MD_FILENAME_TEMPLATE: str = 'aeon_diff_customization_assessment_{timestamp}.md'

## loads input json (done inside main)

## defines heuristics
local_term_patterns: list[str] = [
    r'\bBrown\b',
    r'BruKnow',
    r'John\s*Hay',
    r'\bJHL\b',
    r'Annex Hay',
    r'Brown Digital Repository',
    r'library\.brown\.edu',
    r'search\.library\.brown\.edu',
    r'\bHay\b(?!\s*Street)',
]

vendor_signal_patterns: list[str] = [
    r'\bAeon\b',
    r'transaction-label',
    r'include_scheduled_date(_ead)?\.html',
    r'EADRequest\.min\.js',
    r'Freqdec Datepicker',
    r'include_ResearcherTags\.html',
    r'convert-local',
    r'\bRequestLinks\b',
    r'hideUsernames',
    r'custom-select',
    r'include_request_buttons\.html',
]

# other structural signals we treat as "upgrade-ish"
upgrade_specific_patterns: list[str] = [
    r'<input[^>]+type="hidden"[^>]+name="Username"',  # removed hidden Username field
    r'\bDatepicker\b',
    r'\bISO8601\b',
]

local_regexes: list[re.Pattern[str]] = [re.compile(p, re.I) for p in local_term_patterns]
vendor_regexes: list[re.Pattern[str]] = [re.compile(p, re.I) for p in vendor_signal_patterns]
upgrade_regexes: list[re.Pattern[str]] = [re.compile(p, re.I) for p in upgrade_specific_patterns]


## helpers
def iter_changed_lines(hunks: list[list[str]]) -> Iterator[tuple[str, str]]:
    for h in hunks:
        # each h is a list of lines; skip the header mini-hunks that start with ---/+++
        # We will yield only lines that begin with '+' or '-' (added/removed content)
        for line in h:
            if not line:
                continue
            if line.startswith('@@') or line.startswith('--- ') or line.startswith('+++ '):
                continue
            if line[0] in '+-':
                yield line[0], line[1:]  # (sign, content-without-sign)


def find_matches(lines: list[str], regexes: list[re.Pattern[str]]) -> list[str]:
    matches: list[str] = []
    for ln in lines:
        for rx in regexes:
            if rx.search(ln):
                matches.append(rx.pattern)
    return matches


def summarize_matched_terms(patterns: list[str]) -> list[str]:
    # compact regex patterns into human-friendly tokens
    tokens: list[str] = []
    for p in patterns:
        if 'Brown Digital Repository' in p:
            tokens.append('Brown Digital Repository')
        elif 'library\\.brown\\.edu' in p:
            tokens.append('library.brown.edu')
        elif 'search\\.library\\.brown\\.edu' in p:
            tokens.append('search.library.brown.edu')
        elif 'BruKnow' in p:
            tokens.append('BruKnow')
        elif 'John\\s*Hay' in p:
            tokens.append('John Hay')
        elif '\\bJHL\\b' in p:
            tokens.append('JHL')
        elif 'Annex Hay' in p:
            tokens.append('Annex Hay')
        elif '\\bBrown\\b' in p:
            tokens.append('Brown')
        elif '\\bHay\\b' in p:
            tokens.append('Hay')
        else:
            tokens.append(p)
    # preserve order but unique
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def build_notes(
    relpath: str | None,
    removed_lines: list[str],
    added_lines: list[str],
    local_removed: list[str],
    vendor_added: list[str],
    upgrade_hits_removed: list[str],
    upgrade_hits_added: list[str],
) -> str:
    notes: list[str] = []
    # title genericization
    title_old: list[str] = [ln for ln in removed_lines if '<title>' in ln or '<title ' in ln]
    title_new: list[str] = [ln for ln in added_lines if '<title>' in ln or '<title ' in ln]
    if title_old or title_new:
        # attempt to extract brief title text
        def strip_html_title(s: str) -> str:
            s2 = re.sub(r'.*<title[^>]*>', '', s, flags=re.I)
            s2 = re.sub(r'</title>.*', '', s2, flags=re.I)
            return s2.strip()[:120]

        if title_old:
            t_old = strip_html_title(title_old[0])
        else:
            t_old: str = ''
        if title_new:
            t_new: str = strip_html_title(title_new[0])
        else:
            t_new: str = ''
        if t_old or t_new:
            notes.append(f'title change: "{t_old}" \u2192 "{t_new}"')
    # local term removal
    if local_removed:
        terms: list[str] = summarize_matched_terms(local_removed)
        notes.append('removed local terms: ' + ', '.join(terms[:6]) + ('…' if len(terms) > 6 else ''))
    # vendor signals added
    if vendor_added:
        terms: list[str] = summarize_matched_terms(vendor_added)
        notes.append('vendor features in new version: ' + ', '.join(terms[:6]) + ('…' if len(terms) > 6 else ''))
    # upgrade-ish pattern hits
    if upgrade_hits_removed or upgrade_hits_added:
        hits = summarize_matched_terms(upgrade_hits_removed + upgrade_hits_added)
        notes.append('structural changes: ' + ', '.join(hits[:6]) + ('…' if len(hits) > 6 else ''))
    # specific include changes
    # js minification switch
    for r in removed_lines:
        if 'EADRequest.js' in r and '.min.js' not in r:
            notes.append('switch to minified EADRequest.min.js')
            break
    # include_scheduled_date usage
    if any('include_scheduled_date' in ln for ln in added_lines):
        notes.append('adds include_scheduled_date partial (appointment date handling)')
    return '; '.join(notes) if notes else ''


def compute_probability(local_removed_count: int, vendor_added_count: int, upgrade_count: int) -> float:
    counter: int = vendor_added_count + upgrade_count
    raw: int = local_removed_count
    if raw == 0 and counter == 0:
        p: float = 0.5
    else:
        p = raw / (raw + counter)
    return max(0.0, min(1.0, p))


def display_dataframe_to_user(title: str, df: pl.DataFrame, max_rows: int = 50) -> None:
    """
    Displays the dataframe in Jupyter when available; otherwise prints a truncated text view.
    """
    try:
        from IPython.display import Markdown, display  # type: ignore

        display(Markdown(f'### {title}'))
        # Prefer rich HTML if pandas is available; otherwise show head()
        try:
            display(df.to_pandas())
        except Exception:
            display(df.head(max_rows))
    except Exception:
        print(f'\n=== {title} ===')
        print(df.head(max_rows))


def main() -> int:
    """
    Orchestrates generation of the customization assessment CSV and Markdown report.
    """

    # load input json
    with DIFF_INPUT_PATH.open('r', encoding='utf-8') as f:
        diff_payload: dict[str, Any] = json.load(f)

    files: list[dict[str, Any]] = diff_payload.get('files', [])

    # process files
    rows: list[dict[str, Any]] = []
    for fobj in files:
        rel: str | None = fobj.get('relative_path')
        res: dict[str, Any] = fobj.get('results', {})
        hunks: list[list[str]] = res.get('unified_diff_hunks') or []
        # flatten changed lines
        added_lines: list[str] = []
        removed_lines: list[str] = []
        for sign, content in iter_changed_lines(hunks):
            if sign == '+':
                added_lines.append(content)
            elif sign == '-':
                removed_lines.append(content)
        # find matches
        local_removed: list[str] = find_matches(removed_lines, local_regexes)
        vendor_added: list[str] = find_matches(added_lines, vendor_regexes)
        upgrade_hits_removed: list[str] = find_matches(removed_lines, upgrade_regexes)
        upgrade_hits_added: list[str] = find_matches(added_lines, upgrade_regexes)
        # compute probability
        p: float = compute_probability(
            len(local_removed),
            len(vendor_added),
            len(upgrade_hits_removed) + len(upgrade_hits_added),
        )
        # build notes
        notes: str = build_notes(
            rel,
            removed_lines,
            added_lines,
            local_removed,
            vendor_added,
            upgrade_hits_removed,
            upgrade_hits_added,
        )
        # finalize
        rows.append(
            {
                'file_path': rel,
                'probability_of_customization': round(p * 100, 1),  # percent
                'notes': notes,
            }
        )

    df: pl.DataFrame = (
        pl.DataFrame(rows)
        .sort(by=['probability_of_customization', 'file_path'], descending=[True, False])
    )

    # saves csv
    timestamp: str = datetime.now().strftime('%Y%m%d-%H%M%S')
    csv_path: pathlib.Path = OUTPUT_DIR / CSV_FILENAME_TEMPLATE.format(timestamp=timestamp)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.write_csv(str(csv_path))

    # builds markdown report
    md_lines: list[str] = []
    md_lines.append('# Aeon diff: customization likelihood report\n')
    md_lines.append(
        'This report scores each changed file on the likelihood that differences reflect **local customizations** (vs vendor **upgrade** changes).'
    )
    md_lines.append(
        '\n**How to read**: higher percentages suggest text that looks Brown/JHL-specific was removed/changed; lower percentages suggest generic Aeon features were added or structural changes came from upstream.\n'
    )
    md_lines.append('---\n')

    for row in df.iter_rows(named=True):
        md_lines.append(f'## {row["file_path"]}')
        md_lines.append(f'- **probability_of_customization**: {row["probability_of_customization"]:.1f}%')
        note_txt: str = row['notes'] or '(no notable signals detected)'
        md_lines.append(f'- **notes**: {note_txt}\n')

    md_text: str = '\n'.join(md_lines)

    md_path: pathlib.Path = OUTPUT_DIR / MD_FILENAME_TEMPLATE.format(timestamp=timestamp)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    with md_path.open('w', encoding='utf-8') as f:
        f.write(md_text)

    # displays dataframe to user
    display_dataframe_to_user('Aeon diff customization assessment', df)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
