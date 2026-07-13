Read ARCHI.md and PLAN.md first for full context on this project.

I've been dogfooding the /pack endpoint against the test-repo fixture
(described in test-repo/README.md) and found a real scoring bug in the
hybrid retrieval pipeline. I need you to diagnose the root cause and fix it
— not just patch the symptom.

## Bug report

Query: "optimize the database query performance"
Repo: test-repo (10 files, none of which contain actual database query code
— only `config/settings.py` has a loosely related `DATABASE_URL` variable).

Actual result from /pack:
1. backend/payments.py — 303 tokens, ranked #1
2. backend/auth.py — 421 tokens, ranked #2
3. backend/models.py — 241 tokens
4. README.md — 384 tokens
5. .gitignore — 35 tokens, non-zero relevance score
6. backend/utils.py — 178 tokens

Two separate problems here:

1. `.gitignore` — a config file with no prose or code semantics, just
   filename patterns — is receiving a non-trivial relevance score for an
   unrelated natural-language query. This suggests either (a) it's being
   chunked/embedded as if it were regular content when it shouldn't be
   indexed at all, or (b) there's a scoring bug producing non-zero scores
   for near-empty/irrelevant content.

2. `payments.py` outranks everything for a query it has no real relevance
   to. This isn't the first time — the same file also outranked `auth.py`
   on an earlier "fix the auth bug in login flow" test. Two independent
   queries where an unrelated file scores unexpectedly high points at a
   systemic issue in how the BM25 and vector scores are being merged, not
   a one-off fluke.

I also ran a deliberately vague query ("improve the app") and got a fully
differentiated ranking with confident-looking relevance bars even though
there's no real signal to rank on — the UI has no way to communicate
"none of these matches are actually strong."

## What I need you to do

1. **Investigate the scoring pipeline.** Find where BM25 score and vector
   similarity score are computed and merged for each chunk/file. Log or
   surface the two component scores separately (not just the merged
   score) for the queries above, so we can see which retrieval method is
   producing the bad signal.

2. **Fix file-type filtering in the scanner.** Files like `.gitignore`,
   lockfiles, and other non-code/non-prose files should either be excluded
   from indexing entirely, or explicitly down-weighted so they can never
   dominate a ranking. Decide which approach fits our architecture better
   and document the decision in ARCHI.md.

3. **Add a minimum-relevance threshold to the packer.** If the top score
   for a query doesn't clear a reasonable confidence threshold, the
   response should indicate low confidence (e.g. a `confidence: "low"`
   flag in the /pack response) instead of returning a fully ranked list
   that looks equally authoritative regardless of match quality. The
   extension UI already renders per-file relevance bars — this flag should
   let the UI communicate "weak match" state rather than a bug fix on its
   own.

4. **Write a regression test** using the test-repo fixture that asserts:
   - `.gitignore` never appears in results for a code-relevance query
   - for the query "optimize the database query performance", `payments.py`
     does not outrank `settings.py`
   - for the query "fix the auth bug in login flow", the four auth-cluster
     files (auth.py, models.py, LoginForm.tsx, test_auth.py) all outrank
     payments.py and Dashboard.tsx

5. **Report back** what the actual root cause was (bad chunking, bad merge
   weighting, missing filters — whichever it turns out to be) before
   moving on, so I understand the fix rather than just trusting it works.

Don't touch the extension UI code for this — this is a server/retrieval
pipeline fix only. If you think the UI needs a follow-up change to surface
the new confidence flag, note it but leave it for a separate task.
