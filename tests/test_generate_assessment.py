"""
Tests assessment generation in `d__generate_assessment.py`.
"""

from __future__ import annotations

import unittest

import d__generate_assessment as gen


class TestHelpers(unittest.TestCase):
    """
    Verifies helper functions behavior.
    """

    def test_iter_changed_lines_yields_only_added_removed(self) -> None:
        """
        Ensures header lines are excluded and signs/content are yielded.
        """
        hunks: list[list[str]] = [
            [
                '--- a/file',
                '+++ b/file',
                '@@ -1,2 +1,2 @@',
                '-old line',
                '+new line',
                ' context',
                '',
                '+another',
            ]
        ]
        out = list(gen.iter_changed_lines(hunks))
        self.assertEqual(out, [('-', 'old line'), ('+', 'new line'), ('+', 'another')])

    def test_find_matches_returns_patterns(self) -> None:
        """
        Ensures regex pattern hits are collected.
        """
        lines = ['Brown Digital Repository here', 'no hit']
        regexes = gen.local_regexes  # includes BDR and Brown
        hits = gen.find_matches(lines, regexes)
        self.assertTrue(any('Brown Digital Repository' in h for h in hits))

    def test_summarize_matched_terms_humanizes(self) -> None:
        """
        Converts regex patterns to friendly tokens and de-duplicates preserving order.
        """
        patterns = [
            r'Brown Digital Repository',
            r'library\.brown\.edu',
            r'library\.brown\.edu',
            r'\bJHL\b',
        ]
        tokens = gen.summarize_matched_terms(patterns)
        self.assertEqual(tokens, ['Brown Digital Repository', 'library.brown.edu', 'JHL'])

    def test_compute_probability_edges(self) -> None:
        """
        Validates 0/0 -> 0.5 and clamped range.
        """
        self.assertAlmostEqual(gen.compute_probability(0, 0, 0), 0.5)
        self.assertAlmostEqual(gen.compute_probability(2, 0, 0), 1.0)
        self.assertLess(gen.compute_probability(1, 3, 0), 0.5)

    def test_build_notes_composes_expected_phrases(self) -> None:
        """
        Produces notes for title change, local terms removed, vendor features, structural and js/min items.
        """
        removed_lines = ['<title>Old Title</title>', 'EADRequest.js']
        added_lines = ['<title>New Title</title>', 'include_scheduled_date.html']
        local_removed = ['\\bBrown\\b']
        vendor_added = ['include_scheduled_date(_ead)?\\.html']
        upgrade_removed: list[str] = []
        upgrade_added = ['\\bISO8601\\b']

        notes = gen.build_notes(
            relpath='templates/example.html',
            removed_lines=removed_lines,
            added_lines=added_lines,
            local_removed=local_removed,
            vendor_added=vendor_added,
            upgrade_hits_removed=upgrade_removed,
            upgrade_hits_added=upgrade_added,
        )
        # Basic signals we expect to see called out
        self.assertIn('title change', notes)
        self.assertIn('removed local terms', notes)
        self.assertIn('vendor features in new version', notes)
        self.assertIn('structural changes', notes)
        self.assertIn('switch to minified EADRequest.min.js', notes)
        self.assertIn('adds include_scheduled_date partial', notes)


if __name__ == '__main__':
    unittest.main()
