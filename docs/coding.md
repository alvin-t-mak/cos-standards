# Coding standards

These rules apply in addition to the principles in [`principles.md`](principles.md). A shared principle still governs the work. Read that file first.

They apply when a change touches a file whose extension is listed in [`../standards/code-scope.yaml`](../standards/code-scope.yaml).

A Lightfield automation code step counts as code, in addition to the spec rules in [`lightfield-automations.md`](lightfield-automations.md). The step has no file extension in this repo, so `standards/code-scope.yaml` does not match it and CI does not see it. These rules still apply when you write or edit that step.

The no-comments rule in `principles.md` stays as written. It covers every extension on the list, including SQL. It is stricter than a doc-comment keep list, and this file does not add one.

`standards/code-scope.yaml` is the list the comment check reads. `.pyi`, `.pyw`, `.mts`, `.cts`, `.zsh`, and `.ksh` stay on it because that check already scanned them.

<!-- rule: type-system-discipline -->
## Type system discipline

*From: Type System Discipline and typescript-best-practices.*

**Rule:** Make an illegal value hard to build, and parse external data into a typed value before the rest of the program sees it.

**Use when:** a signature, a parser, a config load, or a new variant.

**Do:**
- Parse at the boundary. JSON, config, CLI args, environment, rows, and request bodies stay untrusted until a parse function returns a named type.
- Do not use `any`. Do not use `as` or `cast` on a value that parse did not validate.
- Brand two ids that share a primitive and must not be mixed, and validate once at creation.
- Prefer a shape that cannot hold the illegal combination: a discriminant, a non-empty tuple, a start plus a duration.
- Handle every variant. In TypeScript, assign the value to `never` in the default arm. In Python, cover the union in a match.
- A `# type: ignore` or `@ts-expect-error` does not validate the value. The comment rule still allows the bare directive. Write a parse instead.

**Steer:** "apply type system discipline. parse the payload at the edge and drop the cast."

<!-- rule: boundary-discipline -->
## Boundary discipline

*From: Boundary Discipline.*

**Rule:** Validate where data enters. Trust the typed value inside. Keep the decision in a pure function and the shell thin.

**Use when:** wiring a CLI, a config file, a network call, or an external API.

**Do:**
- Validate at the edge and return the error there.
- Inside the system, do not validate the same value again.
- Do not re-export a transport, storage, or wire type as the public surface.
- Ask whether this value is crossing a boundary right now. If it is not, the extra check is noise.
- Ask whether this can be a pure function the shell calls. If it can, extract it.

**Steer:** "apply boundary discipline. validate the config once at load, then trust the type."

<!-- rule: test-behavior -->
## Test behavior, not implementation

*From: Test Behavior Not Implementation, tdd, and the real-tests note in typescript-best-practices.*

**Rule:** A test claims what a caller can observe. It fails when that result breaks, and it still passes when only the internals move.

**Use when:** writing, changing, or keeping a test.

**Do:**
- Drive the code through the interface a caller uses. Assert the return value, the error type a caller branches on, state that can be read back, or an effect outside the code (a row written, a message emitted, a request sent).
- Derive the expected value from the requirement. Do not compute it by calling the code under test.
- Break the behavior in your head: a wrong return, a skipped effect, a doubled effect. If the test would still pass, it proves nothing.
- Move the internals in your head and keep every observable result. If the test would fail, it is pinned to the implementation. Rewrite it or delete it.
- A call to an internal helper is implementation. The payload a mocked external service receives is behavior, because that service observes it.
- Run the real function, parser, or file. Mock only a system you cannot run locally.
- When a bug has a cheap local test path, write the failing test first and run it before the fix. Confirm it fails for the reason you think.
- Skip a new test when the only path needs a broad harness, a brittle mock, slow end-to-end setup, or production-only state. No test is better than a test that only checks a mock.
- Do not change a test to match a wrong implementation. Do not weaken an assertion unless the required behavior changed.

**Steer:** "test behavior, not implementation. assert the row that was written, not which helper ran."

<!-- rule: pin-the-behavior -->
## Pin the behavior

*From: the refactoring playbook.*

**Rule:** Before a refactor, pin what callers can observe. The structure moves. The behavior stays.

**Use when:** a change that should not alter results: a rename, a split, a type reshape, a file move.

**Do:**
- Write a characterization test, a snapshot, or an equivalence check before the structure moves. If the area has no coverage, the pin comes first.
- Keep that pin green on each small step.
- A passing type check or lint is not the pin.
- If the cleanup finds a bug or a missing behavior, split that out. Ship the structural change against the pinned contract first.
- For a larger reshape, diff old and new outputs, or replay a recorded baseline.

**Steer:** "pin the behavior. land the characterization test before you move the function."

<!-- rule: migrate-then-delete -->
## Migrate callers, then delete

*From: Migrate Callers Then Delete Legacy APIs.*

**Rule:** When no external user needs the old API, update every caller and delete the old API in the same change.

**Use when:** an internal API is being replaced, and the repo can take the break.

**Do:**
- Update tests to the new contract. Delete tests that only protect the old internals.
- Do not leave a compatibility shim, a wrapper with one caller, or a second path beside the new one.
- This rule does not apply when an external user still depends on the old API.

**Steer:** "migrate callers, then delete. no shim. the old function goes out in this change."

<!-- rule: code-pr-body -->
## Pull request body

*From: opening-a-pr.*

**Rule:** A pull request that touches a file on the code-scope list carries four markdown headings: Why, Scope, Blast radius, and Verification.

**Use when:** opening a pull request that changes code.

**Do:**
- Use a heading line (`#` through `######`) whose text is exactly one of those four. Case does not matter. Trailing hashes are fine. A longer heading does not count. A heading inside a fenced block does not count.
- Why states the problem and the approach, in a few short sentences.
- Scope states what the change covers and what it leaves out.
- Blast radius states who or what the change touches, and why that is safe or risky.
- Verification states the commands that ran and what they showed. That section is the evidence.
- `cos-check-pr-body` enforces the four headings on a pull request. A push straight to a branch has no pull request body, so that step does not run. The compare file list stops at 300 paths, and the check fails when the list reaches that size.

**Steer:** "the PR body needs Why, Scope, Blast radius, and Verification."

<!-- rule: code-pr-proof -->
## Pull request proof

*From: opening-a-pr, shipping, and babysit.*

**Rule:** Keep the pull request small. A green run is not proof. The person or agent who wrote the change does not grade it.

**Use when:** opening, reviewing, or calling a code change done.

**Do:**
- Prefer a few narrow pull requests to one large one. Each one is a change a reviewer can hold in their head.
- The verifier did not write the code. Principle 10 (Builder never grades) is that rule. Hand the verifier the diff and the original ask.
- A green CI run and a bot approval are not the verdict. They did not exercise the behavior the way a caller would.
- Name the run in Verification: the command and the result. If you could not run the failing test first, say why and name the closest check you did run.

**Steer:** "green CI is not the proof. show the test run, and have someone else grade it."
