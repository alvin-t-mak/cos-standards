"""Writing-rule behavior. The banned list is the source of truth."""

import unittest

from cos_standards.lint_writing import load_rules, lint_text

RULES = load_rules(None)


def ids(text, severity=None):
    return {hit[4] for hit in lint_text(text, "t", RULES) if severity is None or hit[3] == severity}


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
    "The deal is not only late; it is over budget.",
    "Hey Sam \u2013 thanks for the follow up here.",
    "Revenue is up \u2013 mostly from renewals.",
    "Hey Sam \u2013 thanks, the deck \u2013 mostly done \u2013 is attached.",
    "Sam - for reference. Just in case helpful",
    "Let me know if you have any questions here.",
    "Let me know if you have any questions.",
]


class LintTests(unittest.TestCase):
    def test_rule_count(self):
        self.assertEqual(len(RULES), 60)

    def test_bad_samples_fire(self):
        for text, rule_id in MUST_FAIL:
            with self.subTest(text=text):
                self.assertIn(rule_id, ids(text, "error"))

    def test_normal_sentences_clean(self):
        for text in MUST_PASS_NO_ERRORS:
            with self.subTest(text=text):
                self.assertEqual(ids(text, "error"), set())

    def test_let_me_know_questions_has_no_hits(self):
        self.assertEqual(ids("Let me know if you have any questions."), set())

    def test_anything_else_closer_fails(self):
        self.assertIn("anything-else", ids("Let me know if you need anything else.", "error"))

    def test_en_dash_passes_em_dash_fails(self):
        self.assertEqual(ids("Hey Sam \u2013 thanks for the deck."), set())
        self.assertEqual(ids("Hey Sam \u2014 thanks for the deck.", "error"), {"em-dash"})
        self.assertEqual(ids("Hey Sam -- thanks for the deck.", "error"), {"double-hyphen-dash"})
        self.assertEqual(ids("A horizontal bar \u2015 is banned.", "error"), {"horizontal-bar"})
        self.assertFalse(
            any(rule["id"] in ("spaced-en-dash", "spaced-hyphen-dash") or "\u2013" in rule["pattern"] for rule in RULES)
        )

    def test_code_fence_skipped(self):
        self.assertEqual(ids("```\nLet's delve in \u2014 hope this helps\n```\n"), set())

    def test_ignore_marker(self):
        self.assertEqual(ids("Hope this helps <!-- lint: ignore -->"), set())

    def test_warn_only(self):
        self.assertEqual(ids("We can leverage the existing model.", "error"), set())
        self.assertIn("leverage", ids("We can leverage the existing model.", "warn"))

    def test_all_regexes_compile(self):
        self.assertTrue(all(rule["rx"] for rule in RULES))


if __name__ == "__main__":
    unittest.main(verbosity=1)
