# lint: ignore-file
import json
import os
import unittest

from cos_standards import lint_writing as lw

RULES = lw.load_rules(None)


def ids(text, severity=None):
    return {h[4] for h in lw.lint_text(text, "t", RULES) if severity is None or h[3] == severity}


MUST_FAIL = [
    ("Revenue is up\u2014mostly from renewals.", "em-dash"),
    ("Revenue is up -- mostly from renewals.", "double-hyphen-dash"),
    ("Revenue is up--mostly from renewals.", "double-hyphen-dash"),
    ("Let's delve into the numbers.", "delve"),
    ("This is a testament to the team's hard work.", "testament-to"),
    ("It\u2019s important to note that Q3 slipped.", "important-to-note"),
    ("In today's fast-paced world, speed matters.", "fast-paced-world"),
    ("We need to navigate the complexities of the merger.", "navigate-complexities"),
    ("The data underscores the need for more headcount.", "underscore-verb"),
    ("This is not just a cost issue but a culture issue.", "not-just-x-but-y"),
    ("Not only did we hit plan, but we beat it by 4%.", "not-just-x-but-y"),
    ("Great question! The deadline is Friday.", "sycophantic-question-praise"),
    ("You're absolutely right, we should move it.", "youre-absolutely-right"),
    ("Certainly! Here is the summary.", "chatbot-opener"),
    ("Hope this helps!", "hope-this-helps"),
    ("Rest assured, it will ship.", "goes-without-saying"),
    ("Feel free to reach out with anything.", "feel-free"),
    ("Here's a quick breakdown of the options:", "heres-the-breakdown"),
    ("Thanks, [Your Name]", "placeholder-left-in"),
    ("The CFO plays a pivotal role in planning.", "plays-pivotal-role"),
    ("A rich tapestry of stakeholders.", "tapestry"),
    ("In conclusion, we should hire.", "in-conclusion"),
    ("I hope this message finds you well.", "hope-message-finds"),
]

SEMICOLON_WITHOUT_BUT = "The deal is not only late; it is over budget."
SPACED_EN_DASH = "Hey Sam \u2013 thanks for the follow up here."

MUST_PASS_NO_ERRORS = [
    "Revenue was $4.2M in Q3, up 8% from Q2.",
    "The 2024\u20132026 plan assumes 3 new hires.",
    "Run `python build_model.py --year 2026 -- --dry-run` to regenerate the model.",
    "Use underscores in file names, e.g. q3_model.xlsx.",
    "Not ready yet. Legal still has the contract.",
    "We did not hit plan, but churn was flat.",
    "It's not ready; legal still has the contract.",
    "Good catch, I fixed the formula in row 12.",
    "Can you send me the deck by 3pm?",
    "I don't just need the number, I need the source.",
    "The board meets on Thursday; I will send the pre-read Wednesday.",
    "See the [link](https://example.com) for details.",
    "Options: 1) hire now, 2) wait for Q1.",
    "We cut 12 vendors and saved $340K.",
    "- Pipeline: 14 deals, $2.1M weighted",
    "Notes from today's staff meeting are below.",
    "We should delegate the vendor review to Sam.",
    SEMICOLON_WITHOUT_BUT,
    SPACED_EN_DASH,
    "Revenue is up \u2013 mostly from renewals.",
    "Hey Sam \u2013 thanks, the deck \u2013 mostly done \u2013 is attached.",
    "Sam - for reference. Just in case helpful",
    "Let me know if you have any questions here.",
    "Let me know if you have any questions.",
]


class LintTests(unittest.TestCase):
    def test_bad_samples_fire(self):
        for text, rid in MUST_FAIL:
            with self.subTest(text=text):
                self.assertIn(rid, ids(text, "error"))

    def test_normal_sentences_clean(self):
        for text in MUST_PASS_NO_ERRORS:
            with self.subTest(text=text):
                self.assertEqual(ids(text, "error"), set())

    def test_en_dash_passes_em_dash_fails(self):
        self.assertEqual(ids("Hey Sam \u2013 thanks for the deck."), set())
        self.assertEqual(ids("Hey Sam \u2014 thanks for the deck.", "error"), {"em-dash"})
        self.assertEqual(ids("Hey Sam -- thanks for the deck.", "error"), {"double-hyphen-dash"})
        self.assertFalse(any(r["id"] in ("spaced-en-dash", "spaced-hyphen-dash") or "\u2013" in r["pattern"] for r in RULES))

    def test_code_fence_skipped(self):
        self.assertEqual(ids("```\nLet's delve in \u2014 hope this helps\n```\n"), set())

    def test_ignore_marker(self):
        self.assertEqual(ids("Hope this helps <!-- lint: ignore -->"), set())

    def test_warn_only(self):
        self.assertEqual(ids("We can leverage the existing model.", "error"), set())
        self.assertIn("leverage", ids("We can leverage the existing model.", "warn"))

    def test_anchored_words_pass(self):
        samples = [
            "Take the elevator to the fourth floor.",
            "The elevation of the site is 200 feet.",
            "Foster sent the model yesterday.",
            "Capacity utilization was 80%.",
            "Pass me the highlighter.",
            "Use a syntax highlight on the input cells.",
            "Highlight the variance in the note.",
        ]
        for text in samples:
            with self.subTest(text=text):
                self.assertEqual(ids(text), set())

    def test_anchored_words_still_warn(self):
        samples = [
            ("We should foster trust on the team.", "foster-enhance"),
            ("This will elevate the brand.", "foster-enhance"),
            ("Please utilize the template.", "utilize"),
            ("The row is highlighted in the spec.", "showcase-highlight"),
            ("The page is showcasing the new offer.", "showcase-highlight"),
        ]
        for text, rid in samples:
            with self.subTest(text=text):
                self.assertIn(rid, ids(text, "warn"))

    def test_python_string_dashes(self):
        bad = 'label = "Revenue is up \u2014 mostly from renewals."\n'
        self.assertIn("em-dash", {h[4] for h in lw.lint_python(bad, "t.py", RULES)})
        commented = '# Revenue is up \u2014 mostly\nx = "fine"\n'
        self.assertEqual(lw.lint_python(commented, "t.py", RULES), [])
        doubled = 'note = "Revenue is up -- mostly from renewals."\n'
        self.assertIn("double-hyphen-dash", {h[4] for h in lw.lint_python(doubled, "t.py", RULES)})
        phrase = 'note = "Please utilize the template."\n'
        self.assertIn("utilize", {h[4] for h in lw.lint_python(phrase, "t.py", RULES)})
        commented_phrase = '# Please utilize the template.\nx = "fine"\n'
        self.assertEqual(
            [h for h in lw.lint_python(commented_phrase, "t.py", RULES) if h[4] == "utilize"],
            [],
        )
        ignored = 'ws.page_setup.orientation = "landscape"  # lint: ignore\n'
        self.assertEqual(lw.lint_python(ignored, "t.py", RULES), [])
        bare = 'ws.page_setup.orientation = "landscape"\n'
        self.assertIn("landscape", {h[4] for h in lw.lint_python(bare, "t.py", RULES)})

    def test_html_dashes(self):
        self.assertIn("em-dash", {h[4] for h in lw.lint_text("<p>Revenue is up \u2014 mostly.</p>", "t.html", lw.dash_rules(RULES))})
        self.assertEqual(lw.lint_text("<p>Hey Sam \u2013 thanks.</p>", "t.html", lw.dash_rules(RULES)), [])

    def test_all_regexes_compile(self):
        self.assertTrue(all(r["rx"] for r in RULES))

    def test_curly_apostrophe_keeps_the_column(self):
        curly = "It\u2019s important to note that Q3 slipped."
        straight = "It's important to note that Q3 slipped."
        curly_hit = next(hit for hit in lw.lint_text(curly, "t", RULES) if hit[4] == "important-to-note")
        straight_hit = next(hit for hit in lw.lint_text(straight, "t", RULES) if hit[4] == "important-to-note")
        self.assertEqual(curly_hit[2], straight_hit[2])
        self.assertEqual(len(curly), len(straight))

    def test_multiline_string_hit_uses_the_opening_line(self):
        source = 'note = """\nPlease utilize the template.\n"""\n'
        hits = lw.lint_python(source, "t.py", RULES)
        self.assertTrue(hits)
        self.assertTrue(all(hit[1] == 1 for hit in hits))

    def test_ignore_file_marker_is_only_read_in_the_opening_lines(self):
        skipped = ["fine\n"] * (lw.IGNORE_FILE_SCAN_LINES - 1)
        skipped.append("lint: ignore-file\n")
        skipped.append("Let's delve into it.\n")
        self.assertEqual(lw.lint_text("".join(skipped), "t", RULES), [])
        visible = ["fine\n"] * lw.IGNORE_FILE_SCAN_LINES
        visible.append("lint: ignore-file\n")
        visible.append("Let's delve into it.\n")
        self.assertIn("delve", ids("".join(visible), "error"))

    def test_banned_json_matches_yaml(self):
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML is required to check banned.json stays in sync with banned.yaml")
        here = lw.HERE
        with open(os.path.join(here, "banned.yaml"), encoding="utf-8") as f:
            from_yaml = yaml.safe_load(f)
        with open(os.path.join(here, "banned.json"), encoding="utf-8") as f:
            from_json = json.load(f)
        self.assertEqual(from_yaml, from_json)


if __name__ == "__main__":
    unittest.main(verbosity=1)
