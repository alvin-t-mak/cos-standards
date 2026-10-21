# Slack style guide

For every Slack deliverable. `cos-lint` checks the writing rules, and on a Slack path it also checks this shape. Warnings fail on those drafts.

## Rules

1. **Answer first.** The first line is the answer, the decision needed, or the ask. It should make sense if it is the only line read.
2. **No fluff.** No warm-up, no restating the question, no filler sign-off. Say it once.
3. **Short.** Aim for 5 lines or fewer. If it needs more, use a list, or put the detail in a thread reply or a linked doc.
4. **Specific.** Numbers, dates, owners, and links beat adjectives.
5. **Plain words.** No em dashes and no ` -- ` stand-ins. En dashes are fine, spaced or not ("Hey Sam – thanks"), and so is a spaced hyphen. No words from `banned.md`. Prefer the short common word (`use`, not `leverage`).
6. **No semicolons.** A Slack draft uses a period or a new line. A semicolon in inline code is ignored.
7. **Flag an assumption only if it is important.** An assumption is important if, were it wrong, the answer, the number, or the recommendation would change. Test: "If this is false, would I rewrite the message?" If no, leave it out. If yes, add one line at the end: `Assumes X. If not, Y.` Two at most.
8. **Decision requests use this shape:**
   - Line 1: the decision.
   - 2 to 4 numbered options, one line each, with the cost or key tradeoff.
   - Mark exactly one option `(recommended)`.
   - One Why line, and only one line: `Why 1: ...`
   - One default-deadline line: `If no answer by Fri, I go with 1.`
   - Important assumptions, if any (rule 7).

A numbered list, a `(recommended)` mark, a Why line, or a default line opts the draft into the full shape. A status note that uses none of those is not a decision request. It still cannot use a semicolon.

## Examples (made up)

**Example 1: status update**

Before:
```
Hi Dana! Hope you're doing well. I wanted to reach out with a quick update on the Q4 budget. After a deep dive into the numbers, it's important to note that we're tracking over budget, not just in marketing but across several teams. This underscores the need for tighter controls going forward. Let me know if you have any questions!
```

After:
```
Q4 budget is $180K over (4%). $150K is the October event (marketing), $30K is Eng contractors. I'll send a fix by Thursday.
```

**Example 2: decision request**

Before:
```
Great question about the offsite! There are a few options we could consider. We could keep it in Austin, which would be great for morale, or go virtual, which would save money, or push it to Q1. Each option has pros and cons, and ultimately it depends on our priorities. Assuming everyone can travel and the venue is still available, I'd probably lean toward Austin. Hope this helps!
```

After:
```
Need a call on the Jan offsite by Fri. The venue hold expires then.
1. Austin, in person, $85K (recommended)
2. Virtual, $10K
3. Push to Q1, $0 now, goals slip to March
Why 1: the offsite has to produce the goals, and the last two virtual ones ended without a plan.
If no answer by Fri, I go with 1.
Assumes the travel line survives the budget review. If it is cut, I pick 2.
```
