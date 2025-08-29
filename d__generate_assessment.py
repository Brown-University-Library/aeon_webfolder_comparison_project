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

import pandas as pd

## constants
DIFF_INPUT_PATH = pathlib.Path('../output_dir/diffed_files_combined/diff_all_real_data.json').resolve()
OUTPUT_DIR = pathlib.Path('../output_dir').resolve()
CSV_FILENAME_TEMPLATE = 'aeon_diff_customization_assessment_{timestamp}.csv'
MD_FILENAME_TEMPLATE = 'aeon_diff_customization_assessment_{timestamp}.md'

## loads input json
with DIFF_INPUT_PATH.open('r', encoding='utf-8') as f:
    diff_payload = json.load(f)

files = diff_payload.get('files', [])

## defines heuristics
local_term_patterns = [
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

vendor_signal_patterns = [
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
upgrade_specific_patterns = [
    r'<input[^>]+type="hidden"[^>]+name="Username"',  # removed hidden Username field
    r'\bDatepicker\b',
    r'\bISO8601\b',
]

local_regexes = [re.compile(p, re.I) for p in local_term_patterns]
vendor_regexes = [re.compile(p, re.I) for p in vendor_signal_patterns]
upgrade_regexes = [re.compile(p, re.I) for p in upgrade_specific_patterns]


## helpers
def iter_changed_lines(hunks):
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


def find_matches(lines, regexes):
    matches = []
    for ln in lines:
        for rx in regexes:
            if rx.search(ln):
                matches.append(rx.pattern)
    return matches


def summarize_matched_terms(patterns):
    # compact regex patterns into human-friendly tokens
    tokens = []
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
    seen = set()
    out = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def build_notes(relpath, removed_lines, added_lines, local_removed, vendor_added, upgrade_hits_removed, upgrade_hits_added):
    notes = []
    # title genericization
    title_old = [ln for ln in removed_lines if '<title>' in ln or '<title ' in ln]
    title_new = [ln for ln in added_lines if '<title>' in ln or '<title ' in ln]
    if title_old or title_new:
        # attempt to extract brief title text
        def strip_html_title(s):
            s2 = re.sub(r'.*<title[^>]*>', '', s, flags=re.I)
            s2 = re.sub(r'</title>.*', '', s2, flags=re.I)
            return s2.strip()[:120]

        if title_old:
            t_old = strip_html_title(title_old[0])
        else:
            t_old = ''
        if title_new:
            t_new = strip_html_title(title_new[0])
        else:
            t_new = ''
        if t_old or t_new:
            notes.append(f'title change: "{t_old}" → "{t_new}"')
    # local term removal
    if local_removed:
        terms = summarize_matched_terms(local_removed)
        notes.append('removed local terms: ' + ', '.join(terms[:6]) + ('…' if len(terms) > 6 else ''))
    # vendor signals added
    if vendor_added:
        terms = summarize_matched_terms(vendor_added)
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


def compute_probability(local_removed_count, vendor_added_count, upgrade_count):
    counter = vendor_added_count + upgrade_count
    raw = local_removed_count
    if raw == 0 and counter == 0:
        p = 0.5
    else:
        p = raw / (raw + counter)
    return max(0.0, min(1.0, p))


def display_dataframe_to_user(title: str, df: pd.DataFrame, max_rows: int = 50) -> None:
    """
    Displays the dataframe in Jupyter when available; otherwise prints a truncated text view.
    """
    try:
        from IPython.display import Markdown, display  # type: ignore

        display(Markdown(f'### {title}'))
        display(df)
    except Exception:
        print(f'\n=== {title} ===')
        with pd.option_context(
            'display.max_rows',
            max_rows,
            'display.max_columns',
            None,
            'display.width',
            120,
        ):
            print(df)


## processes files
rows = []
for f in files:
    rel = f.get('relative_path')
    res = f.get('results', {})
    hunks = res.get('unified_diff_hunks') or []
    # flatten changed lines
    added_lines = []
    removed_lines = []
    for sign, content in iter_changed_lines(hunks):
        if sign == '+':
            added_lines.append(content)
        elif sign == '-':
            removed_lines.append(content)
    # find matches
    local_removed = find_matches(removed_lines, local_regexes)
    local_added = find_matches(added_lines, local_regexes)  # rarely relevant
    vendor_added = find_matches(added_lines, vendor_regexes)
    upgrade_hits_removed = find_matches(removed_lines, upgrade_regexes)
    upgrade_hits_added = find_matches(added_lines, upgrade_regexes)
    # compute probability
    p = compute_probability(len(local_removed), len(vendor_added), len(upgrade_hits_removed) + len(upgrade_hits_added))
    # build notes
    notes = build_notes(
        rel, removed_lines, added_lines, local_removed, vendor_added, upgrade_hits_removed, upgrade_hits_added
    )
    # finalize
    rows.append(
        {
            'file_path': rel,
            'probability_of_customization': round(p * 100, 1),  # percent
            'notes': notes,
        }
    )

df = (
    pd.DataFrame(rows)
    .sort_values(by=['probability_of_customization', 'file_path'], ascending=[False, True])
    .reset_index(drop=True)
)

## saves csv
timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
csv_path = OUTPUT_DIR / CSV_FILENAME_TEMPLATE.format(timestamp=timestamp)
csv_path.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(csv_path, index=False)

## builds markdown report
md_lines = []
md_lines.append('# Aeon diff: customization likelihood report\n')
md_lines.append(
    'This report scores each changed file on the likelihood that differences reflect **local customizations** (vs vendor **upgrade** changes).'
)
md_lines.append(
    '\n**How to read**: higher percentages suggest text that looks Brown/JHL-specific was removed/changed; lower percentages suggest generic Aeon features were added or structural changes came from upstream.\n'
)
md_lines.append('---\n')

for _, row in df.iterrows():
    md_lines.append(f'## {row["file_path"]}')
    md_lines.append(f'- **probability_of_customization**: {row["probability_of_customization"]:.1f}%')
    note_txt = row['notes'] or '(no notable signals detected)'
    md_lines.append(f'- **notes**: {note_txt}\n')

md_text = '\n'.join(md_lines)

md_path = OUTPUT_DIR / MD_FILENAME_TEMPLATE.format(timestamp=timestamp)
md_path.parent.mkdir(parents=True, exist_ok=True)
with md_path.open('w', encoding='utf-8') as f:
    f.write(md_text)

## displays dataframe to user
display_dataframe_to_user('Aeon diff customization assessment', df)

csv_path, md_path
