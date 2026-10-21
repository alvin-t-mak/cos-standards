<!-- lint: ignore-file (this file quotes banned text on purpose) -->
# Banned list for written deliverables

Machine-readable source: `src/cos_standards/data/banned.yaml` (mirrored to `banned.json`).
Checker: `cos-lint`. A consuming repo may add rules. It cannot delete or weaken these.

## How the rules work

- All matching is case-insensitive. Curly apostrophes are treated as straight ones.
- `literal` rules match the exact text, with word boundaries added at letter or digit edges.
- `regex` rules are Python `re` patterns.
- Optional `allow` regex on a rule: a hit that sits entirely inside an `allow` match is skipped.
- `error` fails the lint (exit code 1). `warn` is reported only. Strict mode, which deliverables use, makes warnings fail.
- Skipped: fenced code blocks, inline code in backticks, and any line containing `lint: ignore`.
- Matching is per line, so a phrase split across a hard line wrap is missed. Slack messages rarely wrap, so this is accepted.
- `lint: ignore` and `lint: ignore-file` exist so a standards file can quote a banned phrase. They are not a config exemption. Local config has no exemption key. This file uses `lint: ignore-file` because it quotes banned text.

## Counts

| Category | Severity | Rules |
| --- | --- | --- |
| Punctuation (dashes) | error | 3 |
| (a) Hard-ban words and phrases | error | 25 |
| (b) Hard-ban structural patterns | error | 12 |
| (c) Warn only | warn | 20 |
| Total | | 60 |

Not covered by regex (check by eye): rule-of-three lists for rhythm, bold inline-header bullet lists in short messages, emoji bullets, Title Case Headings in a Slack message, vague attributions ("experts say", "industry reports"), and generic praise that could apply to any topic.

## Punctuation (dashes)

Em dashes and double-hyphen stand-ins are banned. En dashes are allowed everywhere, spaced or not ("Hey Sam – thanks", "2024–2026"), and so is a spaced single hyphen. Code and CLI flags in backticks are skipped.

- **em-dash** (error): `U+2014` (literal). Em dash. Banned outright. Use a period, comma, colon, or parentheses.
- **horizontal-bar** (error): `U+2015` (literal). Horizontal bar, an em dash lookalike. Same rule as em dash.
- **double-hyphen-dash** (error): `(?<=\S) -- (?=\S)|(?<=\S) --$|(?<=[a-z])--(?=[a-z])` (regex). Double hyphen used as an em dash substitute. Code and CLI flags inside backticks are skipped.

## (a) Hard-ban words and phrases

Almost never legitimate in a terse business Slack message. Severity: error.

- **delve**: `\bdelv(e|es|ed|ing)\b` (regex). Most cited LLM tell. Say 'look at' or 'dig into', or just state the finding.
- **tapestry**: `tapestry` (literal). Figurative 'tapestry' is a classic LLM tell. Never needed in business writing.
- **testament-to**: `\btestament to\b` (regex). Puffery. State the fact that proves the point.
- **important-to-note**: `\b(it's|it is|it's also|it is also) (important|worth|crucial|essential) (to note|noting|to remember|to mention|to highlight)\b` (regex). Throat-clearing. If it matters, just say it.
- **worth-noting**: `\b(worth noting|notably,|importantly,)` (regex). Throat-clearing preamble before the actual point.
- **fast-paced-world**: `\bin today's (fast-paced|ever-changing|ever-evolving|rapidly evolving|rapidly changing|digital|modern|competitive) (world|landscape|environment|age|era|market|business environment)\b` (regex). Empty scene-setting opener.
- **ever-evolving**: `\bever-(evolving|changing)\b` (regex). Filler adjective common in LLM output.
- **navigate-complexities**: `\bnavigat(e|es|ed|ing) (the )?(complexities|intricacies|nuances|landscape|challenges)\b` (regex). Vague LLM phrasing. Name the actual problem and the action.
- **intricacies**: `\bintricac(y|ies)\b` (regex). LLM vocabulary. Say what is complicated and why.
- **underscore-verb**: `\bunderscor(e|es|ed|ing) (the|its|their|our|your|his|her|how|that|why|this|these|a|an)\b` (regex). Figurative 'underscores' is a top LLM tell. Literal underscore characters are not flagged.
- **plays-pivotal-role**: `\bplay(s|ed|ing)? an? (pivotal|crucial|vital|key|critical|significant) role\b` (regex). Puffery. Say what it actually does.
- **realm**: `\b(in|within) the (realm|world|landscape) of\b` (regex). Padding phrase. Drop it and name the thing.
- **embark-journey**: `\b(embark(s|ed|ing)? on|journey of|on a journey)\b` (regex). Travel metaphor for ordinary work.
- **unlock-potential**: `\b(unlock|unleash|harness)(es|ed|ing|s)? (the )?(full |true )?(power|potential)\b` (regex). Marketing cliche.
- **game-changer**: `\bgame[- ]chang(er|ers|ing)\b` (regex). Hype word. Quantify the change instead.
- **plethora**: `\b(a )?(plethora|myriad|multitude) of\b|\bmyriad\b` (regex). Inflated quantifier. Give the number or say 'many'.
- **cannot-be-overstated**: `\bcan(not|'t) be overstated\b` (regex). Empty emphasis.
- **goes-without-saying**: `\b(it goes without saying|needless to say|rest assured)\b` (regex). If it goes without saying, don't say it.
- **commendable**: `\b(commendable|meticulous(ly)?|unwavering|indelible)\b` (regex). Top-ranked LLM-overused adjectives in published word-frequency studies.
- **travel-guide-adjectives**: `\b(vibrant|bustling|nestled|breathtaking|rich cultural heritage)\b` (regex). Promotional, travel-guide tone. Never right in a work message.
- **valuable-insights**: `\bactionable insights?\b|\b(provid|offer|gain|yield|deliver)\w* (some |key |deep |rich )?valuable insights?\b` (regex). Says nothing. State the insight.
- **dive-in**: `\blet's (dive|jump|dig) (in|into|right in)\b|\blet's break (it|this|that) down\b` (regex). Chatbot transition. Start with the content.
- **in-conclusion**: `\b(in conclusion|to sum up|in summary|to summarize|all in all),` (regex). Essay-style wrap-up. Slack messages don't need a conclusion paragraph.
- **ai-self-reference**: `\bas an ai\b|\bas a (large )?language model\b|\bas of my (last )?(knowledge )?(update|cutoff|training)\b` (regex). Leaked chatbot disclaimer.
- **limited-info-hedge**: `\b(while|although) (specific )?(details|information) (is|are) (limited|scarce)\b|\bbased on (the )?(available|provided) information\b` (regex). Chatbot hedge about sources. Say what you know and what you don't.

## (b) Hard-ban structural patterns

Sentence shapes, sycophantic openers, filler closers, and chatbot artifacts. Severity: error.

- **not-just-x-but-y**: `\bnot (just|only|merely|simply)\b[^.!?\n]{1,80}?\bbut\b` (regex). 'Not just X but Y' negative parallelism. Say Y directly.
- **sycophantic-question-praise**: `\b(great|excellent|fantastic|wonderful|thoughtful|insightful) (question|point)\b|\bwhat a (great|good|thoughtful) (question|point)\b` (regex). Sycophantic opener. Answer the question.
- **youre-absolutely-right**: `\byou're (absolutely|totally|completely|so) right\b|\byou raise (a|an) (great|good|valid|excellent|fair) point\b` (regex). Sycophantic agreement. State what you agree with and why, or skip it.
- **chatbot-opener**: `^\s*(certainly|absolutely|of course|sure thing)!` (regex). Chatbot opener with exclamation. Start with the answer.
- **happy-to-help**: `\b(i'd|i would|i'm|i am) (be )?(happy|glad|delighted) to help\b` (regex). Assistant-voice filler.
- **hope-message-finds**: `\bhope (this|the|my) (message|email|note) finds you\b|\bi hope you('re| are) (doing )?well\b` (regex). Email-template opener. Not used in Slack.
- **hope-this-helps**: `\b(i )?hope (this|that) (helps|was helpful|is helpful|clarifies)\b` (regex). Filler closer.
- **feel-free**: `\b(feel free|don't hesitate|do not hesitate) to (reach out|ask|contact|let me know|ping)\b` (regex). Filler closer.
- **anything-else**: `\b(let me know if|if) (you need|there's|there is) anything else\b` (regex). Assistant-style closer. End when the message is done.
- **heres-the-breakdown**: `^\s*here's (a|the|my) (quick |brief |detailed )?(breakdown|rundown|overview|summary)\b` (regex). Chatbot preamble. Lead with the content itself.
- **placeholder-left-in**: `\[(your name|insert [^\]]*|name|company( name)?|date|recipient|link)\](?!\()` (regex). Unfilled template placeholder.
- **citation-artifact**: `oaicite|oai_citation|contentReference\[|turn\d+search\d+|utm_source=chatgpt\.com` (regex). Leaked chatbot citation markup.

## (c) Warn only

Sometimes legitimate. Reported, and they do not fail the lint unless the run is strict. Deliverables run strict, so a warning there fails the check.

- **leverage** (warn): `\bleverag(e|es|ed|ing)\b` (regex). Fine for financial leverage. As a verb, 'use' is usually better.
- **robust** (warn): `robust` (literal). Often vague. OK if you mean statistically or operationally robust and can say how.
- **seamless** (warn): `\bseamless(ly)?\b` (regex). Usually a claim with no evidence. Say what actually changes for the user.
- **pivotal-crucial** (warn): `\b(pivotal|crucial|vital|paramount)\b` (regex). Inflated importance. Fine once; a tell when repeated.
- **foster-enhance** (warn): `\b(foster|enhanc|elevat|empower|bolster|streamlin|facilitat)\w*` (regex). LLM-favored verbs. Prefer a concrete verb: build, cut, speed up, add.
- **showcase-highlight** (warn): `\b(showcas|highlight)\w*` (regex). Often superficial analysis. OK when literally highlighting something.
- **landscape** (warn): `landscape` (literal). Abstract 'landscape' is LLM vocabulary. Say 'market' or name the competitors.
- **holistic-synergy** (warn): `\b(holistic(ally)?|synerg(y|ies|istic)|multifaceted|paradigm shift|cutting[- ]edge|groundbreaking|transformative|innovative)\b` (regex). Buzzword. Replace with the specific claim.
- **comprehensive** (warn): `\bcomprehensive(ly)?\b` (regex). Usually unearned. Say what is covered.
- **utilize** (warn): `\butiliz(e|es|ed|ing|ation)\b` (regex). Use 'use'.
- **deep-dive** (warn): `\bdeep[- ]dive\b|\bdive (deeper )?into\b` (regex). Common in business speech, but an LLM favorite. Say 'review' or 'analysis'.
- **transition-adverbs** (warn): `(?:^|(?<=[.!?:] )|(?<=- )|(?<=\* ))(additionally|moreover|furthermore|ultimately|overall|essentially),` (regex). Sentence-opening connector typical of LLM prose. Usually deletable.
- **serves-as** (warn): `\b(serves|stands|functions) as (a|an|the)\b` (regex). Avoids plain 'is'. Usually 'is' is better.
- **isnt-just** (warn): `\b(isn't|aren't|wasn't|doesn't|don't|is not|are not) (just|only|merely|simply) (a|an|the|about)\b` (regex). Negative parallelism setup. Often the start of 'it's not X, it's Y'.
- **its-not-x-its-y** (warn): `\b(it's|it is|this is|that's) not [^.!?\n]{1,50}?[,;:] (it's|it is|this is|that's)\b` (regex). 'It's not X, it's Y' reframe. Legit for corrections, a tell when used for emphasis.
- **trailing-ing-analysis** (warn): `,\s+(highlighting|underscoring|emphasizing|showcasing|reflecting|symbolizing|fostering|cementing|solidifying)\b` (regex). Tacked-on '-ing' clause that adds vague significance.
- **corporate-filler** (warn): `\b(circle back|touch base|move the needle|at the end of the day|going forward|moving forward|in order to)\b` (regex). Filler. Usually deletable or replaceable with one word.
- **just-wanted-to** (warn): `\b(i )?just wanted to (reach out|follow up|check in|touch base|flag|let you know)\b|\bi wanted to reach out\b` (regex). Soft preamble. Start with the ask or the update.
- **genuinely-truly** (warn): `\b(genuinely|truly|incredibly|deeply)\b` (regex). Intensifier that weakens the claim. Delete and reread.
- **offer-closer-question** (warn): `\bwould you like me to\b|\blet me know if you'd like me to\b` (regex). Classic chatbot closer. Fine as a real question to your boss; cut it if it's reflexive.

## Sources

- Wikipedia, "Signs of AI writing" (AI vocabulary, negative parallelisms, superficial analysis, promotional tone, chatbot phrasing, placeholder text, citation artifacts): https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing
- Matsui, K. (2024). "Delving into PubMed Records: Some Terms in Medical Writing Have Drastically Changed after the Arrival of ChatGPT." medRxiv: https://www.medrxiv.org/content/10.1101/2024.05.14.24307373v2.full
- Kobak et al., excess-vocabulary analysis of biomedical abstracts: https://github.com/berenslab/chatgpt-excess-words
- Juzek and Ward (2024). "Why Does ChatGPT 'Delve' So Much? Exploring the Sources of Lexical Overrepresentation in Large Language Models." arXiv: https://arxiv.org/html/2412.11385
- Embryo, "A list of words that AI over-uses": https://embryo.com/blog/list-words-ai-overuses/

Approach (deterministic lint rules for agent and human writing) inspired by Lauren (@poteto)'s agent setup.
