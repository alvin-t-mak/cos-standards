# Slack style guide

For every Slack deliverable. Run `cos-lint` on the file before sending.

## Rules

<!-- rule: slack-answer-first -->
1. **Answer first.** The first line is the answer, the decision needed, or the ask. It should make sense if it's the only line read.
<!-- rule: slack-no-fluff -->
2. **No fluff.** No warm-up ("Hope you're well"), no restating the question, no filler sign-off (`Hope this helps`). Say it once.
<!-- rule: slack-five-lines -->
3. **Short.** Aim for 5 lines or fewer. If it needs more, use `-` bullets, or put the detail in a thread reply or a linked doc.
<!-- rule: slack-specific -->
4. **Specific.** Numbers, dates, owners, and links beat adjectives. "Up 8% vs Q2" not "strong growth".
<!-- rule: slack-plain-words -->
5. **Plain words.** No em dashes and no ` -- ` stand-ins. En dashes are fine, spaced or not ("Hey Sam – thanks"), and so is a spaced hyphen. No words from `banned.md`. Prefer the short common word (`use`, not `leverage`).
<!-- rule: slack-no-semicolon -->
   No semicolons.
<!-- rule: slack-assumptions -->
6. **Flag an assumption only if it's important.** An assumption is important if, were it wrong, the answer, the number, or the recommendation would change. Test: "If this is false, would I rewrite the message?" If no, leave it out. If yes, add one line at the end: `Assumes X. If not, Y.` Two at most.
<!-- rule: slack-decision-request -->
7. **Decision requests use this shape:**
   - Line 1 includes a default-deadline line: `If no answer by Thu, I go with 2.`
   - Numbered options, one line each, with the cost or key tradeoff.
   - Mark one option `(recommended)`.
   - One line saying why.
   - Important assumptions, if any (rule 6).

## Examples (made up for illustration)

**Example 1: status update**

Before:
```
Hi Dana! Hope you're doing well. I wanted to reach out with a quick update on the Q4 budget. After a deep dive into the numbers, it's important to note that we're tracking over budget, not just in marketing but across several teams. This underscores the need for tighter controls going forward. Let me know if you have any questions!
```

After:
```
Q4 budget is $180K over (4%). $150K is the October event (marketing), $30K is Eng contractors. I'll send a fix by Thursday. Let me know if you have any questions.
```

**Example 2: decision request**

Before:
```
Great question about the offsite! There are a few options we could consider. We could keep it in Austin, which would be great for morale, or go virtual, which would save money, or push it to Q1. Each option has pros and cons, and ultimately it depends on our priorities. Assuming everyone can travel and the venue is still available, I'd probably lean toward Austin. Hope this helps!
```

After:
```
Need a call on the Jan offsite. If no answer by Fri, I go with 1. The venue hold expires then.
1. Austin, in person, $85K (recommended)
2. Virtual, $10K
3. Push to Q1, $0 now, 2027 goals slip to March
Why 1: the offsite has to produce 2027 goals, and the last two virtual ones ended without a plan.
Assumes the $90K T&E line survives the budget review. If it's cut, I'd pick 2.
```
